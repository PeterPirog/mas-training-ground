# 01_run.md — Misja 1: Structured Outputs + Pydantic

## 0. Najkrótsza odpowiedź techniczna

Plik `01_run.py` uczy pierwszej kluczowej umiejętności w systemach agentowych: **LLM nie ma zwracać luźnego tekstu, tylko dane o określonej strukturze**.

Ten skrypt:

1. definiuje oczekiwany format danych jako model `TicketAnalysis` w Pydantic,
2. zamienia ten model na schemat JSON,
3. wysyła do lokalnego lub kompatybilnego z OpenAI modelu LLM wiadomość klienta,
4. wymusza odpowiedź w formacie JSON,
5. oczyszcza odpowiedź z ewentualnych znaczników Markdown,
6. waliduje odpowiedź przez Pydantic,
7. drukuje poprawny, zwalidowany obiekt.

Główna lekcja: **LLM proponuje dane, ale Python je weryfikuje.**

---

## 1. Cel szkoleniowy tego pliku

Ten plik odpowiada pierwszej misji z `README.md`: **Wymuszenie Strukturalnych Wyjść**.

Celem nie jest jeszcze LangGraph, wielu agentów ani Tool Calling. Celem jest nauczyć się fundamentu, bez którego system multi-agentowy szybko staje się niekontrolowany:

> odpowiedź LLM musi być zamieniona na jawny, typowany, walidowalny obiekt programu.

W praktyce oznacza to przejście od:

```text
Model coś napisał, więc zakładam, że jest dobrze.
```

do:

```text
Model zwrócił JSON. Pydantic sprawdził pola. Dopiero teraz program uznaje wynik za poprawny.
```

To jest pierwszy krok w stronę architektury, w której później LangGraph będzie przenosił między node'ami nie chaotyczną historię rozmowy, ale **jawny stan workflow**.

---

## 2. Intuicja

Wyobraź sobie, że LLM jest pracownikiem analizującym zgłoszenia klientów. Gdy zapytasz go swobodnie:

```text
Przeanalizuj tę wiadomość.
```

może odpowiedzieć na wiele sposobów:

```text
Klient jest zdenerwowany i chodzi o płatność.
```

albo:

```text
To wygląda na problem billingowy. Priorytet wysoki.
```

albo:

```json
{
  "category": "billing",
  "urgency": "high",
  "sentiment": "negative",
  "summary": "Klient zgłasza podwójne naliczenie opłaty za subskrypcję."
}
```

Dla człowieka wszystkie trzy odpowiedzi są zrozumiałe. Dla programu tylko ostatnia jest wygodna, ponieważ ma stałe pola.

Dlatego w systemach agentowych nie powinieneś ufać temu, że model „ładnie odpowie”. Powinieneś zdefiniować strukturę i sprawdzić ją automatycznie.

---

## 3. Miejsce tego pliku w większej architekturze Multi-Agent System

W docelowym systemie Multi-Agent System z LangGraph każdy agent powinien mieć jasno określone:

- wejście,
- wyjście,
- ograniczenia,
- kryterium sukcesu,
- walidację.

`01_run.py` pokazuje najprostszy przypadek jednego agenta:

| Element | W tym skrypcie | W większym systemie LangGraph |
|---|---|---|
| Agent | analityk zgłoszeń | Requirements Analyst Agent / QA Agent / Developer Agent |
| Wejście | tekst e-maila klienta | fragment manuala, diff kodu, log pytest, opis zadania |
| Wyjście | JSON z kategorią, pilnością, sentymentem i streszczeniem | Pydantic model zapisany w stanie grafu |
| Walidacja | `TicketAnalysis.model_validate_json(...)` | walidacja Pydantic, testy, AST, ruff, pytest |
| Stan | lokalna zmienna `result` | jawny `TypedDict` albo Pydantic state w LangGraph |

To jest więc miniatura większej zasady:

> Agent nie „mówi”, tylko wytwarza dane, które system może sprawdzić i przekazać dalej.

---

## 4. Pełny przepływ danych w `01_run.py`

Schemat działania:

```text
.env
  ↓
load_dotenv()
  ↓
OpenAI(base_url, api_key)
  ↓
TicketAnalysis → JSON Schema
  ↓
wiadomość klienta
  ↓
chat.completions.create(...)
  ↓
surowa odpowiedź modelu jako tekst
  ↓
oczyszczenie z ```json / ```
  ↓
TicketAnalysis.model_validate_json(...)
  ↓
zwalidowany obiekt Pydantic
  ↓
wydruk wyniku
```

