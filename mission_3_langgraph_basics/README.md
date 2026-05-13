# Faza 3: Środowisko Wykonawcze i Walidacja — The Sandbox

## Cel fazy

Celem Fazy 3 jest nauczenie systemu agentowego **bezpiecznego sprawdzania i uruchamiania kodu wygenerowanego przez LLM**.

W Fazie 1 nauczyłeś się kontrolować odpowiedzi modelu przez Pydantic, Structured Outputs, Tool Calling i stabilny kontekst.

W Fazie 2 nauczyłeś się organizować przepływ pracy jako graf stanu: `StateGraph`, node’y, edges, conditional edges, retry loops i podstawowe mechanizmy eskalacji.

W Fazie 3 dodajesz warstwę wykonawczą:

```text
LLM proponuje kod lub zmianę
        ↓
system wykonuje statyczną analizę AST
        ↓
system uruchamia deterministyczne narzędzia CLI
        ↓
system zbiera stdout/stderr/exit_code/raporty
        ↓
graf decyduje: PASS / RETRY / NEEDS_HUMAN / BLOCKED
```

Najważniejsza zasada:

> Kod wygenerowany przez LLM jest niezaufany, dopóki nie przejdzie statycznej analizy, testów, lintingu i kontroli wykonania.

---

## Zakres Fazy 3

Faza 3 obejmuje trzy główne obszary:

1. `subprocess` i orkiestrację narzędzi CLI,
2. analizę statyczną kodu przez `ast`,
3. izolację środowiska wykonawczego, opcjonalnie przez Docker.

Nie uczymy się tutaj już podstaw LangGraph. Zakładamy, że masz workflow z node’ami i routerami. Teraz uczymy się, co powinien robić **Tool Execution Node**.

---

## 3.1. Subprocess & CLI Orchestration

### Co musisz opanować

Musisz umieć uruchamiać z Pythona narzędzia takie jak:

```text
pytest
ruff
git diff --check
python -m compileall
mypy / pyright — opcjonalnie
```

oraz bezpiecznie przechwytywać:

```text
stdout
stderr
exit_code
czas wykonania
raport JSON
ścieżkę roboczą
komendę
status końcowy
```

### Dlaczego to ważne

LLM nie powinien sam oceniać, czy kod działa. LLM może zaproponować rozwiązanie, ale o jakości kodu powinny decydować narzędzia deterministyczne:

```text
pytest mówi, czy testy przeszły
ruff mówi, czy kod spełnia reguły jakości
git diff --check mówi, czy diff nie zawiera błędów whitespace
compileall mówi, czy kod w ogóle się kompiluje
```

### Minimalny kontrakt wyniku narzędzia

Każde uruchomienie narzędzia powinno zwracać jawny obiekt, np. Pydantic model:

```python
from pydantic import BaseModel, Field


class CommandResult(BaseModel):
    command: list[str]
    cwd: str
    exit_code: int
    stdout: str
    stderr: str
    timed_out: bool = False
    duration_seconds: float = Field(ge=0)
```

Ważne: nie przekazuj dalej tylko tekstu `stdout`. Przekazuj pełny wynik narzędzia.

### Zasady bezpieczeństwa dla subprocess

Promowane:

```python
subprocess.run(
    ["pytest", "--json-report"],
    cwd=project_dir,
    capture_output=True,
    text=True,
    timeout=60,
    check=False,
)
```

Unikane:

```python
subprocess.run("pytest && rm -rf tmp", shell=True)
```

Zasady:

- używaj listy argumentów, nie jednego stringa,
- domyślnie nie używaj `shell=True`,
- ustawiaj `cwd`,
- ustawiaj `timeout`,
- zapisuj `stdout`, `stderr`, `exit_code`,
- nigdy nie udawaj, że narzędzie zostało uruchomione,
- wynik narzędzia zapisuj w stanie grafu.

---

## 3.2. AST — Abstract Syntax Tree

### Co musisz opanować

Musisz umieć używać wbudowanego modułu `ast` do statycznej analizy kodu przed jego uruchomieniem.

Minimalny przepływ:

```text
kod wygenerowany przez LLM
        ↓
ast.parse(...)
        ↓
sprawdzenie struktury kodu
        ↓
decyzja: SAFE_TO_RUN / BLOCKED / NEEDS_REVIEW
```

