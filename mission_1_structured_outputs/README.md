# Faza 1 — Kontrola nad LLM: Pydantic, Structured Outputs, Tool Calling, Prompt Caching

## 0. Cel fazy

Celem Fazy 1 jest nauczenie się budowania aplikacji, w której model LLM nie zwraca chaotycznego tekstu, lecz dane i decyzje możliwe do sprawdzenia przez kod.

Po tej fazie powinieneś umieć:

- definiować kontrakty danych przez Pydantic,
- wymuszać odpowiedzi JSON lub schema-based structured outputs,
- walidować odpowiedzi modelu po stronie aplikacji,
- projektować małe, bezpieczne narzędzia aplikacyjne,
- pozwalać modelowi wybierać narzędzie, ale nie oddawać mu kontroli nad wykonaniem,
- przechowywać wynik działania w jawnym stanie workflow,
- rozumieć, kiedy warto stosować prompt caching dla długiego, powtarzalnego kontekstu.

Najważniejsza zasada tej fazy:

```text
LLM proponuje. Aplikacja waliduje, wykonuje i zapisuje wynik.
```

---

## 1. Zakres fazy

Faza 1 obejmuje cztery główne obszary:

| Obszar | Pytanie szkoleniowe | Efekt praktyczny |
|---|---|---|
| Structured Outputs | Jak zmusić model do zwrotu danych zamiast tekstu? | `01_run.py` i `TicketAnalysis` |
| Tool Calling | Jak pozwolić modelowi wybrać funkcję aplikacji? | `02_tool_calling.py` i bezpieczne narzędzie |
| Jawny stan workflow | Jak przekazywać wynik między etapami bez ukrytej pamięci? | `03_state_workflow.py` |
| Prompt Caching | Jak pracować z dużym, powtarzalnym kontekstem? | projekt cache'owalnych promptów i stabilnych prefiksów |

---

## 2. Materiały źródłowe do pobrania

Zapisz poniższe dokumenty w katalogu:

```text
docs/ai_workflow/
```

### 2.1. OpenAI — Structured Outputs

Link:

```text
https://platform.openai.com/docs/guides/structured-outputs
```

Zapisz jako:

```text
docs/ai_workflow/01_openai_structured_outputs.md
```

Po co:

- rozumiesz różnicę między JSON mode a schema adherence,
- uczysz się, że sam poprawny JSON nie wystarcza,
- widzisz, że schemat powinien określać wymagane pola, typy i dozwolone wartości.

Minimalny efekt nauki:

```text
Potrafię wyjaśnić różnicę między:
- response_format={"type": "json_object"}
- response_format / text.format z JSON Schema i strict schema adherence
- walidacją Pydantic po stronie aplikacji
```

---

### 2.2. OpenAI — Function Calling / Tool Calling

Link:

```text
https://platform.openai.com/docs/guides/function-calling
```

Zapisz jako:

```text
docs/ai_workflow/02_openai_function_calling.md
```

Po co:

- rozumiesz, że model nie wykonuje funkcji samodzielnie,
- uczysz się definiować narzędzia przez schemat argumentów,
- uczysz się pętli: model wybiera narzędzie → aplikacja waliduje → aplikacja wykonuje → wynik wraca do workflow.

Minimalny efekt nauki:

```text
Potrafię wyjaśnić, dlaczego tool call jest żądaniem wykonania funkcji, a nie wykonaniem funkcji.
```

---

### 2.3. Pydantic — Concepts & Models

Link:

```text
https://docs.pydantic.dev/latest/concepts/models/
```

Zapisz jako:

```text
docs/ai_workflow/03_pydantic_concepts_models.md
```

Po co:

- uczysz się modelować dane jako klasy dziedziczące po `BaseModel`,
- rozumiesz pola, typy, `Field`, walidację, serializację i JSON Schema,
- przygotowujesz się do używania Pydantic jako kontraktu danych dla LLM, narzędzi i stanu workflow.

Minimalny efekt nauki:

```text
Potrafię zaprojektować model Pydantic dla wejścia, wyjścia i argumentów narzędzia.
```

