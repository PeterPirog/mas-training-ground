# 02_tool_calling.md — Misja 2: Tool Calling w zastosowaniach ogólnych

## 0. Metadane lekcji

**Temat:** Tool Calling, czyli kontrolowane używanie funkcji przez system agentowy  
**Poziom:** podstawowy → średni  
**Poprzednia lekcja:** `01_run.py` / Structured Outputs + Pydantic  
**Plik kodu do utworzenia:** `02_tool_calling.py`  
**Cel techniczny:** zrozumieć, że LLM nie wykonuje narzędzi samodzielnie, lecz proponuje ich użycie, a aplikacja Python waliduje argumenty i wykonuje właściwą funkcję.

---

## 1. Najkrótsza odpowiedź techniczna

W Misji 1 nauczyłeś się wzorca:

```text
LLM → JSON → Pydantic validation → obiekt Python
```

W Misji 2 uczysz się wzorca:

```text
LLM → propozycja tool call → walidacja argumentów → Python wykonuje funkcję → wynik wraca do workflow
```

Najważniejsza zasada:

> **Model nie wykonuje narzędzia. Model tylko proponuje wywołanie. Python decyduje, czy narzędzie wolno uruchomić, waliduje argumenty i wykonuje kod.**

---

## 2. Cel szkoleniowy tej misji

Celem tej lekcji jest zbudowanie pierwszego bezpiecznego narzędzia aplikacyjnego, które później będzie można podłączyć do LLM i LangGraph.

Na tym etapie nie zaczynamy od pełnej integracji z API modelu. Najpierw uczymy się poprawnego kontraktu narzędzia:

```text
nazwa narzędzia
→ model wejścia Pydantic
→ funkcja wykonawcza
→ model wyniku Pydantic
→ walidacja
→ testowalny wynik
```

To jest fundament pod późniejsze narzędzia takie jak:

- `classify_ticket`,
- `calculate_refund_amount`,
- `search_knowledge_base`,
- `summarize_document`,
- `create_report`,
- `run_unit_tests`,
- `read_project_file`,
- `write_markdown_file`.

---

## 3. Intuicja

W pierwszej lekcji model analizował zgłoszenie i zwracał strukturę danych:

```json
{
  "category": "billing",
  "urgency": "high",
  "sentiment": "negative",
  "summary": "Klient zgłasza podwójne naliczenie opłaty."
}
```

To był przypadek **Structured Outputs**.

W Tool Calling idziemy krok dalej. Model nie tylko opisuje sytuację, ale może zasugerować, że trzeba użyć konkretnej funkcji aplikacji.

Przykład wiadomości klienta:

```text
Pobraliście mi opłatę dwa razy. Subskrypcja kosztuje 49.99 zł. Proszę o zwrot.
```

Model powinien rozpoznać, że przyda się narzędzie:

```text
calculate_refund_amount
```

czyli funkcja obliczająca kwotę zwrotu.

Ale model nie powinien samodzielnie wykonywać logiki biznesowej. On może zaproponować:

```json
{
  "tool_name": "calculate_refund_amount",
  "arguments": {
    "monthly_price": 49.99,
    "duplicated_charges": 1
  }
}
```

Następnie aplikacja Python sprawdza:

```text
Czy takie narzędzie istnieje?
Czy jest dozwolone?
Czy argumenty są poprawne?
Czy wynik ma właściwy typ?
Czy można zapisać rezultat do stanu workflow?
```

Dopiero po tej kontroli funkcja zostaje wykonana.

---

## 4. Miejsce Tool Calling w architekturze systemu agentowego

W większym systemie agentowym narzędzia są warstwą wykonawczą. LLM jest warstwą decyzyjną, ale nie powinien mieć nieograniczonego dostępu do systemu.

Poprawny przepływ wygląda tak:

```text
User input
  ↓
LLM Agent
  ↓
propozycja użycia narzędzia
  ↓
Tool Router / Tool Node
  ↓
walidacja nazwy narzędzia i argumentów
  ↓
wykonanie funkcji Python
  ↓
zapis wyniku w stanie
  ↓
kolejny node / odpowiedź końcowa
```

W LangGraph ten wzorzec stanie się później osobnym node'em:

```text
analyze_request_node
  ↓
tool_router_node
  ↓
execute_tool_node
  ↓
critic_or_response_node
```

Na tym etapie budujemy tylko najprostszy, lokalny wariant narzędzia.

