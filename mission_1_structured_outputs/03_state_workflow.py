from __future__ import annotations

import json
import re
from typing import Any, Callable, Literal, Mapping, TypedDict

from pydantic import BaseModel, Field, ValidationError

Category = Literal["billing", "technical", "sales", "other"]
Urgency = Literal["low", "medium", "high"]
Sentiment = Literal["positive", "neutral", "negative"]
ToolName = Literal["calculate_refund_amount"]
NextStep = Literal["analyze", "choose_tool", "execute_tool", "finish", "error"]


class SupportWorkflowState(TypedDict):
    """Jawny stan prostego workflow obsługi zgłoszenia.

    To jeszcze nie jest LangGraph. Ten typ pokazuje jednak dokładnie ten sam
    wzorzec, który później przeniesiemy do StateGraph: każda funkcja-node
    przyjmuje state i zwraca zaktualizowany state.
    """

    customer_email: str
    category: Category | None
    urgency: Urgency | None
    sentiment: Sentiment | None
    summary: str | None
    selected_tool: ToolName | None
    tool_args: dict[str, Any] | None
    tool_result: dict[str, Any] | None
    errors_history: list[str]
    next_step: NextStep


class TicketAnalysis(BaseModel):
    """Zwalidowana analiza zgłoszenia klienta."""

    category: Category
    urgency: Urgency
    sentiment: Sentiment
    summary: str = Field(min_length=5, max_length=240)


class RefundArgs(BaseModel):
    """Argumenty narzędzia obliczającego kwotę zwrotu."""

    monthly_price: float = Field(gt=0, description="Cena miesięcznej subskrypcji")
    duplicated_charges: int = Field(
        ge=1,
        le=12,
        description="Liczba nadmiarowo pobranych opłat",
    )


class RefundResult(BaseModel):
    """Wynik działania narzędzia obliczającego zwrot."""

    refund_amount: float = Field(ge=0)
    currency: str = "PLN"


def make_initial_state(customer_email: str) -> SupportWorkflowState:
    """Tworzy początkowy stan workflow.

    W profesjonalnym systemie stan powinien powstać jawnie, zamiast być
    rozproszony po zmiennych globalnych, historii czatu lub efektach ubocznych.
    """

    return {
        "customer_email": customer_email,
        "category": None,
        "urgency": None,
        "sentiment": None,
        "summary": None,
        "selected_tool": None,
        "tool_args": None,
        "tool_result": None,
        "errors_history": [],
        "next_step": "analyze",
    }


def append_error(state: SupportWorkflowState, message: str) -> SupportWorkflowState:
    """Zwraca kopię stanu z dopisanym błędem."""

    return {
        **state,
        "errors_history": [*state["errors_history"], message],
    }


def analyze_ticket_node(state: SupportWorkflowState) -> SupportWorkflowState:
    """Analizuje treść zgłoszenia i zapisuje wynik w stanie.

    Na tym etapie celowo używamy prostych reguł zamiast LLM. Dzięki temu
    najpierw uczymy się architektury state -> node -> state. Dopiero później
    można wymienić tę logikę na wywołanie modelu ze Structured Outputs.
    """

    email = state["customer_email"].lower()

    if any(term in email for term in ["opłat", "subskrypc", "płatno", "zwrot"]):
        category: Category = "billing"
    elif any(term in email for term in ["błąd", "nie działa", "problem techniczny"]):
        category = "technical"
    elif any(term in email for term in ["oferta", "cennik", "zakup"]):
        category = "sales"
    else:
        category = "other"

    if any(term in email for term in ["natychmiast", "trzeci raz", "rezygnuję"]):
        urgency: Urgency = "high"
    elif any(term in email for term in ["proszę", "pilne"]):
        urgency = "medium"
    else:
        urgency = "low"

    if any(term in email for term in ["wściek", "rezygnuję", "problem", "błąd"]):
        sentiment: Sentiment = "negative"
    elif any(term in email for term in ["dziękuję", "świetnie", "super"]):
        sentiment = "positive"
    else:
        sentiment = "neutral"

    analysis = TicketAnalysis(
        category=category,
        urgency=urgency,
        sentiment=sentiment,
        summary="Klient zgłasza problem wymagający klasyfikacji i dalszej obsługi.",
    )

    return {
        **state,
        "category": analysis.category,
        "urgency": analysis.urgency,
        "sentiment": analysis.sentiment,
        "summary": analysis.summary,
        "next_step": "choose_tool",
    }


def extract_price_pln(text: str) -> float | None:
    """Wyciąga cenę w PLN tylko wtedy, gdy obok liczby występuje waluta.

    To celowe ograniczenie: nie chcemy przypadkowo potraktować numeru karty,
    numeru zgłoszenia lub innej liczby jako ceny.
    """

    pattern = r"(\d+(?:[.,]\d{1,2})?)\s*(?:zł|pln)"
    match = re.search(pattern, text, flags=re.IGNORECASE)
    if match is None:
        return None

    return float(match.group(1).replace(",", "."))