---

### 2.4. Anthropic — Prompt Caching

Link:

```text
https://docs.anthropic.com/en/docs/build-with-claude/prompt-caching
```

Zapisz jako:

```text
docs/ai_workflow/04_anthropic_prompt_caching.md
```

Po co:

- rozumiesz, że duży, stabilny kontekst można cache'ować,
- uczysz się rozdzielać stabilny prefiks promptu od zmiennego wejścia użytkownika,
- przygotowujesz się do kosztowo rozsądnego RAG i pracy z dużą dokumentacją.

Minimalny efekt nauki:

```text
Potrafię wskazać, które części promptu są stabilne, a które powinny być zmienne.
```

---

## 3. Lekcje praktyczne Fazy 1

### Lekcja 01 — Structured Outputs + Pydantic

Pliki:

```text
01_run.py
01_run.md
```

Cel:

```text
Model ma zwrócić dane w strukturze zgodnej z Pydantic, a aplikacja ma je zwalidować.
```

Zakres:

- `BaseModel`,
- `Field`,
- `model_json_schema()`,
- JSON mode,
- czyszczenie odpowiedzi z Markdown,
- `model_validate_json(...)`,
- obsługa błędów walidacji.

Kryterium zaliczenia:

```text
Potrafisz wyjaśnić różnicę między surowym tekstem LLM, JSON-em i obiektem Pydantic.
```

---

### Lekcja 02 — Tool Calling jako kontrolowane narzędzia aplikacji

Pliki:

```text
02_tool_calling.py
02_tool_calling.md
```

Cel:

```text
Model może zaproponować użycie narzędzia, ale Python waliduje argumenty i wykonuje funkcję.
```

Zakres:

- projektowanie małych narzędzi,
- modele argumentów narzędzia,
- modele wyniku narzędzia,
- whitelist/rejestr narzędzi,
- brak narzędzi typu `do_anything`,
- walidacja argumentów przed wykonaniem.

Kryterium zaliczenia:

```text
Potrafisz wyjaśnić, dlaczego argumenty tool call są niezaufane, dopóki nie przejdą walidacji.
```

---

### Lekcja 03 — Jawny stan workflow

Pliki:

```text
03_state_workflow.py
03_state_workflow.md
```

Cel:

```text
Nauczyć się przekazywać wynik między etapami przez jawny, typowany stan.
```

Zakres:

- `TypedDict`,
- `Literal`,
- `errors_history`,
- `next_step`,
- node jako funkcja `state -> state`,
- prosty runner workflow,
- przygotowanie pod `StateGraph`.

Kryterium zaliczenia:

```text
Potrafisz narysować przepływ: state → analyze_node → state → tool_node → state.
```

---

### Lekcja 04 — Prompt Caching i stabilne prefiksy

Proponowane pliki:

```text
04_prompt_caching_design.md
04_prompt_caching_demo.py
```

Cel:

```text
Zrozumieć, jak projektować prompty, żeby kosztownie przetwarzane części były stabilne i możliwe do cache'owania.
```

Zakres:

- stabilny system prompt,
- stałe instrukcje agenta,
- duży kontekst jako prefiks,
- zmienne wejście użytkownika jako suffix,
- cache invalidation,
- kiedy caching ma sens,
- kiedy caching nie daje korzyści.

Minimalny przykład mentalny:

```text
[stabilne instrukcje + dokumentacja + definicje narzędzi]  ← część cache'owalna
[aktualne pytanie użytkownika]                             ← część zmienna
```

Kryterium zaliczenia:

```text
Potrafisz wskazać, dlaczego zmiana system promptu może unieważnić cache, a zmiana samego pytania użytkownika nie musi unieważniać stabilnego prefiksu.
```

---

## 4. Standard lekcji generowanych na podstawie tego README

Każda lekcja w tej fazie powinna mieć tę samą strukturę:

```markdown
# Numer i tytuł lekcji

## 0. Najkrótsza odpowiedź techniczna
## 1. Cel lekcji
## 2. Intuicja
## 3. Miejsce w architekturze systemów agentowych
## 4. Minimalny przykład
## 5. Wersja bardziej profesjonalna
## 6. Typowe błędy
## 7. Ćwiczenia praktyczne
## 8. Pytania kontrolne
## 9. Kryterium zaliczenia
## 10. Następny krok
```

---

## 5. Standard plików `.py` w tej fazie

Każdy plik Python powinien spełniać minimalny standard:

- ma mały, jednoznaczny cel,
- nie miesza wszystkiego w jednym wielkim promptcie,
- używa Pydantic albo `TypedDict` tam, gdzie ma to sens,
- oddziela dane wejściowe od logiki,
- ma funkcję `main()`,
- używa `if __name__ == "__main__":`,
- można go uruchomić samodzielnie,
- można go później przenieść jako node do LangGraph,
- przechodzi formatowanie i lintowanie.

Zalecane komendy:

```bash
ruff format .
ruff check .
python 01_run.py
python 02_tool_calling.py
python 03_state_workflow.py
```

---

## 6. Minimalna architektura po Fazie 1

Po tej fazie projekt powinien przypominać:

```text
.
├── README.md
├── 01_run.py
├── 01_run.md
├── 02_tool_calling.py
├── 02_tool_calling.md
├── 03_state_workflow.py
├── 03_state_workflow.md
├── 04_prompt_caching_design.md
├── docs/
│   └── ai_workflow/
│       ├── 01_openai_structured_outputs.md
│       ├── 02_openai_function_calling.md
│       ├── 03_pydantic_concepts_models.md
│       └── 04_anthropic_prompt_caching.md
└── pyproject.toml
```

---

## 7. Antywzorce zakazane w Fazie 1

Unikaj:

- traktowania odpowiedzi modelu jako prawdy,
- parsowania swobodnego tekstu przez `split()` i przypadkowe regexy,
- narzędzi typu `run_anything(command: str)`,
- jednego wielkiego promptu,
- jednego wielkiego agenta,
- ukrytego stanu w historii rozmowy,
- braku walidacji argumentów narzędzi,
- braku `errors_history`,
- braku kryteriów sukcesu lekcji.

Promuj:

- Pydantic,
- JSON Schema,
- `TypedDict`,
- jawny stan,
- małe funkcje,
- małe narzędzia,
- rejestr narzędzi,
- walidację po stronie aplikacji,
- deterministyczne renderowanie Markdown,
- testowalne kroki.

---

## 8. Checklista ukończenia Fazy 1

Faza 1 jest zaliczona, gdy potrafisz:

- [ ] wyjaśnić różnicę między JSON mode a Structured Outputs,
- [ ] stworzyć model Pydantic z ograniczeniami `Literal`, `Field`, `min_length`, `gt`, `ge`,
- [ ] wygenerować JSON Schema z modelu Pydantic,
- [ ] zwalidować odpowiedź LLM przez `model_validate_json`,
- [ ] zaprojektować bezpieczne narzędzie aplikacyjne,
- [ ] zwalidować argumenty narzędzia przed wykonaniem,
- [ ] zapisać wynik działania w jawnym stanie workflow,
- [ ] wyjaśnić, co powinno trafiać do `errors_history`,
- [ ] rozdzielić stabilny prefiks promptu od zmiennego wejścia,
- [ ] wskazać, kiedy prompt caching ma sens,
- [ ] uruchomić `ruff format` i `ruff check`,
- [ ] przygotować się do Lekcji 05: pierwszy minimalny `StateGraph` w LangGraph.

---

## 9. Następna faza

Po Fazie 1 przejdź do:

```text
Faza 2 — LangGraph: StateGraph, nodes, edges, conditional edges i retry loops
```

Pierwsza lekcja kolejnej fazy:

```text
05_langgraph_minimal_stategraph.py
05_langgraph_minimal_stategraph.md
```

Cel następnej fazy:

```text
Przenieść ręczny workflow state → node → state do prawdziwego grafu LangGraph.
```
