# FAZA 2: LangGraph — Architektura Silnika (State Machine)

## 0. Cel fazy

Celem Fazy 2 jest przejście od pojedynczych, liniowych skryptów do **stanowego workflow opartego na grafie skierowanym**.

W Fazie 1 nauczyłeś się kontrolować pojedyncze wywołania LLM:

```text
LLM → JSON → Pydantic validation
LLM → tool call → walidacja argumentów → wykonanie funkcji
stabilny prompt → dynamiczne wejście
```

W Fazie 2 uczysz się łączyć te elementy w system:

```text
START
  ↓
node_1(state)
  ↓
node_2(state)
  ↓
router(state)
  ├── sukces → END
  ├── błąd → retry
  └── zbyt wiele prób → human_review
```

Najważniejsza zmiana mentalna:

> Nie budujesz już jednego skryptu ani jednego promptu. Budujesz graf stanu, w którym każdy node wykonuje małą, testowalną część pracy.

---

## 1. Co zbudujemy w tej fazie

W tej fazie zbudujesz minimalny system LangGraph dla ogólnego workflow aplikacyjnego.

Domena przykładowa:

```text
Obsługa zgłoszenia klienta / zadania aplikacyjnego
```

System będzie potrafił:

1. przyjąć tekst wejściowy,
2. zapisać go w jawnie zdefiniowanym stanie,
3. wykonać analizę w osobnym node,
4. wybrać następny krok,
5. wykonać narzędzie aplikacyjne,
6. obsłużyć błąd,
7. wykonać retry z limitem prób,
8. zakończyć workflow albo przejść do ręcznej interwencji.

Nie zajmujemy się tutaj sprzętem, PyVISA ani komendami laboratoryjnymi. Faza 2 jest ogólna: **LangGraph jako silnik workflow dla systemów agentowych**.

---

## 2. Wymagania wstępne

Przed rozpoczęciem Fazy 2 powinieneś rozumieć:

- czym jest model Pydantic,
- czym jest `TypedDict`,
- czym jest walidacja danych,
- czym jest Tool Calling,
- dlaczego argumenty narzędzi są niezaufane,
- dlaczego stan aplikacji jest lepszy niż historia rozmowy,
- jak działa wzorzec:

```text
state → node → state
```

W praktyce powinieneś mieć za sobą pliki:

```text
01_run.py
01_run.md
02_tool_calling.py
02_tool_calling.md
03_state_workflow.py
03_state_workflow.md
04_prompt_caching.py
04_prompt_caching.md
```

---

## 3. Główne pojęcia Fazy 2

### 3.1. StateGraph

`StateGraph` to podstawowy mechanizm LangGraph dla workflow, w którym węzły komunikują się przez wspólny stan.

Minimalna intuicja:

```python
from langgraph.graph import StateGraph

builder = StateGraph(MyState)
```

Graf nie powinien przechowywać ukrytych informacji poza stanem. Jeżeli coś ma wpływ na decyzje workflow, powinno znaleźć się w `state`.

---

### 3.2. State

Stan to jawny kontrakt danych całego workflow.

Minimalny przykład:

```python
from typing import Literal, TypedDict


class SupportWorkflowState(TypedDict):
    user_input: str
    category: str | None
    selected_tool: str | None
    tool_result: dict | None
    retry_count: int
    errors_history: list[str]
    next_step: Literal["analyze", "tool", "finish", "retry", "human_review"]
```

Stan powinien przechowywać:

| Pole | Rola |
|---|---|
| `user_input` | pierwotne wejście użytkownika |
| `category` | wynik klasyfikacji lub analizy |
| `selected_tool` | narzędzie wybrane przez system |
| `tool_result` | wynik wykonania narzędzia |
| `retry_count` | licznik ponowień |
| `errors_history` | historia błędów |
| `next_step` | decyzja sterująca workflow |

---

### 3.3. Reducers

Domyślnie node zwracający wartość dla pola stanu zwykle nadpisuje to pole.

Dla logów, historii błędów i list wiadomości często chcemy innego zachowania:

```text
nowy błąd ma zostać dopisany do listy,
a nie zastąpić całą listę błędów.
```

Do tego służą reduktory.

Przykład koncepcyjny:

```python
import operator
from typing import Annotated, TypedDict


class SupportWorkflowState(TypedDict):
    errors_history: Annotated[list[str], operator.add]
```

Dzięki temu gdy node zwróci:

```python
{"errors_history": ["Błąd walidacji argumentów narzędzia"]}
```

