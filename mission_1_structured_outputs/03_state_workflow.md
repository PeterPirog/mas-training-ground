# 03_state_workflow.md — Jawny stan workflow

## 0. Najkrótsza odpowiedź techniczna

Plik `03_state_workflow.py` pokazuje pierwszy prawdziwy wzorzec architektury systemów agentowych:

```text
state → node → state
```

To jeszcze nie jest LangGraph, ale jest to bezpośrednie przygotowanie do LangGraph. Każda funkcja-node przyjmuje jawny stan workflow, wykonuje jedną odpowiedzialność i zwraca zaktualizowany stan.

Główna lekcja:

> W systemie agentowym nie należy polegać na ukrytej historii rozmowy ani przypadkowych zmiennych globalnych. Przepływ powinien być zapisany w jawnym, typowanym stanie.

---

## 1. Cel lekcji

Celem lekcji jest zrozumienie, jak połączyć wiedzę z dwóch poprzednich etapów:

1. **Structured Outputs** — wynik ma być ustrukturyzowany i walidowany.
2. **Tool Calling** — narzędzie ma mieć kontrolowane wejście i wyjście.
3. **Workflow State** — kolejne kroki aplikacji mają wymieniać dane przez jawny stan.

Po tej lekcji masz rozumieć, że aplikacja agentowa nie powinna wyglądać tak:

```text
funkcja A coś drukuje
funkcja B zgaduje, co było wcześniej
funkcja C używa zmiennej globalnej
LLM pamięta resztę w historii czatu
```

Lepszy wzorzec to:

```text
initial_state
  ↓
analyze_ticket_node(state)
  ↓
choose_tool_node(state)
  ↓
execute_tool_node(state)
  ↓
final_state
```

---

## 2. Miejsce lekcji w ścieżce szkoleniowej

Dotychczas:

```text
01_run.py
LLM → JSON → Pydantic validation
```

Potem:

```text
02_tool_calling.py
argumenty → Pydantic validation → narzędzie → wynik
```

Teraz:

```text
03_state_workflow.py
state → analiza → state → wybór narzędzia → state → wykonanie narzędzia → state
```

To jest most między zwykłym Pythonem a LangGraph.

W następnej lekcji ten sam wzorzec zostanie przeniesiony do `StateGraph`.

---

## 3. Intuicja

Wyobraź sobie prosty system obsługi zgłoszeń klienta.

Klient pisze:

```text
Dzień dobry, piszę do was już trzeci raz. Subskrypcja kosztuje 49.99 zł, ale pobrano mi opłatę podwójnie. Jestem wściekły i proszę o natychmiastowy zwrot.
```

System powinien:

1. rozpoznać kategorię zgłoszenia,
2. określić pilność,
3. określić sentyment,
4. zdecydować, czy potrzebne jest narzędzie,
5. przygotować argumenty narzędzia,
6. wykonać narzędzie,
7. zapisać wynik w stanie.

Ważne: każdy etap zapisuje wynik do `state`. Nie zgadujemy, co wydarzyło się wcześniej. Nie polegamy na pamięci modelu. Nie trzymamy ukrytych wartości poza przepływem.

---

## 4. Najważniejszy wzorzec: `state -> node -> state`

W tym pliku node to zwykła funkcja Pythona:

```python
def analyze_ticket_node(state: SupportWorkflowState) -> SupportWorkflowState:
    ...
    return updated_state
```

Każdy node powinien mieć jedną odpowiedzialność.

| Node | Odpowiedzialność |
|---|---|
| `analyze_ticket_node` | analizuje treść zgłoszenia |
| `choose_tool_node` | wybiera narzędzie i przygotowuje argumenty |
| `execute_tool_node` | wykonuje wybrane narzędzie |
| `run_workflow` | steruje przejściami między krokami |

To jest bardzo ważne: node nie powinien robić wszystkiego naraz.

Zły wzorzec:

```python
def big_agent_function():
    analyze()
    choose_tool()
    execute_tool()
    handle_errors()
    print_result()
```

Dobry wzorzec:

