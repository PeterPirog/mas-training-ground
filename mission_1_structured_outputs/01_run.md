# 01_run.md — Misja 1: Structured Outputs + Pydantic

## Status lekcji

| Pole | Wartość |
|---|---|
| Misja | 1 — Structured Outputs |
| Plik omawiany | `01_run.py` |
| Poziom | Fundament agentic systems |
| Główny temat | Zamiana odpowiedzi LLM na zwalidowany obiekt Pydantic |
| Docelowa umiejętność | Umieć odróżnić tekst wygenerowany przez LLM od danych zaakceptowanych przez program |

---

## 1. Najkrótsza odpowiedź techniczna

`01_run.py` pokazuje pierwszy profesjonalny wzorzec pracy z LLM:

```text
model danych → JSON Schema → prompt + JSON mode → odpowiedź LLM → walidacja Pydantic → obiekt Pythona
```

Najważniejsza zasada tej lekcji:

> LLM generuje kandydat na dane. Dopiero Pydantic decyduje, czy program może te dane zaakceptować.

Ten skrypt nie jest jeszcze systemem multi-agentowym. Jest minimalnym fundamentem pod przyszłe node'y LangGraph, w których każdy agent będzie zwracał jawnie zdefiniowaną strukturę danych zamiast swobodnego tekstu.

---

## 2. Cel szkoleniowy

Celem pliku jest nauczenie trzech rzeczy:

1. jak opisać oczekiwany wynik LLM za pomocą modelu Pydantic,
2. jak przekazać modelowi schemat oczekiwanej odpowiedzi,
3. jak zweryfikować, czy odpowiedź modelu spełnia kontrakt danych.

Po tej lekcji masz rozumieć różnicę między:

```text
LLM odpowiedział poprawnie językowo
```

oraz:

```text
program zaakceptował odpowiedź jako poprawną strukturę danych
```

W systemach agentowych interesuje nas przede wszystkim druga sytuacja.

---

## 3. Co dokładnie robi `01_run.py`

Skrypt wykonuje następujący przepływ:

1. ładuje konfigurację z pliku `.env`,
2. tworzy klienta API kompatybilnego z OpenAI,
3. definiuje przykładową wiadomość klienta,
4. generuje JSON Schema z modelu `TicketAnalysis`,
5. wysyła wiadomość do modelu LLM,
6. prosi model o odpowiedź w formacie JSON,
7. pobiera surowy tekst odpowiedzi,
8. usuwa ewentualne znaczniki Markdown,
9. waliduje odpowiedź przez Pydantic,
10. drukuje wynik jako sformatowany JSON.

Schemat przepływu:

```text
.env
  ↓
OpenAI-compatible client
  ↓
TicketAnalysis.model_json_schema()
  ↓
chat.completions.create(...)
  ↓
raw_content: str
  ↓
cleaning
  ↓
TicketAnalysis.model_validate_json(raw_content)
  ↓
TicketAnalysis object
```

---

## 4. Główna intuicja

LLM jest dobry w interpretacji języka, ale nie powinien być traktowany jako źródło prawdy. Dlatego zamiast przyjmować dowolną odpowiedź tekstową, narzucamy kontrakt danych.

Swobodna odpowiedź modelu:

```text
Klient jest zdenerwowany, problem dotyczy płatności, trzeba szybko zareagować.
```

Odpowiedź użyteczna programistycznie:

```json
{
  "category": "billing",
  "urgency": "high",
  "sentiment": "negative",
  "summary": "Klient zgłasza podwójne naliczenie opłaty i żąda natychmiastowego zwrotu."
}
```

Dla człowieka obie odpowiedzi są zrozumiałe. Dla aplikacji produkcyjnej druga odpowiedź jest znacznie lepsza, bo ma stałe pola, które można walidować, testować i przekazywać między komponentami systemu.

---

## 5. Kontrakt danych: `TicketAnalysis`

W skrypcie kontrakt danych jest zdefiniowany tak:

```python
class TicketAnalysis(BaseModel):
    """Model danych reprezentujący przeanalizowane zgłoszenie od klienta."""

    category: str = Field(description="Kategoria zgłoszenia, np. 'billing', 'technical', 'sales'")
    urgency: str = Field(description="Priorytet: 'low', 'medium' lub 'high'")
    sentiment: str = Field(description="Nastawienie klienta: 'positive', 'neutral', 'negative'")
    summary: str = Field(description="Jednozdaniowe, zwięzłe podsumowanie problemu")
```

To oznacza, że poprawna odpowiedź musi zawierać cztery pola:

| Pole | Znaczenie | Obecny typ |
|---|---|---|
| `category` | kategoria zgłoszenia | `str` |
| `urgency` | priorytet zgłoszenia | `str` |
| `sentiment` | nastawienie klienta | `str` |
| `summary` | jednozdaniowe streszczenie | `str` |

### Ważne ograniczenie obecnej wersji

Typ `str` jest poprawny na start, ale zbyt luźny dla kodu produkcyjnego. Pydantic sprawdzi, czy `urgency` jest tekstem, ale nie sprawdzi, czy wartość należy do zbioru `low`, `medium`, `high`.

Dlatego w kolejnym kroku model powinien zostać zaostrzony:

```python
from typing import Literal
from pydantic import BaseModel, Field


class TicketAnalysis(BaseModel):
    category: Literal["billing", "technical", "sales", "other"] = Field(
        description="Kategoria zgłoszenia"
    )
    urgency: Literal["low", "medium", "high"] = Field(
        description="Priorytet zgłoszenia"
    )
    sentiment: Literal["positive", "neutral", "negative"] = Field(
        description="Nastawienie klienta"
    )
    summary: str = Field(
        min_length=10,
        max_length=240,
        description="Jednozdaniowe, zwięzłe podsumowanie problemu"
    )
```

To jest wersja bardziej profesjonalna, bo ogranicza swobodę modelu i ułatwia późniejsze testowanie.

---

## 6. JSON mode a walidacja Pydantic

W skrypcie pojawia się parametr:

```python
response_format={"type": "json_object"}
```

Ten parametr pomaga uzyskać odpowiedź będącą obiektem JSON. Nie należy jednak mylić go z pełną walidacją biznesową.

Różnica jest następująca:

| Mechanizm | Kiedy działa | Co robi | Czego nie gwarantuje |
|---|---|---|---|
| Prompt systemowy | przed generacją | instruuje model, jak ma odpowiedzieć | nie gwarantuje zgodności |
| `response_format` | podczas generacji / po stronie API | wymusza lub wspiera format JSON | nie musi gwarantować zgodności ze wszystkimi polami modelu |
| Pydantic | po odpowiedzi modelu | parsuje i waliduje wynik | nie poprawia automatycznie błędnej odpowiedzi modelu |

Profesjonalna zasada:

```text
JSON mode pomaga modelowi odpowiedzieć poprawnie.
Pydantic decyduje, czy aplikacja może tej odpowiedzi zaufać.
```

---

## 7. Generowanie schematu JSON

Ten fragment:

```python
schema_json = json.dumps(TicketAnalysis.model_json_schema(), indent=2)
```

tworzy opis oczekiwanej struktury danych na podstawie klasy Pydantic.

Dzięki temu prompt nie musi ręcznie powtarzać struktury modelu. To zmniejsza ryzyko niespójności między kodem a instrukcją dla LLM.

W praktyce powstaje wzorzec:

```text
Pydantic model jest źródłem prawdy dla struktury danych.
Prompt tylko przekazuje tę strukturę modelowi LLM.
```

To ważny nawyk architektoniczny. W profesjonalnym systemie nie chcesz mieć jednego schematu w kodzie, a drugiego — lekko innego — w promptach.

---

## 8. Prompt systemowy

W skrypcie prompt systemowy wygląda koncepcyjnie tak:

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