### Dlaczego to ważne

AST pozwala szybko odpowiedzieć na pytania:

```text
Czy kod zawiera eval?
Czy kod zawiera exec?
Czy kod importuje os albo subprocess?
Czy kod używa shell=True?
Czy kod ma top-level side effects?
Czy kod definiuje oczekiwaną funkcję?
Czy kod zmienia pliki poza dozwolonym katalogiem?
Czy kod zawiera niedozwolone wywołania sieciowe?
```

To jest tańsze, szybsze i bardziej wiarygodne niż pytanie LLM:

```text
Czy ten kod jest bezpieczny?
```

### Przykładowe reguły AST dla zastosowań ogólnych

W tej fazie nie analizujemy specyficznych wzorców sprzętowych. Używamy reguł ogólnych:

```text
BLOCK:
- eval(...)
- exec(...)
- os.system(...)
- subprocess.run(..., shell=True)
- import socket
- import requests — jeśli workflow nie wymaga sieci
- open(..., "w") poza dozwolonym katalogiem
- pathlib.Path("/").rglob(...)
- top-level code wykonujący operacje poza definicjami funkcji/klas

REVIEW:
- import os
- import subprocess
- import shutil
- zapis plików
- usuwanie plików
- uruchamianie procesów
- dostęp do zmiennych środowiskowych

ALLOW:
- definicje funkcji
- definicje klas
- importy bibliotek dozwolonych
- czyste funkcje obliczeniowe
- testy jednostkowe w katalogu tests/
```

### Minimalny kontrakt wyniku AST

```python
from typing import Literal
from pydantic import BaseModel


class StaticAnalysisFinding(BaseModel):
    rule_id: str
    severity: Literal["INFO", "WARNING", "ERROR", "BLOCKER"]
    message: str
    line: int | None = None
    column: int | None = None


class StaticAnalysisResult(BaseModel):
    status: Literal["SAFE_TO_RUN", "NEEDS_REVIEW", "BLOCKED"]
    findings: list[StaticAnalysisFinding]
```

---

## 3.3. Isolation / Docker

### Co musisz opanować

Izolacja oznacza uruchamianie kodu wygenerowanego przez LLM w środowisku, które można łatwo odtworzyć i usunąć.

W wariancie minimalnym:

```text
tymczasowy katalog roboczy
brak sekretów
ograniczone pliki wejściowe
timeouty
brak shell=True
jawna lista dozwolonych komend
```

W wariancie mocniejszym:

```text
kontener Docker
read-only mount dla źródeł
oddzielny katalog wyników
brak sieci, jeśli nie jest potrzebna
limit CPU / RAM
użytkownik bez uprawnień root
automatyczne usuwanie kontenera
```

### Dlaczego to ważne

LLM może wygenerować kod z halucynacją lub niebezpiecznym efektem ubocznym, np.:

```python
import os
os.system("rm -rf /")
```

System nie może zakładać, że wygenerowany kod jest bezpieczny tylko dlatego, że wygląda poprawnie.

### Poziomy izolacji

| Poziom | Nazwa | Opis | Kiedy stosować |
|---|---|---|---|
| 0 | No execution | Kod tylko analizowany statycznie | Gdy kod jest podejrzany |
| 1 | Local safe commands | Tylko whitelistowane narzędzia, np. `ruff`, `pytest` | Nauka i małe projekty |
| 2 | Temporary workspace | Kod działa w katalogu tymczasowym | Testowanie wygenerowanych plików |
| 3 | Docker sandbox | Kod działa w kontenerze | Poważniejszy auto-healing |
| 4 | Human approval | Człowiek zatwierdza wykonanie | Operacje ryzykowne |

---

## Rekomendowana struktura lekcji Fazy 3

Faza 3 powinna generować lekcje od numeru `10`, zakładając że Faza 2 kończy się na lekcji `09`.

```text
10_subprocess_cli_orchestration.py
10_subprocess_cli_orchestration.md

11_command_result_schema.py
11_command_result_schema.md

12_ast_static_analysis.py
12_ast_static_analysis.md

13_safe_tool_executor_node.py
13_safe_tool_executor_node.md

14_docker_isolation_optional.py
14_docker_isolation_optional.md
```

---

## Lekcja 10 — Subprocess CLI Orchestration

### Cel