LangGraph może połączyć tę listę z dotychczasową historią, zamiast ją nadpisać.

To jest ważne dla:

- `errors_history`,
- `messages`,
- logów narzędzi,
- list wykonanych kroków,
- śladów audytowych.

---

### 3.4. Nodes

Node to zwykła funkcja Pythona wykonująca jeden krok workflow.

Przykład:

```python
def analyze_ticket_node(state: SupportWorkflowState) -> dict:
    user_input = state["user_input"]

    if "faktura" in user_input.lower() or "opłata" in user_input.lower():
        return {
            "category": "billing",
            "next_step": "tool",
        }

    return {
        "category": "general",
        "next_step": "finish",
    }
```

Profesjonalny node powinien:

- mieć jedną odpowiedzialność,
- przyjmować stan,
- zwracać aktualizację stanu,
- nie ukrywać decyzji w zmiennych globalnych,
- nie wykonywać zbyt wielu zadań naraz,
- dać się przetestować jednostkowo.

---

### 3.5. Edges

Edge to połączenie między node’ami.

Przykład liniowego przepływu:

```python
from langgraph.graph import START, END

builder.add_edge(START, "analyze_ticket")
builder.add_edge("analyze_ticket", "execute_tool")
builder.add_edge("execute_tool", END)
```

To odpowiada przepływowi:

```text
START → analyze_ticket → execute_tool → END
```

Na początku uczymy się zwykłych krawędzi, ponieważ są najprostsze i pozwalają zrozumieć mechanikę grafu.

---

### 3.6. Conditional Edges

Conditional edges pozwalają podejmować decyzję o następnym kroku na podstawie stanu.

Przykład:

```python
from typing import Literal


def route_after_tool(
    state: SupportWorkflowState,
) -> Literal["finish", "retry", "human_review"]:
    if state["next_step"] == "finish":
        return "finish"

    if state["retry_count"] < 3:
        return "retry"

    return "human_review"
```

Potem router podłącza się do grafu:

```python
builder.add_conditional_edges(
    "execute_tool",
    route_after_tool,
    {
        "finish": END,
        "retry": "analyze_ticket",
        "human_review": "human_review",
    },
)
```

To jest fundament pętli auto-healingu:

```text
ToolExecutor
  ↓
router
  ├── PASS → END
  ├── FAIL + retry_count < 3 → wróć do poprawki
  └── FAIL + retry_count >= 3 → human_review
```

---

## 4. Zakres lekcji w Fazie 2

### Lekcja 05 — Minimalny `StateGraph`

**Pliki:**

```text
05_langgraph_minimal_stategraph.py
05_langgraph_minimal_stategraph.md
```

**Cel:**

Zamienić ręczny workflow:

```python
state = analyze_node(state)
state = choose_tool_node(state)
state = execute_tool_node(state)
```

na graf:

```text
START → analyze → choose_tool → execute_tool → END
```

**Co musisz opanować:**

- instalacja LangGraph,
- import `StateGraph`, `START`, `END`,
- definicja `TypedDict` state,
- `add_node`,
- `add_edge`,
- `compile`,
- `invoke`.

**Kryterium zaliczenia:**

Uruchamiasz plik i otrzymujesz końcowy stan z:

```json
{
  "next_step": "finish",
  "errors_history": []
}
```

---

### Lekcja 06 — Reducers i historia błędów

**Pliki:**

```text
06_langgraph_reducers.py
06_langgraph_reducers.md
```

**Cel:**

Zrozumieć, jak dopisywać błędy i logi do stanu, zamiast je nadpisywać.

**Co musisz opanować:**

- `typing.Annotated`,
- `operator.add`,
- różnica między overwrite a append,
- projektowanie `errors_history`,
- projektowanie `execution_log`.

**Przykład:**

```python
import operator
from typing import Annotated, TypedDict


class WorkflowState(TypedDict):
    errors_history: Annotated[list[str], operator.add]
    execution_log: Annotated[list[str], operator.add]
```

**Kryterium zaliczenia:**

Dwa różne node’y dodają wpisy do `errors_history`, a finalny stan zawiera oba wpisy.

---

### Lekcja 07 — Conditional Edges i routery

**Pliki:**

```text
07_langgraph_conditional_edges.py
07_langgraph_conditional_edges.md
```

**Cel:**

Nauczyć się sterować przepływem grafu na podstawie stanu.

**Co musisz opanować:**

- funkcja routera,
- `add_conditional_edges`,
- wartości typu `Literal`,
- mapowanie decyzji na node’y,
- rozdzielenie logiki pracy od logiki routingu.