```python
state = analyze_ticket_node(state)
state = choose_tool_node(state)
state = execute_tool_node(state)
```

---

## 5. Importy i aliasy typów

Plik zaczyna się od:

```python
from __future__ import annotations

import json
import re
from typing import Any, Callable, Literal, Mapping, TypedDict

from pydantic import BaseModel, Field, ValidationError
```

Znaczenie:

| Element | Rola |
|---|---|
| `json` | ładne drukowanie stanu końcowego |
| `re` | prosta ekstrakcja ceny z tekstu |
| `Any` | typ dla danych jeszcze nieznanych statycznie |
| `Callable` | typowanie funkcji w rejestrze narzędzi |
| `Literal` | ograniczenie wartości do konkretnego zbioru |
| `Mapping` | ogólny typ słownika wejściowego |
| `TypedDict` | typowanie struktury stanu workflow |
| `BaseModel` | bazowa klasa modeli Pydantic |
| `Field` | dodatkowe reguły walidacji pól |
| `ValidationError` | obsługa błędów walidacji Pydantic |

Następnie są aliasy:

```python
Category = Literal["billing", "technical", "sales", "other"]
Urgency = Literal["low", "medium", "high"]
Sentiment = Literal["positive", "neutral", "negative"]
ToolName = Literal["calculate_refund_amount"]
NextStep = Literal["analyze", "choose_tool", "execute_tool", "finish", "error"]
```

To jest profesjonalniejszy wariant niż używanie wszędzie gołych `str`.

Dzięki temu `urgency` nie jest dowolnym tekstem. Może mieć tylko jedną z wartości:

```text
low | medium | high
```

---

## 6. Stan workflow: `SupportWorkflowState`

Najważniejszy typ w pliku to:

```python
class SupportWorkflowState(TypedDict):
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
```

Ten typ opisuje, co system wie w danym momencie.

| Pole | Znaczenie |
|---|---|
| `customer_email` | oryginalna wiadomość klienta |
| `category` | kategoria zgłoszenia |
| `urgency` | pilność sprawy |
| `sentiment` | nastawienie klienta |
| `summary` | krótkie podsumowanie |
| `selected_tool` | nazwa wybranego narzędzia |
| `tool_args` | argumenty przygotowane dla narzędzia |
| `tool_result` | wynik wykonania narzędzia |
| `errors_history` | historia błędów workflow |
| `next_step` | następny krok do wykonania |

To pole jest szczególnie ważne:

```python
next_step: NextStep
```

W obecnym pliku `next_step` ręcznie steruje przepływem. W LangGraph tę rolę przejmą edges i conditional edges.

---

## 7. Modele Pydantic

W pliku są trzy modele Pydantic.

### 7.1. `TicketAnalysis`

```python
class TicketAnalysis(BaseModel):
    category: Category
    urgency: Urgency
    sentiment: Sentiment
    summary: str = Field(min_length=5, max_length=240)
```

Ten model reprezentuje wynik analizy zgłoszenia.

Ważne:

- `category` nie może być dowolnym tekstem,
- `urgency` nie może być np. `critical`,
- `sentiment` nie może być np. `angry`,
- `summary` ma ograniczoną długość.

To jest silniejsza walidacja niż w pierwszym skrypcie, gdzie pola były zwykłymi stringami.

### 7.2. `RefundArgs`

```python
class RefundArgs(BaseModel):
    monthly_price: float = Field(gt=0)
    duplicated_charges: int = Field(ge=1, le=12)
```

Ten model waliduje argumenty narzędzia.

Reguły:

| Pole | Reguła |
|---|---|
| `monthly_price` | musi być większe od 0 |
| `duplicated_charges` | musi być od 1 do 12 |

Dzięki temu narzędzie nie przyjmie np. ceny `-49.99`.

### 7.3. `RefundResult`

```python
class RefundResult(BaseModel):
    refund_amount: float = Field(ge=0)
    currency: str = "PLN"
```

Ten model reprezentuje wynik narzędzia.

Ważne: walidujemy nie tylko wejście, ale również strukturę wyjścia.

---