Najważniejszy fragment logiczny:

```python
result = TicketAnalysis.model_validate_json(raw_content)
```

To jest granica bezpieczeństwa. Przed tą linią masz tylko tekst wygenerowany przez model. Po tej linii masz obiekt Pythona zgodny z klasą `TicketAnalysis`.

---

## 5. Omówienie kodu krok po kroku

### 5.1. Importy

```python
import os
import json
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from openai import OpenAI
```

Znaczenie:

| Import | Rola |
|---|---|
| `os` | odczyt zmiennych środowiskowych, np. `OPENAI_BASE_URL` |
| `json` | zamiana schematu Pydantic na czytelny tekst JSON |
| `load_dotenv` | wczytanie pliku `.env` do środowiska programu |
| `BaseModel` | bazowa klasa Pydantic do definiowania struktury danych |
| `Field` | opis pól modelu, przydatny dla schematu JSON i instrukcji dla LLM |
| `OpenAI` | klient API zgodny z OpenAI |

Na tym etapie uczysz się, że konfiguracja modelu nie powinna być wpisana na sztywno w kodzie. Powinna być zewnętrzna, np. w `.env`.

---

### 5.2. Model Pydantic `TicketAnalysis`

```python
class TicketAnalysis(BaseModel):
    """Model danych reprezentujący przeanalizowane zgłoszenie od klienta."""

    category: str = Field(description="Kategoria zgłoszenia, np. 'billing', 'technical', 'sales'")
    urgency: str = Field(description="Priorytet: 'low', 'medium' lub 'high'")
    sentiment: str = Field(description="Nastawienie klienta: 'positive', 'neutral', 'negative'")
    summary: str = Field(description="Jednozdaniowe, zwięzłe podsumowanie problemu")
```

To jest centrum całego skryptu.

Model mówi programowi i LLM:

- wynik ma mieć pole `category`,
- wynik ma mieć pole `urgency`,
- wynik ma mieć pole `sentiment`,
- wynik ma mieć pole `summary`,
- każde pole ma być tekstem.

Przykład poprawnego wyniku:

```json
{
  "category": "billing",
  "urgency": "high",
  "sentiment": "negative",
  "summary": "Klient zgłasza podwójne naliczenie opłaty i żąda natychmiastowego zwrotu."
}
```

Przykład błędnego wyniku:

```json
{
  "typ": "billing",
  "pilnosc": "wysoka"
}
```

Dlaczego błędny? Bo nie zgadza się z modelem `TicketAnalysis`: brakuje pól `category`, `urgency`, `sentiment`, `summary`.

### Ważna uwaga architektoniczna

W obecnej wersji pola mają typ `str`, więc Pydantic sprawdza głównie obecność pól i ich typ tekstowy. Nie sprawdza jeszcze, czy `urgency` należy tylko do zbioru `low | medium | high`.

Wersja bardziej rygorystyczna mogłaby wyglądać tak:

```python
from typing import Literal
from pydantic import BaseModel, Field

class TicketAnalysis(BaseModel):
    category: Literal["billing", "technical", "sales"]
    urgency: Literal["low", "medium", "high"]
    sentiment: Literal["positive", "neutral", "negative"]
    summary: str = Field(min_length=5, max_length=240)
```

To jest kierunek produkcyjny: im bardziej krytyczne dane, tym mniej swobody dla modelu.

---

### 5.3. Funkcja `main()`

```python
def main() -> None:
    """Główna funkcja wykonująca zapytanie do lokalnego modelu LLM."""
```

`main()` jest punktem startowym logiki programu. Adnotacja `-> None` oznacza, że funkcja nie zwraca wartości, tylko wykonuje działania uboczne: odczytuje konfigurację, pyta model i drukuje wynik.

W późniejszej wersji agentowej nie zawsze będziemy drukować wynik. Częściej node LangGraph będzie zwracał zaktualizowany stan, np.:

```python
return {"ticket_analysis": result}
```

---

### 5.4. Wczytanie `.env`

```python
load_dotenv()
```

Ta linia ładuje zmienne z pliku `.env`.