Ten prompt robi cztery rzeczy:

1. nadaje modelowi rolę,
2. zakazuje swobodnego komentarza,
3. zakazuje Markdown,
4. przekazuje schemat JSON.

To jest dobry wzorzec na start. W wersji produkcyjnej warto jednak doprecyzować, że model nie powinien dopisywać pól spoza schematu i powinien wybierać wartości z zamkniętych słowników, jeśli model Pydantic używa `Literal`.

---

## 9. Czyszczenie odpowiedzi z Markdown

Skrypt zawiera zabezpieczenie:

```python
if raw_content.startswith("```json"):
    raw_content = raw_content[7:]
if raw_content.startswith("```"):
    raw_content = raw_content[3:]
if raw_content.endswith("```"):
    raw_content = raw_content[:-3]

raw_content = raw_content.strip()
```

To działa dla prostych przypadków, ale profesjonalnie lepiej wydzielić tę logikę do osobnej funkcji:

```python
def clean_json_response(raw_content: str) -> str:
    text = raw_content.strip()

    if text.startswith("```json"):
        text = text.removeprefix("```json").strip()
    elif text.startswith("```"):
        text = text.removeprefix("```").strip()

    if text.endswith("```"):
        text = text.removesuffix("```").strip()

    return text
```

Dlaczego to jest bardziej profesjonalne?

- `main()` staje się krótszy,
- funkcję można testować jednostkowo,
- odpowiedzialność jest nazwana,
- łatwiej później wymienić parser na bardziej rygorystyczny.

---

## 10. Walidacja Pydantic

Najważniejsza linia skryptu:

```python
result = TicketAnalysis.model_validate_json(raw_content)
```

Ta linia robi trzy rzeczy:

1. próbuje sparsować `raw_content` jako JSON,
2. sprawdza zgodność z modelem `TicketAnalysis`,
3. zwraca instancję klasy `TicketAnalysis`.

Po tej linii `result` nie jest już zwykłym tekstem. To zwalidowany obiekt Pythona.

Można używać go tak:

```python
print(result.category)
print(result.urgency)
print(result.sentiment)
print(result.summary)
```

W przyszłym grafie LangGraph taki wynik powinien trafić do jawnego stanu workflow, a nie tylko zostać wydrukowany w terminalu.

---

## 11. Obsługa błędów

Obecna wersja łapie wszystkie wyjątki:

```python
except Exception as error:
    print(f"\nBłąd wykonania: {error}")
```

Do nauki jest to akceptowalne, ale wersja profesjonalna powinna rozróżniać typy błędów:

- brak konfiguracji,
- błąd połączenia z modelem,
- brak treści w odpowiedzi,
- błąd parsowania JSON,
- błąd walidacji Pydantic.

Minimalny kierunek poprawy:

```python
from pydantic import ValidationError

try:
    result = TicketAnalysis.model_validate_json(raw_content)
except ValidationError as error:
    print("Model zwrócił JSON niezgodny ze schematem TicketAnalysis.")
    print(error)
    print("Surowa odpowiedź modelu:")
    print(raw_content)
```

To jest ważne, bo w systemie agentowym różne błędy powinny prowadzić do różnych decyzji grafu. Błąd walidacji może prowadzić do retry. Brak konfiguracji powinien zatrzymać program natychmiast.

---

## 12. Bezpieczeństwo danych wejściowych

W przykładowym tekście znajduje się końcówka karty płatniczej:

```text
karta z końcówką 4432
```

W ćwiczeniu to akceptowalne, ale w systemie produkcyjnym należy traktować takie dane ostrożnie.

Profesjonalny kierunek:

```python
def redact_sensitive_data(text: str) -> str:
    # Minimalny przykład szkoleniowy, niepełny produkcyjnie.
    return text.replace("końcówką 4432", "końcówką ****")