## 8. Tworzenie stanu początkowego

Funkcja:

```python
def make_initial_state(customer_email: str) -> SupportWorkflowState:
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
```

Ta funkcja tworzy pierwszy stan workflow.

Najważniejsze: stan powstaje jawnie.

Nie robimy tak:

```python
customer_email = "..."
category = None
urgency = None
# dużo luźnych zmiennych
```

Robimy tak:

```python
state = make_initial_state(customer_email)
```

Dzięki temu cały workflow ma jeden obiekt, który można:

- przekazać do node'a,
- zapisać do pliku,
- zalogować,
- przekazać do LangGraph,
- przetestować.

---

## 9. Obsługa błędów: `append_error`

Funkcja:

```python
def append_error(state: SupportWorkflowState, message: str) -> SupportWorkflowState:
    return {
        **state,
        "errors_history": [*state["errors_history"], message],
    }
```

Ta funkcja nie modyfikuje listy błędów bezpośrednio. Zwraca nową wersję stanu z dopisanym błędem.

W praktyce:

```text
stary stan + nowy błąd → nowy stan
```

To jest dobry nawyk przed LangGraph, bo w grafie stan powinien być aktualizowany jawnie.

Typowe wpisy w `errors_history`:

```text
Nie znaleziono ceny z walutą PLN.
Narzędzie nie istnieje w TOOL_REGISTRY.
Błąd walidacji argumentów narzędzia.
Workflow przekroczył limit kroków.
```

---

## 10. Node 1: `analyze_ticket_node`

Funkcja:

```python
def analyze_ticket_node(state: SupportWorkflowState) -> SupportWorkflowState:
    ...
```

Odpowiedzialność:

```text
customer_email → category, urgency, sentiment, summary
```

W tej lekcji analiza jest deterministyczna, oparta na prostych regułach:

```python
if any(term in email for term in ["opłat", "subskrypc", "płatno", "zwrot"]):
    category = "billing"
```

To jest celowe. Na tym etapie nie chcemy jeszcze używać LLM. Najpierw uczymy się architektury stanu.

Później będzie można wymienić wnętrze tej funkcji na:

```python
raw = call_llm(...)
analysis = TicketAnalysis.model_validate_json(raw)
```

ale interfejs node'a pozostanie ten sam:

```python
def analyze_ticket_node(state: SupportWorkflowState) -> SupportWorkflowState:
    ...
```

To jest dobry projekt: zmienia się implementacja, ale nie zmienia się kontrakt workflow.

---

## 11. Ekstrakcja ceny: `extract_price_pln`

Funkcja:

```python
def extract_price_pln(text: str) -> float | None:
    pattern = r"(\d+(?:[.,]\d{1,2})?)\s*(?:zł|pln)"
    match = re.search(pattern, text, flags=re.IGNORECASE)
    if match is None:
        return None

    return float(match.group(1).replace(",", "."))
```

Jej zadanie jest wąskie: znaleźć liczbę występującą obok waluty `zł` albo `PLN`.

Dlaczego to istotne?

Ponieważ tekst klienta może zawierać inne liczby:

```text
piszę trzeci raz
numer zamówienia 12345
karta kończy się na 4432
```

Gdyby parser brał pierwszą lepszą liczbę, mógłby potraktować numer karty lub numer zgłoszenia jako cenę. Dlatego funkcja wymaga waluty obok liczby.

To jest mały przykład bezpiecznego projektowania narzędzi: nie ufaj surowemu tekstowi, ograniczaj interpretację danych.

---

## 12. Node 2: `choose_tool_node`

Funkcja:

```python
def choose_tool_node(state: SupportWorkflowState) -> SupportWorkflowState:
    ...
```

Odpowiedzialność:

```text
stan po analizie → decyzja, czy potrzebne jest narzędzie
```

Ta funkcja nie wykonuje narzędzia. Tylko wybiera narzędzie i przygotowuje argumenty.

To rozdzielenie jest kluczowe.

Zły wzorzec:

```python
def choose_tool_node(state):
    # wybiera narzędzie
    # wykonuje narzędzie
    # drukuje wynik
    # obsługuje błędy
```