Minimalny plik `.env` może wyglądać tak:

```env
OPENAI_BASE_URL=http://localhost:11434/v1
OPENAI_API_KEY=not-needed
MODEL_NAME=nazwa-twojego-modelu
```

Znaczenie:

| Zmienna | Znaczenie |
|---|---|
| `OPENAI_BASE_URL` | adres serwera LLM kompatybilnego z OpenAI API |
| `OPENAI_API_KEY` | klucz API; przy lokalnych modelach często symboliczny |
| `MODEL_NAME` | nazwa modelu, który ma obsłużyć zapytanie |

Jeżeli korzystasz z innego lokalnego serwera, np. vLLM, LM Studio albo innego endpointu zgodnego z OpenAI, wartości będą inne.

---

### 5.5. Utworzenie klienta OpenAI

```python
client = OpenAI(
    base_url=os.getenv("OPENAI_BASE_URL"),
    api_key=os.getenv("OPENAI_API_KEY", "not-needed")
)
model_name = os.getenv("MODEL_NAME")
```

Tu powstaje klient komunikujący się z modelem.

Ważne:

- `base_url` decyduje, gdzie wysyłane jest zapytanie,
- `api_key` jest pobierany z `.env`,
- `model_name` wskazuje konkretny model.

Potencjalny problem: jeżeli `MODEL_NAME` nie istnieje w `.env`, zmienna `model_name` będzie miała wartość `None`. Wtedy API może zwrócić błąd.

Wersja bardziej odporna:

```python
model_name = os.getenv("MODEL_NAME")
if not model_name:
    raise ValueError("Brakuje zmiennej MODEL_NAME w pliku .env")
```

---

### 5.6. Dane wejściowe: wiadomość klienta

```python
customer_email = (
    "Dzień dobry, piszę do was już trzeci raz! Z mojego konta pobrano podwójną "
    "opłatę za subskrypcję w tym miesiącu. Jestem wściekły, bo potrzebuję tych pieniędzy. "
    "Proszę o natychmiastowy zwrot na moją kartę z końcówką 4432, inaczej rezygnuję z usług."
)
```

To jest przykładowe wejście dla modelu.

Model powinien z niego wywnioskować:

| Cecha | Oczekiwana wartość |
|---|---|
| kategoria | `billing` |
| pilność | `high` |
| sentyment | `negative` |
| streszczenie | podwójna opłata i żądanie zwrotu |

Ważna uwaga: tekst zawiera końcówkę karty `4432`. W produkcyjnych systemach trzeba uważać na dane wrażliwe. W kolejnych etapach warto dodać filtr lub redakcję danych przed wysłaniem ich do modelu.

---

### 5.7. Generowanie schematu JSON z Pydantic

```python
schema_json = json.dumps(TicketAnalysis.model_json_schema(), indent=2)
```

Ta linia robi bardzo ważną rzecz:

1. `TicketAnalysis.model_json_schema()` generuje schemat JSON z modelu Pydantic,
2. `json.dumps(..., indent=2)` zamienia go na czytelny tekst,
3. ten tekst zostanie później wklejony do promptu systemowego.

Czyli zamiast ręcznie pisać:

```text
Zwróć JSON z polami category, urgency, sentiment, summary.
```

program generuje opis struktury automatycznie z klasy Pythona.

To zmniejsza ryzyko rozjazdu między kodem a promptem.

---

### 5.8. Wywołanie modelu LLM

```python
response = client.chat.completions.create(
    model=model_name,
    messages=[...],
    response_format={"type": "json_object"},
    temperature=0.1
)
```

To jest właściwe zapytanie do modelu.

#### `model=model_name`

Wskazuje model z `.env`.

#### `messages=[...]`

Lista wiadomości składa się z dwóch ról:

1. `system` — instrukcja nadrzędna,
2. `user` — konkretne zadanie z wiadomością klienta.

#### `response_format={"type": "json_object"}`

To mówi API, że odpowiedź ma być obiektem JSON.

Ważna uwaga: w tym skrypcie jest to **wymuszenie formatu JSON**, ale nie pełne, ścisłe wymuszenie całego schematu przez API. Schemat Pydantic jest przekazywany w treści promptu, a ostateczna kontrola odbywa się dopiero tutaj:

```python
TicketAnalysis.model_validate_json(raw_content)
```