Nauczyć się uruchamiać bezpiecznie narzędzia CLI z Pythona i zbierać ich wynik w jawnej strukturze danych.

### Co zbudujemy

Skrypt:

```text
10_subprocess_cli_orchestration.py
```

który uruchamia:

```text
python --version
ruff --version
pytest --version
```

a następnie zapisuje wynik jako `CommandResult`.

### Kryteria sukcesu

Uczeń potrafi:

- użyć `subprocess.run(...)`,
- przechwycić `stdout` i `stderr`,
- odczytać `returncode`,
- obsłużyć timeout,
- nie używać `shell=True`,
- opisać, dlaczego wynik narzędzia musi być zapisany w stanie.

---

## Lekcja 11 — Command Result Schema

### Cel

Zamienić wynik CLI z nieustrukturyzowanego tekstu na walidowalny model Pydantic.

### Co zbudujemy

Modele:

```python
class CommandResult(BaseModel):
    ...


class ToolExecutionReport(BaseModel):
    ...
```

oraz funkcję:

```python
def run_command(command: list[str], cwd: Path, timeout_seconds: int) -> CommandResult:
    ...
```

### Kryteria sukcesu

Uczeń potrafi:

- odróżnić `stdout` od `stderr`,
- interpretować `exit_code`,
- zapisać raport wykonania jako JSON,
- użyć wyniku w LangGraph state.

---

## Lekcja 12 — AST Static Analysis

### Cel

Nauczyć się statycznie analizować kod Python przed jego uruchomieniem.

### Co zbudujemy

Skrypt:

```text
12_ast_static_analysis.py
```

który wykrywa:

```text
eval(...)
exec(...)
os.system(...)
subprocess.run(..., shell=True)
import socket
import requests
```

i zwraca `StaticAnalysisResult`.

### Kryteria sukcesu

Uczeń potrafi:

- użyć `ast.parse(...)`,
- przejść po drzewie przez `ast.walk(...)`,
- wykryć `ast.Call`,
- wykryć `ast.Import` i `ast.ImportFrom`,
- zwrócić listę findings,
- podjąć decyzję `SAFE_TO_RUN`, `NEEDS_REVIEW`, `BLOCKED`.

---

## Lekcja 13 — Safe Tool Executor Node

### Cel

Połączyć subprocess i AST z LangGraph.

### Co zbudujemy

Node:

```python
def static_analysis_node(state: WorkflowState) -> dict:
    ...


def tool_executor_node(state: WorkflowState) -> dict:
    ...


def qa_router(state: WorkflowState) -> Literal["pass", "retry", "human", "blocked"]:
    ...
```

### Przepływ

```text
GeneratedCode
    ↓
StaticAnalysisNode
    ↓
Router
    ├── BLOCKED → HumanReviewNode
    ├── SAFE_TO_RUN → ToolExecutorNode
    └── NEEDS_REVIEW → HumanReviewNode
```

### Kryteria sukcesu

Uczeń potrafi:

- zapisać wynik AST w stanie,
- zapisać wynik CLI w stanie,
- rozdzielić `BLOCKED`, `RETRY`, `PASS`,
- nie wykonywać kodu, który nie przeszedł analizy statycznej.

---

## Lekcja 14 — Docker Isolation Optional

### Cel

Zrozumieć, kiedy potrzebna jest izolacja kontenerowa i jak ją włączyć do workflow.

### Co zbudujemy

Minimalny koncept:

```text
projekt testowy
        ↓
kontener z Pythonem
        ↓
pytest / ruff w kontenerze
        ↓
raport JSON
        ↓
stan LangGraph
```

### Kryteria sukcesu

Uczeń potrafi:

- wyjaśnić, po co izolować kod,
- odróżnić analizę statyczną od wykonania w sandboxie,
- opisać ryzyka montowania katalogów,
- opisać, dlaczego kontener nie zastępuje walidacji AST,
- wskazać, kiedy potrzebna jest zgoda człowieka.

---

## Docelowy stan workflow po Fazie 3

Po Fazie 3 Twój system powinien umieć przechowywać w stanie między innymi:

```python
from typing import Literal, TypedDict


class WorkflowState(TypedDict):
    task_description: str
    generated_code: str | None
    static_analysis_status: Literal["SAFE_TO_RUN", "NEEDS_REVIEW", "BLOCKED"] | None
    static_analysis_findings: list[dict]
    command_results: list[dict]
    pytest_status: Literal["PASS", "FAIL", "ERROR", "NOT_RUN"] | None
    ruff_status: Literal["PASS", "FAIL", "ERROR", "NOT_RUN"] | None
    retry_count: int
    next_step: Literal["generate", "analyze", "execute", "retry", "human", "blocked", "finish"]
    errors_history: list[str]
```

---

## Główna pętla Fazy 3

```text
DeveloperAgent
    ↓
StaticAnalysisNode
    ↓
SafetyRouter
    ├── BLOCKED → HumanReviewNode
    ├── NEEDS_REVIEW → HumanReviewNode
    └── SAFE_TO_RUN
            ↓
      ToolExecutorNode
            ↓
      QAResultRouter
            ├── PASS → Finish
            ├── FAIL + retry_count < max_retries → DeveloperAgent
            └── FAIL + retry_count >= max_retries → HumanReviewNode
```

To jest praktyczny fundament dla auto-healingu.

---

## Kryteria ukończenia Fazy 3

Fazę 3 uznaj za ukończoną, gdy potrafisz:

- uruchomić narzędzie CLI przez `subprocess.run(...)`,
- przechwycić `stdout`, `stderr`, `exit_code` i timeout,
- zapisać wynik narzędzia w modelu Pydantic,
- uruchomić `pytest`, `ruff` i `git diff --check` z Pythona,
- użyć `ast.parse(...)` do analizy kodu,
- wykryć co najmniej pięć antywzorców bezpieczeństwa przez AST,
- zablokować wykonanie kodu z `eval`, `exec`, `os.system` albo `shell=True`,
- zapisać wynik analizy statycznej w stanie LangGraph,
- podjąć decyzję przez router: `PASS`, `RETRY`, `NEEDS_HUMAN`, `BLOCKED`,
- wyjaśnić, kiedy warto użyć Dockera,
- wyjaśnić, dlaczego Docker nie zastępuje walidacji i analizy statycznej.

---

## Typowe błędy

### Błąd 1: Uruchamianie kodu przed analizą AST

Nie wykonuj kodu wygenerowanego przez LLM, zanim nie przejdziesz przez statyczną analizę.

### Błąd 2: `shell=True` jako domyślne rozwiązanie

`shell=True` zwiększa ryzyko wykonania niepożądanych komend. W tej fazie domyślnie go unikamy.

### Błąd 3: Brak timeoutu

Każde narzędzie uruchamiane przez subprocess powinno mieć limit czasu.

### Błąd 4: Zaufanie do stdout

`stdout` nie mówi sam, czy komenda się udała. Decyduje `exit_code` i kontrakt danego narzędzia.

### Błąd 5: Brak izolacji katalogów

Nie uruchamiaj wygenerowanego kodu w katalogu, w którym masz ważne dane, sekrety albo prywatne pliki.

### Błąd 6: Pytanie LLM o rzeczy, które mogą sprawdzić narzędzia

Nie pytaj LLM, czy testy przechodzą. Uruchom testy i przekaż LLM wynik.

---

## Materiały źródłowe do pobrania do `docs/ai_workflow/`

Przygotuj lub pobierz następujące pliki:

```text
08_python_subprocess_docs.md
09_python_ast_docs.md
10_pytest_json_report.md
11_ruff_docs.md
12_git_diff_check.md
13_docker_sandboxing.md
```

### Minimalna funkcja każdego źródła

| Plik | Funkcja w szkoleniu |
|---|---|
| `08_python_subprocess_docs.md` | bezpieczne uruchamianie procesów |
| `09_python_ast_docs.md` | statyczna analiza kodu |
| `10_pytest_json_report.md` | raportowanie testów do stanu |
| `11_ruff_docs.md` | linting i formatowanie jako narzędzie |
| `12_git_diff_check.md` | kontrola jakości diffów |
| `13_docker_sandboxing.md` | izolacja środowiska wykonawczego |

---

## Następna faza

Po Fazie 3 przejdź do:

```text
Faza 4: Actor-Critic i auto-healing
```

Tam połączysz:

```text
DeveloperAgent
QA/CriticAgent
StaticAnalysisNode
ToolExecutorNode
RetryRouter
HumanReviewNode
```

w pętlę automatycznej naprawy z limitem prób.