Dobry wzorzec:

```text
choose_tool_node → tylko decyzja i argumenty
execute_tool_node → tylko wykonanie
```

Jeżeli zgłoszenie nie jest billingowe, workflow kończy się:

```python
"next_step": "finish"
```

Jeżeli zgłoszenie jest billingowe, ale brakuje ceny w PLN, workflow przechodzi do błędu:

```python
"next_step": "error"
```

Jeżeli wszystko jest poprawne, node przygotowuje:

```python
"selected_tool": "calculate_refund_amount"
"tool_args": {
    "monthly_price": 49.99,
    "duplicated_charges": 1,
}
"next_step": "execute_tool"
```

---

## 13. Narzędzie: `calculate_refund_amount`

Funkcja:

```python
def calculate_refund_amount(raw_args: Mapping[str, Any]) -> dict[str, Any]:
    args = RefundArgs.model_validate(raw_args)
    result = RefundResult(
        refund_amount=round(args.monthly_price * args.duplicated_charges, 2),
        currency="PLN",
    )
    return result.model_dump()
```

To jest bezpieczne narzędzie aplikacyjne.

Najważniejsze jest to, że funkcja nie ufa argumentom:

```python
args = RefundArgs.model_validate(raw_args)
```

Dopiero po walidacji wykonuje obliczenie.

To jest właściwy wzorzec Tool Calling:

```text
model lub node przygotowuje argumenty
  ↓
Pydantic waliduje argumenty
  ↓
funkcja wykonuje działanie
  ↓
Pydantic modeluje wynik
  ↓
wynik trafia do stanu
```

---

## 14. Rejestr narzędzi: `TOOL_REGISTRY`

W pliku jest prosty rejestr:

```python
ToolFunction = Callable[[Mapping[str, Any]], dict[str, Any]]

TOOL_REGISTRY: dict[str, ToolFunction] = {
    "calculate_refund_amount": calculate_refund_amount,
}
```

To jest whitelist narzędzi.

System nie wykonuje dowolnej funkcji po nazwie. Wykonuje tylko to, co jawnie wpisano do rejestru.

Zły wzorzec:

```python
tool = globals()[tool_name]
tool(args)
```

Dobry wzorzec:

```python
tool = TOOL_REGISTRY.get(tool_name)
```

Dlaczego?

Bo rejestr narzędzi jest kontrolowaną powierzchnią wykonania. W przyszłości mogą tu trafić narzędzia takie jak:

```text
search_documents
create_ticket
summarize_document
run_unit_tests
render_markdown_report
```

Każde z nich powinno mieć osobny kontrakt wejścia, wyjścia i walidacji.

---

## 15. Node 3: `execute_tool_node`

Funkcja:

```python
def execute_tool_node(state: SupportWorkflowState) -> SupportWorkflowState:
    ...
```

Odpowiedzialność:

```text
selected_tool + tool_args → tool_result
```

Ten node robi kilka kontroli:

1. Czy `selected_tool` istnieje?
2. Czy narzędzie jest w `TOOL_REGISTRY`?
3. Czy są przygotowane argumenty?
4. Czy argumenty przechodzą walidację Pydantic?
5. Czy wynik można zapisać do stanu?

Jeżeli wszystko jest poprawne:

```python
return {
    **state,
    "tool_result": tool_result,
    "next_step": "finish",
}
```

Jeżeli walidacja argumentów się nie powiedzie:

```python
except ValidationError as error:
    ...
    "next_step": "error"
```

To jest ważne: błąd walidacji nie jest porażką systemu. Jest sukcesem mechanizmu bezpieczeństwa, bo niepoprawne dane zostały zatrzymane przed wykonaniem akcji.

---

## 16. Runner workflow: `run_workflow`

Funkcja:

```python
def run_workflow(
    initial_state: SupportWorkflowState,
    max_steps: int = 10,
) -> SupportWorkflowState:
    ...
```

To prosty silnik workflow.

Działa na podstawie pola:

```python
next_step = state["next_step"]
```