def choose_tool_node(state: SupportWorkflowState) -> SupportWorkflowState:
    """Wybiera narzędzie na podstawie aktualnego stanu.

    Node nie wykonuje narzędzia. Jego odpowiedzialność jest węższa: ma tylko
    zdecydować, czy narzędzie jest potrzebne i przygotować argumenty.
    """

    if state["category"] != "billing":
        return {
            **state,
            "selected_tool": None,
            "tool_args": None,
            "next_step": "finish",
        }

    email = state["customer_email"]
    email_lower = email.lower()

    if not any(term in email_lower for term in ["podwójn", "zwrot", "pobrano"]):
        return {
            **state,
            "selected_tool": None,
            "tool_args": None,
            "next_step": "finish",
        }

    monthly_price = extract_price_pln(email)
    if monthly_price is None:
        state_with_error = append_error(
            state,
            "Nie można obliczyć zwrotu: w zgłoszeniu nie znaleziono ceny z walutą PLN.",
        )
        return {
            **state_with_error,
            "selected_tool": None,
            "tool_args": None,
            "next_step": "error",
        }

    return {
        **state,
        "selected_tool": "calculate_refund_amount",
        "tool_args": {
            "monthly_price": monthly_price,
            "duplicated_charges": 1,
        },
        "next_step": "execute_tool",
    }


def calculate_refund_amount(raw_args: Mapping[str, Any]) -> dict[str, Any]:
    """Bezpieczne narzędzie aplikacyjne: oblicza kwotę zwrotu.

    Funkcja nie ufa argumentom wejściowym. Najpierw waliduje je przez Pydantic,
    a dopiero potem wykonuje obliczenie.
    """

    args = RefundArgs.model_validate(raw_args)
    result = RefundResult(
        refund_amount=round(args.monthly_price * args.duplicated_charges, 2),
        currency="PLN",
    )
    return result.model_dump()


ToolFunction = Callable[[Mapping[str, Any]], dict[str, Any]]

TOOL_REGISTRY: dict[str, ToolFunction] = {
    "calculate_refund_amount": calculate_refund_amount,
}


def execute_tool_node(state: SupportWorkflowState) -> SupportWorkflowState:
    """Wykonuje wybrane narzędzie po sprawdzeniu whitelisty i argumentów."""

    tool_name = state["selected_tool"]
    if tool_name is None:
        return {
            **state,
            "next_step": "finish",
        }

    tool = TOOL_REGISTRY.get(tool_name)
    if tool is None:
        state_with_error = append_error(
            state,
            f"Narzędzie '{tool_name}' nie istnieje w TOOL_REGISTRY.",
        )
        return {
            **state_with_error,
            "next_step": "error",
        }

    if state["tool_args"] is None:
        state_with_error = append_error(
            state,
            f"Narzędzie '{tool_name}' nie ma przygotowanych argumentów.",
        )
        return {
            **state_with_error,
            "next_step": "error",
        }

    try:
        tool_result = tool(state["tool_args"])
    except ValidationError as error:
        state_with_error = append_error(
            state,
            f"Błąd walidacji argumentów narzędzia '{tool_name}': {error}",
        )
        return {
            **state_with_error,
            "next_step": "error",
        }

    return {
        **state,
        "tool_result": tool_result,
        "next_step": "finish",
    }


def run_workflow(
    initial_state: SupportWorkflowState,
    max_steps: int = 10,
) -> SupportWorkflowState:
    """Uruchamia prosty workflow state -> node -> state.

    Limit kroków chroni przed przypadkową nieskończoną pętlą. To ten sam nawyk,
    który później będzie ważny przy retry loops w LangGraph.
    """

    state = initial_state

    for _ in range(max_steps):
        next_step = state["next_step"]

        if next_step == "analyze":
            state = analyze_ticket_node(state)
        elif next_step == "choose_tool":
            state = choose_tool_node(state)
        elif next_step == "execute_tool":
            state = execute_tool_node(state)
        elif next_step in {"finish", "error"}:
            return state
        else:
            state_with_error = append_error(
                state,
                f"Nieznany następny krok workflow: {next_step}",
            )
            return {
                **state_with_error,
                "next_step": "error",
            }

    state_with_error = append_error(
        state,
        f"Workflow przekroczył limit kroków: max_steps={max_steps}.",
    )
    return {
        **state_with_error,
        "next_step": "error",
    }


def main() -> None:
    """Uruchamia demonstracyjny workflow obsługi zgłoszenia."""

    customer_email = (
        "Dzień dobry, piszę do was już trzeci raz. "
        "Subskrypcja kosztuje 49.99 zł, ale pobrano mi opłatę podwójnie. "
        "Jestem wściekły i proszę o natychmiastowy zwrot."
    )

    initial_state = make_initial_state(customer_email)
    final_state = run_workflow(initial_state)

    print(json.dumps(final_state, ensure_ascii=False, indent=4))


if __name__ == "__main__":
    main()