```

Docelowo warto dodać osobny etap redakcji danych wrażliwych przed wysłaniem tekstu do modelu.

---

## 13. Miejsce w architekturze LangGraph

W obecnej wersji skrypt kończy się wydrukiem wyniku:

```python
print(result.model_dump_json(indent=4))
```

W LangGraph node nie powinien tylko drukować wyniku. Powinien zwracać zaktualizowany stan.

Minimalna wersja koncepcyjna:

```python
from typing import TypedDict


class TicketState(TypedDict):
    customer_email: str
    ticket_analysis: dict | None
    errors_history: list[str]


def analyze_ticket_node(state: TicketState) -> TicketState:
    raw_content = ask_llm_for_ticket_analysis(state["customer_email"])
    clean_content = clean_json_response(raw_content)
    result = TicketAnalysis.model_validate_json(clean_content)

    return {
        **state,
        "ticket_analysis": result.model_dump(),
    }
```

To pokazuje przejście od skryptu liniowego do architektury stanowej:

```text
funkcja drukująca wynik → node aktualizujący jawny stan
```

---

## 14. Co obecny plik robi dobrze

| Obszar | Ocena | Komentarz |
|---|---|---|
| Cel lekcji | dobry | jasno pokazuje, że LLM ma zwracać dane, nie opis |
| Pydantic | dobry | używa modelu jako kontraktu danych |
| JSON Schema | dobry | schemat pochodzi z kodu, nie z ręcznego opisu |
| Walidacja | dobry | wynik jest sprawdzany po stronie programu |
| Konfiguracja | dobry | używa `.env` zamiast wpisywać endpoint w kodzie |
| Testowalność | do poprawy | logika jest jeszcze zbyt mocno skupiona w `main()` |
| Rygor typów | do poprawy | pola `str` warto zastąpić przez `Literal` tam, gdzie są zamknięte słowniki |
| Obsługa błędów | do poprawy | warto rozdzielić `ValidationError` od błędów konfiguracji i API |

---

## 15. Najważniejsze poprawki profesjonalizujące

### Poprawka 1 — zaostrzyć model Pydantic

Zamień luźne `str` na `Literal`, gdzie wartości są zamknięte.

```python
urgency: Literal["low", "medium", "high"]
```

Efekt: model nie może zaakceptować wartości typu `critical`, `urgent`, `bardzo pilne`.

---

### Poprawka 2 — wydzielić czyszczenie JSON do funkcji

Zamiast trzymać czyszczenie Markdown w `main()`, zrób:

```python
def clean_json_response(raw_content: str) -> str:
    ...
```

Efekt: można napisać testy jednostkowe.

---

### Poprawka 3 — dodać testy

Minimalne testy:

```python
def test_clean_plain_json():
    assert clean_json_response('{"a": 1}') == '{"a": 1}'


def test_clean_json_markdown_fence():
    raw = '```json\n{"a": 1}\n```'
    assert clean_json_response(raw) == '{"a": 1}'
```

Następnie test dla walidacji:

```python
import pytest
from pydantic import ValidationError


def test_invalid_urgency_is_rejected():
    raw = '''
    {
      "category": "billing",
      "urgency": "critical",
      "sentiment": "negative",
      "summary": "Klient zgłasza podwójną opłatę."
    }
    '''

    with pytest.raises(ValidationError):
        TicketAnalysis.model_validate_json(raw)
```

---

### Poprawka 4 — rozdzielić błędy

Nie każdy błąd oznacza to samo.

```text
brak MODEL_NAME → błąd konfiguracji
brak serwera LLM → błąd infrastruktury
niepoprawny JSON → błąd formatu odpowiedzi
niezgodny JSON → błąd walidacji danych
```

W systemie LangGraph te przypadki będą później prowadzić do różnych ścieżek grafu.

---

### Poprawka 5 — dodać checklistę uruchomienia

Przed uruchomieniem sprawdź:

- czy istnieje `.env`,
- czy `OPENAI_BASE_URL` wskazuje działający serwer,
- czy `MODEL_NAME` jest poprawny,
- czy model obsługuje tryb JSON albo przynajmniej dobrze reaguje na prompt,
- czy środowisko ma zainstalowane `openai`, `pydantic`, `python-dotenv`.

---

## 16. Minimalna profesjonalna wersja funkcji pomocniczych

Poniższy kod nie zastępuje całego skryptu. Pokazuje kierunek refaktoryzacji.

```python
from typing import Literal
from pydantic import BaseModel, Field, ValidationError


