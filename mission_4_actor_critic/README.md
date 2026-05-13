# Faza 4: Zaawansowane wzorce MAS — Human-in-the-Loop, Memory, Reflexion

## Cel fazy

Celem Fazy 4 jest przejście od prostych grafów i bezpiecznego uruchamiania narzędzi do **produkcyjnych wzorców Multi-Agent System**.

W Fazie 1 opanowałeś kontrolę nad wyjściem LLM: Structured Outputs, Pydantic, Tool Calling i Prompt Caching.

W Fazie 2 opanowałeś LangGraph jako maszynę stanów: `StateGraph`, node’y, edges, conditional edges i retry loops.

W Fazie 3 opanowałeś środowisko wykonawcze: `subprocess`, AST, raporty narzędzi, sandbox i walidację wygenerowanego kodu.

W Fazie 4 uczysz się trzech wzorców wymaganych dla systemów produkcyjnych:

```text
1. Human-in-the-Loop — człowiek zatwierdza ryzykowne kroki.
2. Checkpointing / Memory — graf zapisuje stan i może wznowić pracę.
3. Reflexion / Actor-Critic — system uczy się z błędów i generuje instrukcje naprawcze.
```

Najważniejsza zasada:

> Im większy wpływ działania agenta na świat zewnętrzny, tym silniejsza musi być kontrola: typy, logi, checkpointy, limity prób i decyzje człowieka.

---

## Ważne doprecyzowanie zakresu

Ta faza jest opisana pod **ogólne zastosowania systemów agentowych**, nie pod konkretny sprzęt laboratoryjny.

Przykłady ryzykownych operacji w zastosowaniach ogólnych:

```text
wysłanie e-maila do klienta
utworzenie zgłoszenia w systemie produkcyjnym
zmiana rekordu w bazie danych
uruchomienie migracji
zapisanie pliku w repozytorium
wykonanie deploya
usunięcie danych
utworzenie Pull Requesta
wysłanie raportu do przełożonego
```

Jeżeli kiedyś workflow dotyczyłby sprzętu lub środowiska fizycznego, mechanizmy Human-in-the-Loop i checkpointing byłyby jeszcze ważniejsze, ale nie jest to główny temat tej ścieżki.

---

## 4.1. Breakpoints / Interrupts — Human-in-the-Loop

### Co musisz opanować

Musisz umieć zatrzymać graf przed ryzykownym node’em i wznowić go dopiero po decyzji człowieka.

Przykład ogólny:

```text
DraftEmailNode
    ↓
HumanApprovalNode
    ↓
jeśli APPROVED → SendEmailNode
jeśli REJECTED → ReviseDraftNode
```

Albo:

```text
GeneratePatchNode
    ↓
RunTestsNode
    ↓
HumanReviewNode
    ↓
jeśli APPROVED → CreatePullRequestNode
jeśli REJECTED → DeveloperAgentNode
```

### Po co to jest

LLM może przygotować działanie, ale nie powinien samodzielnie wykonywać operacji o realnych skutkach.

Human-in-the-Loop jest potrzebny, gdy:

```text
operacja zmienia dane produkcyjne
operacja wysyła coś do człowieka
operacja kosztuje pieniądze
operacja może uszkodzić repozytorium
operacja usuwa dane
operacja publikuje treść
operacja przekracza uprawnienia automatycznego agenta
```

### Minimalny kontrakt decyzji człowieka

```python
from typing import Literal
from pydantic import BaseModel, Field


class HumanDecision(BaseModel):
    decision: Literal["APPROVED", "REJECTED", "NEEDS_CHANGES"]
    reviewer: str
    reason: str = Field(min_length=1)
    requested_changes: str | None = None
```

### Dane, które powinny trafić do stanu

```python
from typing import Literal, TypedDict


class WorkflowState(TypedDict):
    task_description: str
    proposed_action: dict | None
    risk_level: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    human_decision: dict | None
    human_feedback: str | None
    next_step: Literal["continue", "revise", "blocked", "finish"]
```

### Zasada

Nie projektuj workflow:

```text
LLM uznał, że trzeba wysłać e-mail → system wysyła e-mail automatycznie
```

Projektuj workflow:

```text
LLM przygotował e-mail
    ↓
system pokazuje treść człowiekowi
    ↓
człowiek zatwierdza / odrzuca / zgłasza poprawki
    ↓
graf wznawia pracę na podstawie jawnej decyzji
```

---

## 4.2. Checkpointers — trwała pamięć stanu