---

## 5. Structured Outputs vs Tool Calling

| Cecha | Structured Outputs | Tool Calling |
|---|---|---|
| Cel | Model zwraca dane | Model wskazuje narzędzie i argumenty |
| Wynik modelu | JSON z odpowiedzią | JSON z nazwą funkcji i argumentami |
| Kto wykonuje akcję? | Nikt — to tylko dane | Python wykonuje funkcję |
| Główna kontrola | Pydantic waliduje wynik | Pydantic waliduje argumenty i wynik |
| Ryzyko | Błędna struktura danych | Błędne lub niebezpieczne użycie funkcji |
| Profesjonalna ochrona | Schema + walidacja | Whitelist + Pydantic + logi + limity |

Wniosek:

> **Structured Outputs porządkuje odpowiedzi modelu. Tool Calling pozwala modelowi sterować funkcjami aplikacji, ale tylko przez kontrolowaną bramkę.**

---

## 6. Kontrakt profesjonalnego narzędzia

Każde narzędzie powinno mieć jasno opisany kontrakt.

Dla przykładu:

| Element | Wartość |
|---|---|
| Nazwa | `calculate_refund_amount` |
| Rola | Oblicza kwotę zwrotu dla klienta |
| Wejście | `RefundArgs` |
| Wyjście | `RefundResult` |
| Walidacja wejścia | Pydantic: cena > 0, liczba opłat od 1 do 12 |
| Efekty uboczne | Brak |
| Ryzyko | Niskie |
| Kryterium sukcesu | Wynik zawiera dodatnią kwotę zwrotu i walutę |
| Testowalność | Można przetestować bez LLM |

Profesjonalne narzędzie powinno być:

- małe,
- jednoznaczne,
- testowalne,
- ograniczone zakresem,
- walidowane,
- możliwe do użycia bez modelu LLM.

---

## 7. Czego nie robimy

Nie budujemy narzędzia typu:

```python
def do_anything(command: str) -> str:
    ...
```

To jest zły wzorzec, ponieważ:

- ma zbyt szerokie uprawnienia,
- trudno je testować,
- trudno ustalić, co wolno, a czego nie wolno,
- zwiększa ryzyko wykonania niechcianej akcji,
- nie ma jasnego kontraktu wejścia i wyjścia.

Zamiast tego budujemy małe narzędzia:

```python
def calculate_refund_amount(args: RefundArgs) -> RefundResult:
    ...
```

```python
def classify_ticket(args: TicketArgs) -> TicketClassification:
    ...
```

```python
def search_documents(args: SearchArgs) -> SearchResult:
    ...
```

To jest styl, który dobrze skaluje się do LangGraph i multi-agent workflow.

---

## 8. Minimalny plik `02_tool_calling.py`

Utwórz plik:

```text
02_tool_calling.py
```

Wstaw do niego:

```python
from pydantic import BaseModel, Field


class RefundArgs(BaseModel):
    """Argumenty narzędzia obliczającego kwotę zwrotu."""

    monthly_price: float = Field(
        gt=0,
        description="Cena miesięcznej subskrypcji",
    )
    duplicated_charges: int = Field(
        ge=1,
        le=12,
        description="Liczba nadmiarowo pobranych opłat",
    )


class RefundResult(BaseModel):
    """Wynik obliczenia zwrotu."""

    refund_amount: float = Field(
        ge=0,
        description="Kwota zwrotu",
    )
    currency: str = Field(
        default="PLN",
        description="Waluta zwrotu",
    )


def calculate_refund_amount(args: RefundArgs) -> RefundResult:
    """Oblicza kwotę zwrotu dla klienta."""
    amount = args.monthly_price * args.duplicated_charges

    return RefundResult(
        refund_amount=round(amount, 2),
        currency="PLN",
    )


def main() -> None:
    args = RefundArgs(
        monthly_price=49.99,
        duplicated_charges=1,
    )

    result = calculate_refund_amount(args)

    print(result.model_dump_json(indent=4))


if __name__ == "__main__":
    main()
```

---

## 9. Uruchomienie

W terminalu:

```bash
python 02_tool_calling.py
```

Oczekiwany wynik:

```json
{
    "refund_amount": 49.99,
    "currency": "PLN"
}
```

Jeżeli używasz Ruff, po zapisaniu pliku uruchom:

```bash
ruff format 02_tool_calling.py
ruff check 02_tool_calling.py
python 02_tool_calling.py
```