**Przykład decyzji:**

```text
jeżeli category == "billing" → billing_tool
jeżeli category == "technical" → technical_tool
w przeciwnym razie → finish
```

**Kryterium zaliczenia:**

Ten sam graf dla różnych wejść przechodzi różnymi ścieżkami.

---

### Lekcja 08 — Retry loop i limit prób

**Pliki:**

```text
08_langgraph_retry_loop.py
08_langgraph_retry_loop.md
```

**Cel:**

Zbudować pierwszą kontrolowaną pętlę auto-naprawy.

**Co musisz opanować:**

- `retry_count`,
- `max_retries`,
- statusy `PASS`, `FAIL`, `NEEDS_HUMAN`,
- unikanie nieskończonych pętli,
- przejście do `human_review`.

**Przykład przepływu:**

```text
execute_tool
  ↓
check_result
  ├── PASS → finish
  ├── FAIL + retry_count < max_retries → repair
  └── FAIL + retry_count >= max_retries → human_review
```

**Kryterium zaliczenia:**

Graf nigdy nie wykonuje nieskończonej pętli. Po przekroczeniu limitu prób kończy się stanem:

```json
{
  "next_step": "human_review"
}
```

---

### Lekcja 09 — Human Review Node

**Pliki:**

```text
09_langgraph_human_review_node.py
09_langgraph_human_review_node.md
```

**Cel:**

Dodać node reprezentujący ręczną interwencję człowieka.

**Co musisz opanować:**

- status `NEEDS_HUMAN`,
- zapis przyczyny eskalacji,
- oddzielenie automatycznej decyzji od decyzji człowieka,
- projektowanie pola `human_feedback`.

**Uwaga:**

Na tym etapie human review będzie zasymulowany jako zwykły node. Prawdziwe breakpointy i wznawianie pracy pojawią się później.

**Kryterium zaliczenia:**

Gdy system przekroczy limit prób, finalny stan zawiera:

```json
{
  "qa_status": "NEEDS_HUMAN",
  "human_feedback": null
}
```

---

## 5. Standard architektoniczny Fazy 2

Każdy node powinien być opisany według wzorca:

| Pole | Opis |
|---|---|
| Nazwa | techniczna nazwa node’a |
| Rola | za co odpowiada |
| Wejście | jakie pola stanu czyta |
| Wyjście | jakie pola stanu aktualizuje |
| Ograniczenia | czego node nie może robić |
| Kryterium sukcesu | kiedy node działa poprawnie |
| Walidacja | jak testujemy node |

Przykład:

```text
Nazwa: execute_tool_node
Rola: wykonuje narzędzie wybrane przez choose_tool_node
Wejście: selected_tool, tool_args
Wyjście: tool_result, errors_history, next_step
Ograniczenia: wykonuje tylko narzędzia z TOOL_REGISTRY
Kryterium sukcesu: wynik narzędzia zapisany w tool_result
Walidacja: test z poprawnymi i błędnymi argumentami
```

---

## 6. Minimalna struktura katalogów dla Fazy 2

Proponowana struktura:

```text
project/
  README.md
  pyproject.toml

  lessons/
    05_langgraph_minimal_stategraph.py
    06_langgraph_reducers.py
    07_langgraph_conditional_edges.py
    08_langgraph_retry_loop.py
    09_langgraph_human_review_node.py

  docs/
    05_langgraph_minimal_stategraph.md
    06_langgraph_reducers.md
    07_langgraph_conditional_edges.md
    08_langgraph_retry_loop.md
    09_langgraph_human_review_node.md

  tests/
    test_05_minimal_stategraph.py
    test_06_reducers.py
    test_07_conditional_edges.py
    test_08_retry_loop.py
```

Na początku możesz trzymać pliki w jednym katalogu. Gdy liczba lekcji urośnie, przenieś kod i dokumentację do osobnych folderów.

---

## 7. Wymagane zależności

Minimalnie:

```bash
pip install langgraph
```

Rekomendowane dla jakości kodu:

```bash
pip install pytest ruff
```

Opcjonalnie:

```bash
pip install pydantic
```

Jeżeli używasz Pydantic state lub walidujesz wejścia/wyjścia node’ów.

---

## 8. Minimalny przykład docelowy Fazy 2

Na koniec Fazy 2 powinieneś rozumieć taki szkielet:

```python
from typing import Literal, TypedDict

from langgraph.graph import END, START, StateGraph


class WorkflowState(TypedDict):
    user_input: str
    category: str | None
    retry_count: int
    max_retries: int
    next_step: Literal["finish", "retry", "human_review"]


def analyze_node(state: WorkflowState) -> dict:
    return {"category": "billing"}


def execute_node(state: WorkflowState) -> dict:
    return {"next_step": "finish"}


def route_after_execute(
    state: WorkflowState,
) -> Literal["finish", "retry", "human_review"]:
    if state["next_step"] == "finish":
        return "finish"

    if state["retry_count"] < state["max_retries"]:
        return "retry"

    return "human_review"


builder = StateGraph(WorkflowState)
builder.add_node("analyze", analyze_node)
builder.add_node("execute", execute_node)

builder.add_edge(START, "analyze")
builder.add_edge("analyze", "execute")
builder.add_conditional_edges(
    "execute",
    route_after_execute,
    {
        "finish": END,
        "retry": "analyze",
        "human_review": END,
    },
)

graph = builder.compile()

result = graph.invoke(
    {
        "user_input": "Mam problem z opłatą.",
        "category": None,
        "retry_count": 0,
        "max_retries": 3,
        "next_step": "retry",
    }
)

print(result)
```

---

## 9. Typowe błędy w Fazie 2

### Błąd 1: Node robi za dużo

Źle:

```text
jeden node analizuje, wybiera narzędzie, wykonuje je, ocenia wynik i generuje raport
```

Dobrze:

```text
analyze_node
choose_tool_node
execute_tool_node
evaluate_result_node
```

---

### Błąd 2: Ukryty stan

Źle:

```python
GLOBAL_RETRY_COUNT = 0
```

Dobrze:

```python
state["retry_count"]
```

---

### Błąd 3: Brak limitu pętli

Źle:

```text
jeżeli błąd, wracaj do poprawki bez limitu
```

Dobrze:

```text
jeżeli błąd i retry_count < max_retries, ponów
w przeciwnym razie przejdź do human_review
```

---

### Błąd 4: Router wykonuje pracę

Źle:

```python
def router(state):
    result = expensive_tool_call()
    ...
```

Dobrze:

```python
def router(state):
    return "next_node_name"
```

Router ma decydować, a nie wykonywać główną pracę.

---

### Błąd 5: Nadpisywanie historii błędów

Źle:

```python
return {"errors_history": ["nowy błąd"]}
```

gdy oczekujesz zachowania poprzednich błędów bez reduktora.

Dobrze:

```python
errors_history: Annotated[list[str], operator.add]
```

albo ręczne dopisanie w node:

```python
return {
    "errors_history": state["errors_history"] + ["nowy błąd"]
}
```

---

## 10. Kryteria ukończenia Fazy 2

Faza 2 jest zaliczona, gdy potrafisz:

- zdefiniować globalny stan grafu jako `TypedDict`,
- wyjaśnić, które pola stanu powinny być nadpisywane, a które dopisywane,
- użyć reduktora dla listy błędów lub logów,
- napisać node jako funkcję `state -> partial update`,
- połączyć node’y przez `add_edge`,
- napisać router dla `add_conditional_edges`,
- zbudować pętlę retry z limitem prób,
- doprowadzić workflow do `END`,
- uniknąć ukrytego stanu,
- wyjaśnić, kiedy workflow powinien przejść do `human_review`.

---

## 11. Pytania kontrolne

1. Czym różni się zwykły edge od conditional edge?
2. Dlaczego node powinien zwracać tylko aktualizację stanu, a nie zawsze cały stan?
3. Co robi reduktor `operator.add` na polu listowym?
4. Dlaczego `errors_history` nie powinno być zwykłą zmienną globalną?
5. Dlaczego router nie powinien wykonywać narzędzia?
6. Jak zabezpieczyć graf przed nieskończoną pętlą?
7. Jakie pola powinien zawierać stan dla retry loop?
8. Kiedy workflow powinien przejść do `human_review`?

---

## 12. Kolejny etap po Fazie 2

Po ukończeniu Fazy 2 przechodzimy do:

```text
FAZA 3: Agenci, narzędzia wykonawcze i pętla Actor-Critic
```

W Fazie 3 połączymy:

- LLM jako agenta decyzyjnego,
- Tool Calling,
- rzeczywiste narzędzia programowe,
- QA/Critic node,
- retry loop,
- testy automatyczne,
- logi wykonania.

Faza 2 daje kręgosłup. Faza 3 doda inteligentne node’y i narzędzia wykonawcze.