### Co musisz opanować

Musisz umieć podłączyć checkpointer do grafu LangGraph, aby stan workflow był zapisywany po krokach grafu.

Minimalnie:

```text
MemorySaver — do nauki i testów lokalnych
SQLite checkpointer — do lokalnej trwałości między uruchomieniami
Postgres checkpointer — do środowisk produkcyjnych
```

### Dlaczego to ważne

Bez checkpointingu długi workflow jest kruchy:

```text
agent wygenerował plan
uruchomił testy
dostał błąd
przygotował poprawkę
czekał na człowieka
proces się zatrzymał
stan znika
```

Z checkpointingiem:

```text
każdy istotny krok zapisuje stan
workflow ma thread_id
możesz wrócić do zadania następnego dnia
graf wie, gdzie skończył
człowiek może zatwierdzić krok i wznowić wykonanie
```

### Co powinien przechowywać stan

```python
class WorkflowState(TypedDict):
    user_request: str
    current_plan: dict | None
    generated_artifacts: list[dict]
    command_results: list[dict]
    critic_feedback: list[str]
    retry_count: int
    human_decision: dict | None
    next_step: str
    errors_history: list[str]
```

### Thread ID

Każdy uruchomiony workflow powinien mieć identyfikator wątku:

```text
thread_id = "ticket-2026-05-08-001"
thread_id = "repo-review-123"
thread_id = "report-generation-abc"
```

To pozwala rozróżnić wiele niezależnych uruchomień tego samego grafu.

### Różnica: pamięć rozmowy vs checkpoint

| Element | Pamięć rozmowy | Checkpoint grafu |
|---|---|---|
| Co przechowuje | zwykle wiadomości | pełny stan workflow |
| Czy jest typowany | zwykle nie | powinien być oparty o state schema |
| Czy pozwala wznowić graf | ograniczenie | tak |
| Czy nadaje się do audytu | słabo | dobrze |
| Czy wspiera Human-in-the-Loop | częściowo | tak |

---

## 4.3. Reflexion / Actor-Critic

### Co musisz opanować

Musisz umieć zaprojektować pętlę, w której:

```text
Actor generuje rozwiązanie
        ↓
Tool Node uruchamia testy / walidację
        ↓
Critic analizuje wynik
        ↓
Critic generuje instrukcję naprawczą
        ↓
Actor poprawia rozwiązanie
        ↓
pętla kończy się po sukcesie albo po limicie prób
```

### Role agentów

#### Actor / Developer Agent

Rola:

```text
Generuje rozwiązanie albo poprawkę na podstawie zadania i feedbacku.
```

Wejście:

```text
opis zadania
aktualny kod
wyniki testów
feedback krytyka
liczba prób
```

Wyjście:

```text
patch / kod / plan zmian / odpowiedź strukturalna
```

Ograniczenia:

```text
mała paczka zmian
brak ukrytych efektów ubocznych
zmiany muszą być testowalne
```

Walidacja:

```text
AST
ruff
pytest
git diff --check
review człowieka, gdy potrzeba
```

#### Critic / QA Agent

Rola:

```text
Analizuje wynik narzędzi i generuje krótką, konkretną instrukcję naprawczą.
```

Wejście:

```text
stdout
stderr
exit_code
raport pytest
raport ruff
diff
poprzednia instrukcja
```

Wyjście:

```python
class CriticFeedback(BaseModel):
    status: Literal["PASS", "RETRY", "NEEDS_HUMAN", "BLOCKED"]
    summary: str
    repair_instruction: str | None
    evidence: list[str]
```

Ograniczenia:

```text
nie zgaduje
opiera się na logach
nie generuje całej aplikacji od nowa
zwraca krótką instrukcję naprawczą
respektuje limit prób
```

### Dlaczego potrzebny jest limit prób

Bez limitu system może wejść w death loop:

```text
Koder → testy fail → Krytyk → Koder → testy fail → Krytyk → ...
```

Dlatego w stanie powinno być:

```python
retry_count: int
max_retries: int
```

Router powinien działać tak:

```text
jeśli PASS → finish
jeśli FAIL i retry_count < max_retries → retry
jeśli FAIL i retry_count >= max_retries → human_review
jeśli BLOCKED → human_review
```

---

## Rekomendowana struktura lekcji Fazy 4

Zakładamy, że Faza 3 kończy się na lekcji `14`.