---

## 10. Co dokładnie robi ten kod

### 10.1. `RefundArgs`

```python
class RefundArgs(BaseModel):
    monthly_price: float = Field(gt=0)
    duplicated_charges: int = Field(ge=1, le=12)
```

To jest model wejścia narzędzia.

Oznacza:

- `monthly_price` musi być liczbą większą od zera,
- `duplicated_charges` musi być liczbą całkowitą od 1 do 12.

Dzięki temu funkcja nie przyjmie danych takich jak:

```python
RefundArgs(monthly_price=-49.99, duplicated_charges=1)
```

ani:

```python
RefundArgs(monthly_price=49.99, duplicated_charges=1000)
```

Pydantic zatrzyma błędne dane przed wykonaniem narzędzia.

---

### 10.2. `RefundResult`

```python
class RefundResult(BaseModel):
    refund_amount: float = Field(ge=0)
    currency: str = "PLN"
```

To jest model wyjścia narzędzia.

Narzędzie nie zwraca luźnego słownika bez kontroli, tylko obiekt zgodny z kontraktem.

Dzięki temu dalszy workflow wie, czego się spodziewać:

```text
refund_amount: float
currency: str
```

---

### 10.3. `calculate_refund_amount`

```python
def calculate_refund_amount(args: RefundArgs) -> RefundResult:
    amount = args.monthly_price * args.duplicated_charges
    return RefundResult(refund_amount=round(amount, 2), currency="PLN")
```

To jest właściwe narzędzie.

Ważne cechy:

- przyjmuje jeden obiekt argumentów,
- zwraca jeden obiekt wyniku,
- nie komunikuje się z LLM,
- nie ma efektów ubocznych,
- jest łatwe do testowania.

To jest bardzo dobry wzorzec dla narzędzi w systemach agentowych.

---

### 10.4. `main`

```python
def main() -> None:
    args = RefundArgs(monthly_price=49.99, duplicated_charges=1)
    result = calculate_refund_amount(args)
    print(result.model_dump_json(indent=4))
```

Na razie `main()` symuluje to, co później zrobi LLM:

```text
przygotowanie argumentów → walidacja Pydantic → wykonanie narzędzia → prezentacja wyniku
```

Jeszcze nie używamy modelu LLM. Najpierw upewniamy się, że narzędzie jest poprawne samo w sobie.

---

## 11. Test błędu walidacji

Zmień w `main()`:

```python
args = RefundArgs(
    monthly_price=-49.99,
    duplicated_charges=1,
)
```

Uruchom:

```bash
python 02_tool_calling.py
```

Powinieneś zobaczyć błąd walidacji Pydantic.

To jest oczekiwane i poprawne.

Dlaczego?

Bo `monthly_price` ma ograniczenie:

```python
Field(gt=0)
```

czyli cena musi być większa od zera.

Wniosek:

> **Błąd walidacji nie jest porażką systemu. Jest dowodem, że system zatrzymał niepoprawne dane przed wykonaniem narzędzia.**

---

## 12. Jak wyglądałby tool call od modelu

Na razie nie implementujemy jeszcze pełnego wywołania przez API. Ale mentalnie model mógłby zwrócić coś takiego:

```json
{
  "tool_name": "calculate_refund_amount",
  "arguments": {
    "monthly_price": 49.99,
    "duplicated_charges": 1
  }
}
```

A aplikacja powinna zrobić:

```python
allowed_tools = {
    "calculate_refund_amount": calculate_refund_amount,
}

tool_name = "calculate_refund_amount"
raw_arguments = {
    "monthly_price": 49.99,
    "duplicated_charges": 1,
}

if tool_name not in allowed_tools:
    raise ValueError(f"Niedozwolone narzędzie: {tool_name}")

args = RefundArgs.model_validate(raw_arguments)
result = allowed_tools[tool_name](args)
```

To jest kluczowy wzorzec:

```text
whitelist narzędzi → walidacja argumentów → wykonanie funkcji
```

---

## 13. Router narzędzi — wersja edukacyjna

W kolejnym kroku możesz dodać prosty router narzędzi.

Przykład:

```python
from typing import Any


TOOLS = {
    "calculate_refund_amount": calculate_refund_amount,
}


def execute_tool(tool_name: str, raw_arguments: dict[str, Any]) -> BaseModel:
    if tool_name not in TOOLS:
        raise ValueError(f"Niedozwolone narzędzie: {tool_name}")

    if tool_name == "calculate_refund_amount":
        args = RefundArgs.model_validate(raw_arguments)
        return calculate_refund_amount(args)

    raise ValueError(f"Brak obsługi narzędzia: {tool_name}")
```