Następnie wybiera odpowiedni node:

```python
if next_step == "analyze":
    state = analyze_ticket_node(state)
elif next_step == "choose_tool":
    state = choose_tool_node(state)
elif next_step == "execute_tool":
    state = execute_tool_node(state)
elif next_step in {"finish", "error"}:
    return state
```

To jest ręczna wersja grafu.

W LangGraph ten fragment zostanie zastąpiony przez:

```text
StateGraph
nodes
edges
conditional edges
```

Ale mentalny model zostanie ten sam.

---

## 17. Limit kroków: `max_steps`

W `run_workflow` znajduje się limit:

```python
max_steps: int = 10
```

oraz:

```python
for _ in range(max_steps):
    ...
```

To chroni przed nieskończoną pętlą.

Dlaczego to ważne?

W systemach agentowych łatwo stworzyć zły przepływ:

```text
analyze → choose_tool → analyze → choose_tool → analyze → ...
```

Dlatego każdy workflow z pętlami powinien mieć limit kroków, limit prób albo warunek zatrzymania.

To przygotowuje Cię do późniejszych tematów:

```text
retry loops
errors_history
auto-healing
NEEDS_HUMAN
```

---

## 18. Funkcja `main()`

Funkcja demonstracyjna:

```python
def main() -> None:
    customer_email = (...)

    initial_state = make_initial_state(customer_email)
    final_state = run_workflow(initial_state)

    print(json.dumps(final_state, ensure_ascii=False, indent=4))
```

Znaczenie:

1. Tworzymy przykładowe zgłoszenie klienta.
2. Budujemy `initial_state`.
3. Uruchamiamy workflow.
4. Drukujemy `final_state`.

Ważne: wynik nie jest tylko tekstem dla człowieka. To kompletny stan po wykonaniu workflow.

---

## 19. Jak uruchomić plik

W katalogu projektu uruchom:

```bash
python 03_state_workflow.py
```

Oczekiwany wynik powinien mieć strukturę podobną do:

```json
{
    "customer_email": "...",
    "category": "billing",
    "urgency": "high",
    "sentiment": "negative",
    "summary": "Klient zgłasza problem wymagający klasyfikacji i dalszej obsługi.",
    "selected_tool": "calculate_refund_amount",
    "tool_args": {
        "monthly_price": 49.99,
        "duplicated_charges": 1
    },
    "tool_result": {
        "refund_amount": 49.99,
        "currency": "PLN"
    },
    "errors_history": [],
    "next_step": "finish"
}
```

Najważniejsze pola końcowe:

```text
category = billing
selected_tool = calculate_refund_amount
tool_result.refund_amount = 49.99
next_step = finish
errors_history = []
```

---

## 20. Co ten plik robi dobrze

### 20.1. Ma jawny stan

Wszystkie kluczowe informacje są w `SupportWorkflowState`.

### 20.2. Ma małe node'y

Każda funkcja ma ograniczoną odpowiedzialność.

### 20.3. Używa silnych typów

`Literal` ogranicza dozwolone wartości.

### 20.4. Waliduje dane przez Pydantic

Argumenty narzędzia i wynik narzędzia nie są przypadkowymi słownikami.

### 20.5. Ma rejestr narzędzi

`TOOL_REGISTRY` działa jak whitelist.

### 20.6. Ma historię błędów

`errors_history` pozwala debugować ścieżkę wykonania.

### 20.7. Ma limit kroków

`max_steps` chroni przed przypadkową pętlą nieskończoną.

---

## 21. Ograniczenia obecnej wersji

### 21.1. Analiza zgłoszenia jest regułowa

Obecnie `analyze_ticket_node` nie używa LLM. To celowe na tym etapie.

W kolejnych lekcjach będzie można wymienić reguły na Structured Outputs.

### 21.2. Router workflow jest ręczny

`run_workflow` sam sprawdza `next_step` przez `if/elif`.

W LangGraph zastąpimy to grafem.

### 21.3. `tool_args` i `tool_result` są słownikami

To jest praktyczne, ale produkcyjnie można rozważyć bardziej typowane modele stanu.