```text
15_human_in_the_loop_interrupts.py
15_human_in_the_loop_interrupts.md

16_checkpointers_memory.py
16_checkpointers_memory.md

17_resume_with_thread_id.py
17_resume_with_thread_id.md

18_reflexion_actor_critic.py
18_reflexion_actor_critic.md

19_integrated_production_workflow.py
19_integrated_production_workflow.md
```

---

## Lekcja 15 — Human-in-the-Loop Interrupts

### Cel

Nauczyć się projektować workflow, który zatrzymuje się przed ryzykowną akcją i wymaga jawnej decyzji człowieka.

### Co zbudujemy

Minimalny workflow:

```text
GenerateDraftNode
    ↓
HumanReviewNode
    ↓
SendOrReviseRouter
    ├── APPROVED → FinalizeNode
    ├── NEEDS_CHANGES → ReviseDraftNode
    └── REJECTED → StopNode
```

### Przykładowa domena

```text
agent przygotowuje odpowiedź e-mail do klienta
człowiek zatwierdza treść
dopiero po zatwierdzeniu workflow kończy sprawę
```

Nie wysyłamy jeszcze realnego e-maila. Uczymy się decyzji człowieka jako danych w stanie.

### Kryteria sukcesu

Uczeń potrafi:

- wskazać node, przed którym workflow powinien się zatrzymać,
- zapisać decyzję człowieka jako Pydantic model,
- rozróżnić `APPROVED`, `REJECTED`, `NEEDS_CHANGES`,
- wznowić przepływ na podstawie decyzji,
- wyjaśnić, dlaczego LLM nie powinien sam zatwierdzać ryzykownych działań.

---

## Lekcja 16 — Checkpointers Memory

### Cel

Nauczyć się zapisywać stan grafu między krokami.

### Co zbudujemy

Minimalny graf z checkpointerem:

```text
START
  ↓
PlanNode
  ↓
WorkNode
  ↓
ReviewNode
  ↓
END
```

Stan będzie zawierał:

```python
messages: list[dict]
current_step: str
artifacts: list[dict]
errors_history: list[str]
```

### Kryteria sukcesu

Uczeń potrafi:

- wyjaśnić, czym jest checkpoint,
- odróżnić `MemorySaver` od trwałego backendu typu SQLite,
- uruchomić graf z `thread_id`,
- odczytać stan po przerwaniu workflow,
- wskazać, co powinno, a czego nie powinno być zapisane w stanie.

---

## Lekcja 17 — Resume with Thread ID

### Cel

Nauczyć się wznawiać workflow po przerwaniu.

### Co zbudujemy

Scenariusz:

```text
uruchom workflow
zatrzymaj się na HumanReview
zapisz thread_id
uruchom program ponownie
wczytaj thread_id
dodaj decyzję człowieka
wznów workflow
```

### Kryteria sukcesu

Uczeń potrafi:

- nadać workflow jawny `thread_id`,
- wyjaśnić, dlaczego `thread_id` jest częścią konfiguracji wykonania,
- wznowić workflow po przerwie,
- nie polegać wyłącznie na historii czatu.

---

## Lekcja 18 — Reflexion Actor-Critic

### Cel

Nauczyć się budować kontrolowaną pętlę auto-naprawczą.

### Co zbudujemy

Minimalny workflow:

```text
ActorNode
    ↓
StaticAnalysisNode
    ↓
ToolExecutorNode
    ↓
CriticNode
    ↓
RepairRouter
        ├── PASS → END
        ├── RETRY → ActorNode
        ├── NEEDS_HUMAN → HumanReviewNode
        └── BLOCKED → HumanReviewNode
```

### Kryteria sukcesu

Uczeń potrafi:

- rozdzielić rolę Actor i Critic,
- przekazać Criticowi logi narzędzi,
- wygenerować krótką instrukcję naprawczą,
- ograniczyć liczbę prób,
- eskalować do człowieka po przekroczeniu limitu.

---

## Lekcja 19 — Integrated Production Workflow

### Cel

Połączyć Human-in-the-Loop, checkpointing i Reflexion w jeden wzorzec produkcyjny.

### Co zbudujemy

Workflow dla ogólnej aplikacji agentowej:

```text
UserRequest
    ↓
PlannerAgent
    ↓
DeveloperAgent
    ↓
StaticAnalysisNode
    ↓
ToolExecutorNode
    ↓
CriticAgent
    ↓
QualityRouter
        ├── PASS → HumanApprovalNode
        ├── RETRY → DeveloperAgent
        ├── BLOCKED → HumanApprovalNode
        └── NEEDS_HUMAN → HumanApprovalNode
    ↓
FinalizeNode
```