Dlatego aktualna architektura to:

```text
miękkie prowadzenie modelu przez prompt + JSON mode + twarda walidacja Pydantic
```

To jest bardzo dobry etap szkoleniowy, ale nie należy mylić go z pełną gwarancją poprawności przed walidacją.

#### `temperature=0.1`

Niska temperatura ogranicza losowość odpowiedzi.

Przy zadaniach strukturalnych zwykle chcesz mało kreatywności, a dużo powtarzalności.

---

### 5.9. Prompt systemowy

```python
{
    "role": "system",
    "content": (
        "Jesteś analitykiem zgłoszeń. Zwracasz WYŁĄCZNIE czysty tekst w formacie JSON.\n"
        "Nie dodawaj żadnych powitań, komentarzy ani znaczników markdown.\n\n"
        f"Twój JSON musi ściśle pasować do tego schematu:\n{schema_json}"
    )
}
```

Ten prompt pełni rolę kontraktu z modelem.

Mówi:

- jaka jest rola modelu,
- że wynik ma być czystym JSON-em,
- że nie wolno dodawać Markdown,
- że JSON ma pasować do schematu.

To jest dobry wzorzec, ale pamiętaj: prompt nie jest walidatorem. Prompt prosi. Pydantic sprawdza.

---

### 5.10. Prompt użytkownika

```python
{
    "role": "user",
    "content": f"Przeanalizuj poniższą wiadomość i zwróć JSON:\n{customer_email}"
}
```

Ta wiadomość zawiera właściwe zadanie.

Warto zauważyć rozdzielenie odpowiedzialności:

| Rola | Co robi |
|---|---|
| `system` | ustala format, rolę i ograniczenia |
| `user` | przekazuje dane do analizy |

W większym systemie agentowym podobny podział będzie bardzo ważny. Instrukcja agenta powinna być stabilna, a dane wejściowe powinny być zmienną częścią stanu.

---

### 5.11. Odczyt surowej odpowiedzi

```python
raw_content = response.choices[0].message.content.strip()
```

Ta linia pobiera tekst wygenerowany przez model.

Na tym etapie `raw_content` może wyglądać tak:

```json
{"category":"billing","urgency":"high","sentiment":"negative","summary":"Klient zgłasza podwójne naliczenie opłaty."}
```

Ale niektóre modele mimo instrukcji mogą zwrócić:

```markdown
```json
{
  "category": "billing",
  "urgency": "high",
  "sentiment": "negative",
  "summary": "Klient zgłasza podwójne naliczenie opłaty."
}
```
```

Dlatego autor skryptu dodał kolejną sekcję zabezpieczającą.

---

### 5.12. Czyszczenie znaczników Markdown

```python
if raw_content.startswith("```json"):
    raw_content = raw_content[7:]
if raw_content.startswith("```"):
    raw_content = raw_content[3:]
if raw_content.endswith("```"):
    raw_content = raw_content[:-3]

raw_content = raw_content.strip()
```

To jest praktyczne zabezpieczenie przed sytuacją, w której model opakuje JSON w blok Markdown.

Dlaczego to potrzebne?

Bo taki tekst:

```text
```json
{"category": "billing"}
```
```

nie jest czystym JSON-em. Pydantic nie powinien tego przyjąć jako JSON.

Uwaga produkcyjna: to zabezpieczenie jest użyteczne, ale nie idealne. W większym systemie lepiej byłoby mieć osobną funkcję:

```python
def strip_markdown_json_fence(text: str) -> str:
    ...
```

i testy jednostkowe dla kilku przypadków odpowiedzi.

---

### 5.13. Walidacja Pydantic

```python
result = TicketAnalysis.model_validate_json(raw_content)
```

To najważniejsza linia w całym pliku.

Robi trzy rzeczy:

1. parsuje tekst jako JSON,
2. sprawdza, czy JSON pasuje do modelu `TicketAnalysis`,
3. zwraca instancję klasy `TicketAnalysis`.

Po tej linii `result` nie jest już tekstem. To obiekt Pythona.

Możesz odwołać się do pól:

```python
print(result.category)
print(result.urgency)
print(result.sentiment)
print(result.summary)
```

To jest dokładnie ten typ obiektu, który w LangGraph można później zapisać do stanu.

---

### 5.14. Wydruk wyniku

```python
print("\nSUKCES. Zgłoszenie zostało przeprocesowane w obiekt Pydantic:")
print(result.model_dump_json(indent=4))
```

Pierwsza linia drukuje komunikat sukcesu.

Druga linia zamienia obiekt Pydantic z powrotem na JSON, tylko po to, żeby ładnie go wyświetlić.

To nie znaczy, że `result` jest stringiem. `result` pozostaje obiektem Pydantic. `model_dump_json(...)` to tylko metoda prezentacji.

---

### 5.15. Obsługa błędów

```python
except Exception as error:
    print(f"\nBłąd wykonania: {error}")
    if 'raw_content' in locals():
        print(f"Surowa odpowiedź modelu:\n{raw_content}")