class TicketAnalysis(BaseModel):
    category: Literal["billing", "technical", "sales", "other"] = Field(
        description="Kategoria zgłoszenia"
    )
    urgency: Literal["low", "medium", "high"] = Field(
        description="Priorytet zgłoszenia"
    )
    sentiment: Literal["positive", "neutral", "negative"] = Field(
        description="Nastawienie klienta"
    )
    summary: str = Field(
        min_length=10,
        max_length=240,
        description="Jednozdaniowe podsumowanie problemu"
    )


def clean_json_response(raw_content: str) -> str:
    text = raw_content.strip()

    if text.startswith("```json"):
        text = text.removeprefix("```json").strip()
    elif text.startswith("```"):
        text = text.removeprefix("```").strip()

    if text.endswith("```"):
        text = text.removesuffix("```").strip()

    return text


def validate_ticket_analysis(raw_content: str) -> TicketAnalysis:
    clean_content = clean_json_response(raw_content)
    return TicketAnalysis.model_validate_json(clean_content)
```

---

## 17. Ćwiczenie praktyczne

Wykonaj trzy małe kroki, nie wszystko naraz.

### Krok 1

Zmień model `TicketAnalysis`, używając `Literal` dla pól:

- `category`,
- `urgency`,
- `sentiment`.

Kryterium zaliczenia: skrypt nadal działa dla poprawnej odpowiedzi.

### Krok 2

Wydziel funkcję:

```python
def clean_json_response(raw_content: str) -> str:
    ...
```

Kryterium zaliczenia: `main()` jest krótszy, a zachowanie programu się nie zmieniło.

### Krok 3

Dodaj testy dla `clean_json_response` i walidacji `TicketAnalysis`.

Kryterium zaliczenia:

```bash
pytest
```

kończy się sukcesem.

---

## 18. Pytania kontrolne

Odpowiedz samodzielnie:

1. Czy `response_format={"type": "json_object"}` zastępuje Pydantic?
2. Co dokładnie robi `model_validate_json(...)`?
3. Dlaczego `Literal` jest lepszy niż `str` dla pola `urgency`?
4. Dlaczego czyszczenie Markdown warto wydzielić do funkcji?
5. Jaka jest różnica między błędem formatu JSON a błędem walidacji Pydantic?
6. Co powinien zwracać node LangGraph: wydruk w konsoli czy zaktualizowany stan?

---

## 19. Kryterium zaliczenia lekcji

Lekcja jest zaliczona, gdy potrafisz:

- wyjaśnić rolę `TicketAnalysis`,
- wygenerować JSON Schema z modelu Pydantic,
- odróżnić JSON mode od walidacji Pydantic,
- celowo wywołać błąd walidacji,
- zaostrzyć model przez `Literal`,
- wydzielić czyszczenie odpowiedzi do osobnej funkcji,
- napisać minimalne testy jednostkowe,
- opisać, jak ta logika stanie się node'em LangGraph.

---

## 20. Następny krok

Po tej lekcji naturalnym następnym etapem jest **Tool Calling**.

Structured Outputs odpowiadają na pytanie:

```text
Jak zmusić model, aby zwrócił dane w kontrolowanym formacie?
```

Tool Calling odpowie na pytanie:

```text
Jak pozwolić modelowi wybrać kontrolowaną funkcję, ale nie pozwolić mu robić dowolnych rzeczy?
```

To będzie pierwszy krok w stronę agentów, którzy nie tylko odpowiadają, ale potrafią wywoływać ograniczone, testowalne narzędzia.