### Kryteria sukcesu

Uczeń potrafi:

- połączyć trwały stan z pętlą naprawczą,
- zapisać wyniki testów i feedback człowieka w stanie,
- wznowić workflow po przerwaniu,
- wyjaśnić, gdzie kończy się automatyzacja, a zaczyna decyzja człowieka.

---

## Docelowy stan workflow po Fazie 4

```python
from typing import Literal, TypedDict


class AdvancedWorkflowState(TypedDict):
    user_request: str
    task_plan: dict | None
    generated_artifacts: list[dict]
    command_results: list[dict]
    static_analysis_findings: list[dict]
    critic_feedback: list[dict]
    retry_count: int
    max_retries: int
    human_decision: dict | None
    human_feedback: str | None
    checkpoint_thread_id: str
    qa_status: Literal["PASS", "FAIL", "NEEDS_HUMAN", "BLOCKED", "NOT_RUN"]
    next_step: Literal[
        "plan",
        "generate",
        "validate",
        "critic",
        "retry",
        "human_review",
        "finalize",
        "blocked",
        "finish",
    ]
    errors_history: list[str]
```

---

## Główna pętla Fazy 4

```text
PlannerAgent
    ↓
Actor / DeveloperAgent
    ↓
StaticAnalysisNode
    ↓
ToolExecutorNode
    ↓
CriticAgent
    ↓
QualityRouter
        ├── PASS → HumanApprovalNode
        ├── RETRY if retry_count < max_retries → Actor / DeveloperAgent
        ├── NEEDS_HUMAN → HumanApprovalNode
        └── BLOCKED → HumanApprovalNode
    ↓
FinalizeNode
```

---

## Arkusz umiejętności — wersja do skopiowania do Excela

Poniższy blok jest zapisany jako TSV, czyli kolumny są oddzielone tabulatorami. Skopiuj cały blok i wklej bezpośrednio do Excela, LibreOffice Calc albo Google Sheets.

```tsv
Kategoria (Technologia)	Konkretna umiejętność do opanowania	Priorytet	Status	Czas na naukę (szacunek)	Dowód zaliczenia
LLM API	Wymuszanie odpowiedzi w Pydantic / Structured Outputs	Krytyczny	[ ]	1-2 dni	Skrypt zwraca obiekt Pydantic i obsługuje ValidationError
LLM API	Definiowanie i obsługa Tool Calling / Function Calling	Krytyczny	[ ]	2-3 dni	Model proponuje tool call, Python waliduje argumenty i wykonuje funkcję
LLM API	Prompt Caching i projektowanie stabilnego kontekstu	Średni	[ ]	1 dzień	Prompt jest podzielony na stabilny prefiks i dynamiczny sufiks
LangGraph	Definiowanie State jako TypedDict / Pydantic z reduktorami	Krytyczny	[ ]	1 dzień	State zawiera errors_history i logi dopisywane przez reducer
LangGraph	Definiowanie Nodes i Edges — prosty DAG	Krytyczny	[ ]	2 dni	Graf wykonuje co najmniej trzy node'y w ustalonej kolejności
LangGraph	Conditional Edges — routery i pętle retry	Krytyczny	[ ]	2 dni	Router rozdziela PASS / RETRY / NEEDS_HUMAN / BLOCKED
LangGraph	Human-in-the-Loop / interrupts / breakpoints	Wysoki	[ ]	1-2 dni	Workflow zatrzymuje się przed ryzykownym krokiem i czeka na decyzję
LangGraph	Checkpointers — trwały stan i thread_id	Wysoki	[ ]	2 dni	Workflow można wznowić po przerwaniu na podstawie thread_id
LangGraph	Resume workflow po zatwierdzeniu człowieka	Wysoki	[ ]	1 dzień	Stan po decyzji człowieka prowadzi graf do poprawnej gałęzi
Python System	Subprocess — uruchamianie CLI i chwytanie stdout/stderr	Krytyczny	[ ]	1 dzień	CommandResult zawiera command, exit_code, stdout, stderr i timeout
Python Quality	AST — statyczna analiza wygenerowanego kodu	Wysoki	[ ]	3 dni	AST wykrywa eval, exec, os.system i shell=True
Python Quality	Ruff / pytest / git diff --check jako Tool Nodes	Krytyczny	[ ]	2 dni	Wyniki narzędzi są zapisane w stanie i sterują routerem
MAS Pattern	Reflexion / Actor-Critic loop	Wysoki	[ ]	3-5 dni	Critic analizuje logi i generuje instrukcję naprawczą
MAS Pattern	Limit prób i ochrona przed death loop	Krytyczny	[ ]	1 dzień	Po przekroczeniu max_retries workflow przechodzi do HumanReview
MAS Pattern	Projektowanie agentów przez role, wejścia, wyjścia i walidację	Krytyczny	[ ]	2 dni	Każdy agent ma opisany kontrakt i kryterium sukcesu
Production	Audytowalne logi decyzji człowieka i wyników narzędzi	Wysoki	[ ]	2 dni	Stan zawiera historię decyzji, logów i wyników walidacji
Production	Zasady automatyzacji ryzykownych operacji	Krytyczny	[ ]	1 dzień	Workflow jasno rozdziela akcje automatyczne i wymagające zgody
```