```

Ta sekcja łapie błędy.

Mogą to być między innymi:

- brak połączenia z lokalnym serwerem LLM,
- zła nazwa modelu,
- brak zmiennej `MODEL_NAME`,
- model zwrócił tekst, który nie jest JSON-em,
- model zwrócił JSON niezgodny ze strukturą `TicketAnalysis`.

Dobra praktyka: gdy walidacja się nie uda, warto pokazać surową odpowiedź modelu. Dzięki temu możesz debugować, czy problem jest w modelu, promptcie, konfiguracji czy walidacji.

Wersja bardziej precyzyjna powinna łapać osobno błędy Pydantic, np. `ValidationError`, zamiast ogólnego `Exception`.

---

### 5.16. Uruchomienie jako skrypt

```python
if __name__ == "__main__":
    main()
```

Ten idiom oznacza:

- jeżeli plik uruchamiasz bezpośrednio: wykonaj `main()`,
- jeżeli plik importujesz jako moduł: nie wykonuj automatycznie `main()`.

To jest ważne dla testowania. Dzięki temu w przyszłości będzie można importować funkcje z pliku bez automatycznego wykonywania zapytania do LLM.

---

## 6. Jak uruchomić skrypt

### 6.1. Instalacja zależności

W katalogu projektu:

```bash
python -m venv .venv
```

Linux / macOS:

```bash
source .venv/bin/activate
```

Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
```

Instalacja bibliotek:

```bash
pip install openai pydantic python-dotenv
```

### 6.2. Plik `.env`

Utwórz plik `.env` obok `01_run.py`:

```env
OPENAI_BASE_URL=http://localhost:11434/v1
OPENAI_API_KEY=not-needed
MODEL_NAME=nazwa-twojego-modelu
```

Dostosuj `OPENAI_BASE_URL` i `MODEL_NAME` do swojego środowiska.

### 6.3. Uruchomienie

```bash
python 01_run.py
```

Przykładowy wynik:

```json
{
    "category": "billing",
    "urgency": "high",
    "sentiment": "negative",
    "summary": "Klient zgłasza podwójne naliczenie opłaty za subskrypcję i żąda natychmiastowego zwrotu."
}
```

Dokładne słowa w `summary` mogą się różnić, ale struktura powinna pozostać taka sama.

---

## 7. Co ten plik robi dobrze

### 7.1. Używa Pydantic jako kontraktu danych

To bardzo dobry kierunek. Model danych jest jawny, nazwany i możliwy do walidacji.

### 7.2. Generuje schemat z kodu

Zamiast pisać schemat ręcznie w promptcie, skrypt bierze go z `TicketAnalysis.model_json_schema()`.

To ogranicza niespójność między definicją Pythona a instrukcją dla modelu.

### 7.3. Waliduje wynik po stronie programu

To jest kluczowa zasada systemów agentowych:

> LLM może się mylić. Program musi sprawdzić wynik.

### 7.4. Oddziela konfigurację od kodu

`OPENAI_BASE_URL`, `OPENAI_API_KEY` i `MODEL_NAME` pochodzą ze środowiska, a nie z kodu.

---

## 8. Ograniczenia obecnej wersji

### 8.1. Pola są zbyt luźne

Obecnie:

```python
urgency: str
```

pozwala na wartości:

```text
"high"
"urgent"
"bardzo pilne"
"natychmiast!!!"
```

Dla produkcyjnego systemu lepiej użyć `Literal`.

---

### 8.2. `response_format={"type": "json_object"}` nie wystarcza jako pełna walidacja

Ten parametr pomaga uzyskać JSON, ale pełną kontrolę daje dopiero Pydantic.