### 21.4. Brak testów jednostkowych

Plik jest gotowy do testowania, ale testy nie są jeszcze dodane.

### 21.5. Brak trwałego checkpointu

Stan jest tylko w pamięci programu. Później LangGraph pozwoli zapisywać i wznawiać workflow.

---

## 22. Typowe błędy początkującego

### Błąd 1: Trzymanie stanu w wielu luźnych zmiennych

Źle:

```python
category = "billing"
urgency = "high"
selected_tool = "calculate_refund_amount"
```

Lepiej:

```python
state = {
    **state,
    "category": "billing",
    "urgency": "high",
    "selected_tool": "calculate_refund_amount",
}
```

### Błąd 2: Node robi zbyt dużo

Źle:

```python
def analyze_and_execute_everything(state):
    ...
```

Lepiej:

```python
def analyze_ticket_node(state): ...
def choose_tool_node(state): ...
def execute_tool_node(state): ...
```

### Błąd 3: Brak historii błędów

Jeżeli workflow zwróci tylko:

```text
error
```

nie wiesz, co się stało.

Lepszy stan zawiera:

```python
"errors_history": ["Nie znaleziono ceny z walutą PLN."]
```

### Błąd 4: Wykonywanie dowolnych narzędzi

Źle:

```python
tool = globals()[tool_name]
```

Lepiej:

```python
tool = TOOL_REGISTRY.get(tool_name)
```

### Błąd 5: Brak limitu kroków

Każdy workflow, który może się zapętlić, powinien mieć limit.

---

## 23. Ćwiczenia praktyczne

### Ćwiczenie 1 — uruchomienie pliku

Uruchom:

```bash
python 03_state_workflow.py
```

Kryterium zaliczenia:

```text
next_step == "finish"
errors_history == []
tool_result zawiera refund_amount
```

---

### Ćwiczenie 2 — przypadek bez ceny

W `main()` usuń cenę `49.99 zł` z wiadomości klienta, ale zostaw informację o zwrocie.

Przykład:

```text
Pobrano mi opłatę podwójnie. Proszę o zwrot.
```

Oczekiwany efekt:

```text
next_step == "error"
errors_history zawiera informację o braku ceny w PLN
```

Cel: zobaczyć, że system potrafi zakończyć workflow błędem kontrolowanym.

---

### Ćwiczenie 3 — przypadek techniczny

Zmień wiadomość na:

```text
Aplikacja nie działa po zalogowaniu. Proszę o pomoc.
```

Oczekiwany efekt:

```text
category == "technical"
selected_tool == None
tool_result == None
next_step == "finish"
```

Cel: zrozumieć, że nie każde zgłoszenie wymaga narzędzia refundacyjnego.

---

### Ćwiczenie 4 — test walidacji argumentów

Celowo zmień `duplicated_charges` w `choose_tool_node` na `0`.

Oczekiwany efekt:

```text
next_step == "error"
errors_history zawiera błąd walidacji Pydantic
```

Cel: potwierdzić, że Pydantic zatrzymuje niepoprawne argumenty narzędzia.

---

### Ćwiczenie 5 — dodaj nowe narzędzie

Dodaj nowe narzędzie:

```python
def create_ticket_summary(raw_args: Mapping[str, Any]) -> dict[str, Any]:
    ...
```

Następnie dodaj je do:

```python
TOOL_REGISTRY = {
    "calculate_refund_amount": calculate_refund_amount,
    "create_ticket_summary": create_ticket_summary,
}
```

Kryterium zaliczenia: rozumiesz, że każde narzędzie musi być jawnie wpisane do rejestru.

---

## 24. Jak ten plik przejdzie do LangGraph

Obecnie masz ręczny runner:

```python
state = analyze_ticket_node(state)
state = choose_tool_node(state)
state = execute_tool_node(state)
```

W LangGraph będzie to wyglądało koncepcyjnie tak:

```text
START
  ↓
analyze_ticket
  ↓
choose_tool
  ↓
execute_tool
  ↓
END
```

A decyzje będą mogły przejść przez conditional edges:

```text
po choose_tool:
  jeśli selected_tool istnieje → execute_tool
  jeśli selected_tool == None → finish
  jeśli error → error
```

Najważniejsze: nie wyrzucisz obecnej pracy. Obecne node'y są już bliskie temu, czego wymaga LangGraph.

---

## 25. Wersja produkcyjna — kierunek rozwoju

Docelowo można rozdzielić plik na moduły:

```text
src/
  support_workflow/
    state.py
    models.py
    nodes.py
    tools.py
    runner.py
tests/
  test_state.py
  test_nodes.py
  test_tools.py
  test_runner.py
```

Podział odpowiedzialności:

| Plik | Odpowiedzialność |
|---|---|
| `state.py` | `SupportWorkflowState`, aliasy typów |
| `models.py` | modele Pydantic |
| `nodes.py` | node'y workflow |
| `tools.py` | narzędzia i `TOOL_REGISTRY` |
| `runner.py` | ręczny runner albo integracja z LangGraph |
| `tests/` | testy jednostkowe |

To jest profesjonalny kierunek rozwoju, ale nie należy robić go zbyt wcześnie. Najpierw trzeba dobrze zrozumieć wersję jednoplikową.

---

## 26. Minimalne testy, które warto dodać

Przykładowe testy:

```python
def test_extract_price_pln():
    assert extract_price_pln("Cena to 49.99 zł") == 49.99


def test_extract_price_pln_without_currency():
    assert extract_price_pln("Numer zgłoszenia 12345") is None


def test_refund_args_reject_negative_price():
    with pytest.raises(ValidationError):
        RefundArgs(monthly_price=-1, duplicated_charges=1)


def test_workflow_finishes_for_billing_refund():
    state = make_initial_state("Subskrypcja kosztuje 49.99 zł, pobrano podwójnie.")
    final_state = run_workflow(state)
    assert final_state["next_step"] == "finish"
    assert final_state["tool_result"]["refund_amount"] == 49.99
```

Testy są ważne, bo w systemach agentowych LLM może proponować rozwiązania, ale jakość powinny potwierdzać narzędzia.

---

## 27. Pytania kontrolne

Po przerobieniu pliku odpowiedz samodzielnie:

1. Czym jest `SupportWorkflowState`?
2. Dlaczego `state` jest lepszy niż historia rozmowy?
3. Co oznacza wzorzec `state -> node -> state`?
4. Dlaczego `choose_tool_node` nie powinien wykonywać narzędzia?
5. Po co istnieje `TOOL_REGISTRY`?
6. Co trafia do `errors_history`?
7. Co się stanie, gdy w zgłoszeniu nie będzie ceny w PLN?
8. Dlaczego `max_steps` jest potrzebne?
9. Który fragment tego pliku stanie się później node'em LangGraph?
10. Jak dodałbyś drugie narzędzie do workflow?

---

## 28. Kryterium zaliczenia lekcji

Lekcję uznaj za zaliczoną, gdy potrafisz:

- wyjaśnić, czym jest jawny stan workflow,
- wskazać wszystkie pola `SupportWorkflowState`,
- uruchomić `03_state_workflow.py`,
- zinterpretować `final_state`,
- celowo wywołać kontrolowany błąd workflow,
- wyjaśnić rolę `errors_history`,
- wyjaśnić rolę `next_step`,
- wyjaśnić, czym różni się wybór narzędzia od wykonania narzędzia,
- dodać prosty test jednostkowy,
- opisać, jak ten przepływ zostanie przeniesiony do LangGraph.

---

## 29. Najważniejsza myśl końcowa

Ten plik nie jest jeszcze „inteligentnym agentem”. To dobrze.

Najpierw budujemy stabilny szkielet:

```text
jawny stan
małe node'y
walidacja danych
kontrolowany rejestr narzędzi
historia błędów
limit kroków
```

Dopiero na takim szkielecie warto osadzać LLM i LangGraph.

W systemach agentowych model językowy nie powinien być kręgosłupem aplikacji. Kręgosłupem powinien być jawny, walidowalny workflow.