---

## Kryteria ukończenia Fazy 4

Fazę 4 uznaj za ukończoną, gdy potrafisz:

- zaprojektować node wymagający decyzji człowieka,
- zapisać decyzję człowieka jako typowany model danych,
- wznowić workflow po decyzji,
- wyjaśnić, czym różni się checkpoint od zwykłej historii rozmowy,
- uruchomić graf z `thread_id`,
- opisać różnicę między `MemorySaver`, SQLite i produkcyjnym backendem stanu,
- zaprojektować Actor-Critic loop,
- przekazać Criticowi rzeczywiste wyniki narzędzi,
- wygenerować instrukcję naprawczą opartą na logach,
- ograniczyć liczbę prób,
- eskalować do człowieka po przekroczeniu limitu,
- połączyć Human-in-the-Loop, checkpointing i Reflexion w jeden workflow.

---

## Typowe błędy

### Błąd 1: Human-in-the-Loop jako komentarz, nie mechanizm

Nie wystarczy napisać w promptcie:

```text
Zapytaj człowieka o zgodę.
```

Zgoda człowieka musi być reprezentowana jako dane w stanie i musi sterować routerem.

### Błąd 2: Checkpoint bez thread_id

Bez identyfikatora wątku trudno odróżnić jedno uruchomienie workflow od drugiego.

### Błąd 3: Reflexion bez logów narzędzi

Critic nie powinien zgadywać. Powinien analizować konkretne dowody: `stdout`, `stderr`, `exit_code`, raporty testów i diff.

### Błąd 4: Brak limitu prób

Każda pętla auto-naprawcza musi mieć limit. Brak limitu to ryzyko nieskończonego workflow.

### Błąd 5: Traktowanie checkpointa jako pamięci semantycznej

Checkpoint przechowuje stan wykonania grafu. Nie zastępuje RAG, bazy wiedzy ani długoterminowej pamięci semantycznej.

### Błąd 6: Automatyzacja działań produkcyjnych bez zatwierdzenia

Ryzykowne operacje powinny mieć jawny etap zatwierdzenia człowieka.

---

## Materiały źródłowe do `docs/ai_workflow/`

Przygotuj lub pobierz:

```text
14_langgraph_human_in_the_loop.md
15_langgraph_interrupts.md
16_langgraph_checkpointers.md
17_langgraph_persistence_sqlite.md
18_langgraph_thread_id_resume.md
19_reflexion_actor_critic.md
20_langgraph_reflection_example.md
```

### Minimalna funkcja każdego źródła

| Plik | Funkcja w szkoleniu |
|---|---|
| `14_langgraph_human_in_the_loop.md` | koncepcja człowieka jako kontrolera ryzyka |
| `15_langgraph_interrupts.md` | zatrzymywanie i wznawianie grafu |
| `16_langgraph_checkpointers.md` | trwałość stanu grafu |
| `17_langgraph_persistence_sqlite.md` | lokalny backend trwałego stanu |
| `18_langgraph_thread_id_resume.md` | identyfikowanie i wznawianie konkretnych workflow |
| `19_reflexion_actor_critic.md` | wzorzec Actor-Critic i feedback loop |
| `20_langgraph_reflection_example.md` | implementacyjny przykład pętli refleksji |

---

## Następna faza

Po Fazie 4 przejdź do:

```text
Faza 5: RAG, dokumentacja i integracja wiedzy
```

Tam połączysz:

```text
retrieval
chunking
źródła dokumentów
cytowanie
pamięć semantyczną
agentów pracujących nad dokumentacją
```

z grafem, checkpointami i kontrolą jakości.