To jeszcze nie jest docelowa wersja produkcyjna, ale pokazuje ważny podział:

```text
LLM wybiera nazwę narzędzia i argumenty
router sprawdza nazwę
Pydantic sprawdza argumenty
funkcja wykonuje pracę
```

---

## 14. Jak to stanie się node'em LangGraph

W LangGraph taki mechanizm powinien operować na jawnym stanie.

Przykładowy stan:

```python
from typing import TypedDict


class SupportWorkflowState(TypedDict):
    customer_message: str
    selected_tool: str | None
    tool_arguments: dict | None
    tool_result: dict | None
    errors_history: list[str]
```

Przykładowy node:

```python
def execute_tool_node(state: SupportWorkflowState) -> SupportWorkflowState:
    tool_name = state["selected_tool"]
    raw_arguments = state["tool_arguments"]

    if tool_name is None or raw_arguments is None:
        return {
            **state,
            "errors_history": [
                *state["errors_history"],
                "Brak narzędzia lub argumentów do wykonania.",
            ],
        }

    result = execute_tool(tool_name, raw_arguments)

    return {
        **state,
        "tool_result": result.model_dump(),
    }
```

To pokazuje przejście od prostego skryptu do workflow:

```text
funkcja lokalna → router narzędzi → node LangGraph → stan workflow
```

---

## 15. Minimalne testy jednostkowe

Profesjonalne narzędzie powinno mieć testy.

Przykładowy plik:

```text
tests/test_02_tool_calling.py
```

Przykładowe testy:

```python
import pytest
from pydantic import ValidationError

from 02_tool_calling import RefundArgs, calculate_refund_amount


def test_calculate_refund_amount() -> None:
    args = RefundArgs(monthly_price=49.99, duplicated_charges=2)

    result = calculate_refund_amount(args)

    assert result.refund_amount == 99.98
    assert result.currency == "PLN"


def test_refund_args_reject_negative_price() -> None:
    with pytest.raises(ValidationError):
        RefundArgs(monthly_price=-49.99, duplicated_charges=1)


def test_refund_args_reject_too_many_charges() -> None:
    with pytest.raises(ValidationError):
        RefundArgs(monthly_price=49.99, duplicated_charges=100)
```

Uwaga techniczna: import z pliku zaczynającego się od cyfry (`02_tool_calling.py`) może być niewygodny w testach. W wersji produkcyjnej lepiej przenieść kod do pakietu, np.:

```text
src/support_tools/refund.py
```

Plik `02_tool_calling.py` może wtedy zostać tylko edukacyjnym runnerem.

---

## 16. Profesjonalny kierunek struktury projektu

Wersja edukacyjna:

```text
02_tool_calling.py
```

Wersja bardziej profesjonalna:

```text
src/
  support_tools/
    __init__.py
    refund.py
    router.py

tests/
  test_refund.py
  test_tool_router.py
```

Podział odpowiedzialności:

| Plik | Odpowiedzialność |
|---|---|
| `refund.py` | Modele `RefundArgs`, `RefundResult` i funkcja `calculate_refund_amount` |
| `router.py` | Whitelist narzędzi i funkcja `execute_tool` |
| `test_refund.py` | Testy narzędzia refundacji |
| `test_tool_router.py` | Testy routingu narzędzi |

To jest kierunek, w którym pójdziemy po zrozumieniu podstaw.

---

## 17. Typowe błędy początkującego

### Błąd 1: Ufać argumentom z modelu

Źle:

```python
result = calculate_refund_amount(raw_arguments)
```

Dobrze:

```python
args = RefundArgs.model_validate(raw_arguments)
result = calculate_refund_amount(args)
```

---

### Błąd 2: Tworzyć jedno narzędzie do wszystkiego

Źle:

```python
def execute_action(action: str, payload: dict) -> dict:
    ...
```

Dobrze:

```python
def calculate_refund_amount(args: RefundArgs) -> RefundResult:
    ...
```

---

### Błąd 3: Brak modelu wyniku

Źle:

```python
return {"amount": amount}
```

Dobrze:

```python
return RefundResult(refund_amount=amount, currency="PLN")
```