Dlatego nie myśl:

```text
response_format załatwia wszystko.
```

Myśl:

```text
response_format pomaga, ale walidacja Pydantic decyduje.
```

---

### 8.3. Brak osobnych funkcji utrudnia testy

Obecnie większość logiki jest w `main()`.

Do nauki to jest akceptowalne. Do rozwoju projektu warto rozdzielić kod na funkcje:

```python
def build_schema() -> str:
    ...

def build_messages(customer_email: str, schema_json: str) -> list[dict]:
    ...

def clean_json_response(raw_content: str) -> str:
    ...

def validate_ticket_analysis(raw_content: str) -> TicketAnalysis:
    ...
```

Wtedy każdą funkcję można przetestować osobno.

---

### 8.4. Brak testów jednostkowych

Na tym etapie powinieneś dodać małe testy dla:

- poprawnego JSON-a,
- JSON-a opakowanego w ```json,
- JSON-a bez wymaganego pola,
- błędnej wartości `urgency`, gdy dodasz `Literal`.

---

### 8.5. Dane wrażliwe

Wiadomość klienta zawiera końcówkę karty płatniczej. W ćwiczeniu to nie problem, ale w produkcji powinieneś dodać etap redakcji danych wrażliwych.

Przykład kierunku:

```python
def redact_sensitive_data(text: str) -> str:
    ...
```

---

## 9. Typowe błędy początkującego

### Błąd 1: Traktowanie odpowiedzi LLM jako prawdy

Źle:

```python
print(response.choices[0].message.content)
```

i uznanie, że to wystarczy.

Dobrze:

```python
result = TicketAnalysis.model_validate_json(raw_content)
```

---

### Błąd 2: Parsowanie tekstu przez `split()` albo regex

Źle:

```python
category = raw_content.split("category:")[1]
```

Dobrze:

```python
result = TicketAnalysis.model_validate_json(raw_content)
```

W systemach agentowych unikamy parsowania swobodnego tekstu. Preferujemy jawny JSON i walidację.

---

### Błąd 3: Za szerokie typy

Na początku `str` jest proste, ale zbyt luźne.

Lepszy następny krok:

```python
urgency: Literal["low", "medium", "high"]
```

---

### Błąd 4: Brak widoczności błędu modelu

Jeżeli walidacja się nie uda, musisz zobaczyć surową odpowiedź modelu. Ten skrypt robi to dobrze przez:

```python
print(f"Surowa odpowiedź modelu:\n{raw_content}")
```

---

### Błąd 5: Jeden wielki `main()` w nieskończoność

Na start jest dobrze. Później należy rozdzielać logikę na małe funkcje i testować każdą z nich.

---

## 10. Minimalna wersja mentalna

Gdyby sprowadzić ten plik do jednej idei, wygląda ona tak:

```python
class ExpectedOutput(BaseModel):
    field: str

raw = ask_llm("Zwróć JSON zgodny ze schematem")
validated = ExpectedOutput.model_validate_json(raw)
```

To jest wzorzec, który będzie wracał w całym projekcie:

```text
schemat → LLM → JSON → walidacja → stan aplikacji
```

---

## 11. Wersja produkcyjna — kierunek rozwoju

Docelowo ten skrypt warto przekształcić w bardziej testowalną strukturę:

```text
01_run.py
src/
  ticket_analysis/
    models.py
    prompts.py
    parser.py
    client.py
tests/
  test_parser.py
  test_models.py
```

Przykładowy podział odpowiedzialności:

| Plik | Odpowiedzialność |
|---|---|
| `models.py` | Pydantic models |
| `prompts.py` | budowanie wiadomości system/user |
| `parser.py` | czyszczenie i walidacja JSON |
| `client.py` | konfiguracja klienta OpenAI-compatible |
| `tests/` | testy jednostkowe |

Dopiero po takim uporządkowaniu warto przenieść logikę do LangGraph jako node.

---

## 12. Jak ten skrypt stanie się node'em LangGraph

Obecnie funkcja robi wszystko lokalnie:

```python
def main() -> None:
    ...
```

W LangGraph podobna logika mogłaby stać się node'em:

```python
from typing import TypedDict

class TicketState(TypedDict):
    customer_email: str
    ticket_analysis: dict | None
    errors_history: list[str]