Model wyniku pomaga utrzymać jawny kontrakt danych.

---

### Błąd 4: Brak whitelisty narzędzi

Źle:

```python
globals()[tool_name](**arguments)
```

To jest niebezpieczne i niekontrolowane.

Dobrze:

```python
TOOLS = {
    "calculate_refund_amount": calculate_refund_amount,
}
```

---

### Błąd 5: Łączenie decyzji LLM i wykonania narzędzia w jednym miejscu

Źle:

```text
prompt → model → automatycznie wykonaj wszystko
```

Dobrze:

```text
prompt → model proponuje → router sprawdza → Pydantic waliduje → Python wykonuje
```

---

## 18. Ćwiczenia praktyczne

### Ćwiczenie 1 — uruchomienie poprawnego narzędzia

Utwórz `02_tool_calling.py`, uruchom:

```bash
python 02_tool_calling.py
```

Kryterium zaliczenia:

```text
Program wypisuje JSON z refund_amount i currency.
```

---

### Ćwiczenie 2 — wymuszenie błędu walidacji

Zmień `monthly_price` na wartość ujemną:

```python
monthly_price=-49.99
```

Kryterium zaliczenia:

```text
Pydantic zgłasza błąd i narzędzie nie wykonuje się na błędnych danych.
```

---

### Ćwiczenie 3 — dodanie drugiego narzędzia

Dodaj nowe narzędzie:

```python
class TicketPriorityArgs(BaseModel):
    urgency: str
    sentiment: str


class TicketPriorityResult(BaseModel):
    priority_score: int


def calculate_priority_score(args: TicketPriorityArgs) -> TicketPriorityResult:
    score = 0

    if args.urgency == "high":
        score += 2
    if args.sentiment == "negative":
        score += 1

    return TicketPriorityResult(priority_score=score)
```

Kryterium zaliczenia:

```text
Masz dwa małe narzędzia, każde z własnym modelem wejścia i wyjścia.
```

---

### Ćwiczenie 4 — whitelist narzędzi

Dodaj słownik:

```python
TOOLS = {
    "calculate_refund_amount": calculate_refund_amount,
    "calculate_priority_score": calculate_priority_score,
}
```

Kryterium zaliczenia:

```text
Program nie pozwala wykonać narzędzia spoza listy.
```

---

### Ćwiczenie 5 — opis narzędzia jako schema

Wypisz schemat argumentów:

```python
print(RefundArgs.model_json_schema())
```

Kryterium zaliczenia:

```text
Rozumiesz, że ten schemat można później przekazać modelowi LLM jako opis argumentów narzędzia.
```

---

## 19. Pytania kontrolne

Odpowiedz samodzielnie:

1. Czym różni się Structured Outputs od Tool Calling?
2. Kto faktycznie wykonuje funkcję: model LLM czy Python?
3. Dlaczego argumenty narzędzia trzeba traktować jako niezaufane?
4. Po co tworzymy osobny model `RefundArgs`?
5. Po co tworzymy osobny model `RefundResult`?
6. Dlaczego narzędzie `do_anything(command: str)` jest złym wzorcem?
7. Co oznacza `Field(gt=0)`?
8. Jaką rolę pełni whitelist narzędzi?
9. Jak wynik narzędzia mógłby trafić do stanu LangGraph?
10. Dlaczego najpierw testujemy narzędzie bez LLM?

---

## 20. Kryterium zaliczenia lekcji

Uznaj lekcję za zaliczoną, gdy potrafisz:

- utworzyć model Pydantic dla argumentów narzędzia,
- utworzyć model Pydantic dla wyniku narzędzia,
- napisać małą funkcję narzędziową,
- uruchomić ją bez LLM,
- celowo wywołać błąd walidacji,
- wyjaśnić, dlaczego LLM tylko proponuje tool call,
- wyjaśnić, dlaczego Python musi walidować argumenty,
- wskazać, jak takie narzędzie stanie się node'em w LangGraph.

---

## 21. Następny krok

W kolejnym etapie rozbudujemy tę lekcję o właściwą integrację z modelem:

```text
LLM otrzymuje listę dostępnych narzędzi
→ model wybiera narzędzie
→ model zwraca argumenty
→ Python waliduje argumenty
→ Python wykonuje narzędzie
→ wynik trafia do kolejnego kroku workflow
```

Dopiero potem przeniesiemy mechanizm do LangGraph jako osobny `Tool Node`.