def analyze_ticket_node(state: TicketState) -> TicketState:
    raw_content = ask_llm_for_ticket_analysis(state["customer_email"])
    result = TicketAnalysis.model_validate_json(raw_content)

    return {
        **state,
        "ticket_analysis": result.model_dump(),
    }
```

Wtedy wynik pracy agenta nie znika w konsoli, tylko trafia do jawnego stanu grafu.

To jest dokładnie kierunek Multi-Agent System:

```text
node analizuje → waliduje → aktualizuje stan → graf decyduje, co dalej
```

---

## 13. Ćwiczenia praktyczne

### Ćwiczenie 1 — uruchomienie bez zmian

Uruchom:

```bash
python 01_run.py
```

Sprawdź, czy otrzymujesz JSON z polami:

- `category`,
- `urgency`,
- `sentiment`,
- `summary`.

Kryterium zaliczenia: skrypt kończy się komunikatem `SUKCES`.

---

### Ćwiczenie 2 — zaostrzenie typów

Zmień model na:

```python
from typing import Literal

class TicketAnalysis(BaseModel):
    category: Literal["billing", "technical", "sales"]
    urgency: Literal["low", "medium", "high"]
    sentiment: Literal["positive", "neutral", "negative"]
    summary: str = Field(description="Jednozdaniowe, zwięzłe podsumowanie problemu")
```

Uruchom ponownie skrypt.

Kryterium zaliczenia: model nadal zwraca poprawny wynik, a Pydantic pilnuje dozwolonych wartości.

---

### Ćwiczenie 3 — wymuszenie błędu walidacji

Tymczasowo zmień prompt tak, aby model zwrócił błędną wartość, np. `urgency="critical"`.

Sprawdź, czy Pydantic zgłosi błąd.

Kryterium zaliczenia: rozumiesz, że błąd walidacji jest sukcesem architektury, bo system wykrył niepoprawne dane.

---

### Ćwiczenie 4 — wydzielenie funkcji czyszczącej

Wydziel ten fragment:

```python
if raw_content.startswith("```json"):
    raw_content = raw_content[7:]
if raw_content.startswith("```"):
    raw_content = raw_content[3:]
if raw_content.endswith("```"):
    raw_content = raw_content[:-3]

raw_content = raw_content.strip()
```

do funkcji:

```python
def clean_json_response(raw_content: str) -> str:
    ...
```

Kryterium zaliczenia: `main()` staje się krótszy, a funkcję można przetestować osobno.

---

### Ćwiczenie 5 — przygotowanie pod testy

Dodaj testy dla funkcji `clean_json_response`.

Przykładowe przypadki:

```python
def test_clean_plain_json():
    assert clean_json_response('{"a": 1}') == '{"a": 1}'


def test_clean_json_markdown_fence():
    raw = '```json\n{"a": 1}\n```'
    assert clean_json_response(raw) == '{"a": 1}'
```

Kryterium zaliczenia: przynajmniej dwa testy przechodzą w `pytest`.

---

## 14. Pytania kontrolne

Odpowiedz samodzielnie po przerobieniu pliku:

1. Czym różni się surowa odpowiedź LLM od obiektu Pydantic?
2. Dlaczego `response_format={"type": "json_object"}` nie zastępuje walidacji Pydantic?
3. Co się stanie, gdy model nie zwróci pola `summary`?
4. Dlaczego warto użyć `Literal` dla `urgency`?
5. Który fragment kodu powinien zostać wydzielony do funkcji jako pierwszy?
6. Jak zapisałbyś wynik `TicketAnalysis` w stanie LangGraph?

---

## 15. Kryterium zaliczenia tej lekcji

Uznaj lekcję za zaliczoną, gdy potrafisz:

- wyjaśnić, po co istnieje klasa `TicketAnalysis`,
- powiedzieć, czym jest `model_json_schema()`,
- wskazać różnicę między JSON-em jako tekstem a obiektem Pydantic,
- uruchomić skrypt z własnym `.env`,
- celowo wywołać błąd walidacji,
- poprawić model przez `Literal`,
- wskazać, jak ta logika stanie się node'em w LangGraph.

Po tym etapie jesteś gotowy do kolejnej misji: **Tool Calling**, czyli dodania modelowi kontrolowanych „rąk” w postaci funkcji/narzędzi.
