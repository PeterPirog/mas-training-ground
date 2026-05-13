# 04_prompt_caching.md — Lekcja 04: Prompt Caching i projektowanie stabilnego kontekstu

## 0. Najkrótsza odpowiedź techniczna

**Prompt caching** polega na tym, że provider LLM może ponownie użyć wcześniej przetworzonego początku promptu, jeżeli kolejne zapytanie zaczyna się od identycznego prefiksu.

Najważniejszy wzorzec projektowy:

```text
[stabilny prefiks]
  instrukcje systemowe
  definicje narzędzi
  schematy Pydantic / JSON Schema
  stała dokumentacja

[dynamiczny sufiks]
  aktualne pytanie użytkownika
  aktualny stan sprawy
  nowe wyniki narzędzi
```

Główna zasada:

> To, co powtarzalne, trzymaj na początku promptu. To, co zmienne, przesuwaj na koniec.

---

## 1. Cel lekcji

Po lekcjach 01–03 umiesz już:

1. wymuszać strukturalne odpowiedzi JSON,
2. walidować wynik przez Pydantic,
3. definiować narzędzia aplikacyjne,
4. przenosić wynik pracy przez jawny stan workflow.

Lekcja 04 dodaje kolejny element produkcyjnego myślenia: **koszt i opóźnienie dużego kontekstu**.

W większych systemach agentowych prompt często zawiera:

- długie instrukcje systemowe,
- opisy narzędzi,
- schematy danych,
- fragmenty dokumentacji,
- streszczenie stanu projektu,
- historię błędów,
- wyniki wcześniejszych narzędzi.

Jeżeli za każdym razem wysyłasz całość jako zmieszany, niestabilny tekst, tracisz możliwość skutecznego cache'owania.

---

## 2. Intuicja

Wyobraź sobie dwa zapytania do modelu.

Pierwsze:

```text
Jesteś asystentem obsługi klienta.
Masz takie narzędzia: ...
Odpowiadasz takim JSON-em: ...
Dokumentacja firmowa: ...

Pytanie użytkownika: Klient zgłasza podwójną opłatę.
```

Drugie:

```text
Jesteś asystentem obsługi klienta.
Masz takie narzędzia: ...
Odpowiadasz takim JSON-em: ...
Dokumentacja firmowa: ...

Pytanie użytkownika: Klient prosi o fakturę.
```

Początek jest taki sam. Zmienia się tylko końcówka.

To jest idealna sytuacja dla prompt caching.

Zły układ:

```text
Pytanie użytkownika: Klient zgłasza podwójną opłatę.

Jesteś asystentem obsługi klienta.
Masz takie narzędzia: ...
Odpowiadasz takim JSON-em: ...
Dokumentacja firmowa: ...
```

Tutaj zmienna część jest na początku, więc każdy prompt zaczyna się inaczej. To utrudnia lub całkowicie psuje cache hit.

---

## 3. Miejsce w architekturze systemu agentowego

Prompt caching nie zastępuje:

- Pydantic,
- Tool Calling,
- jawnego stanu,
- testów,
- LangGraph.

To jest optymalizacja warstwy wejścia do modelu.

W architekturze agentowej wygląda to tak:

```text
Workflow State
  ↓
Prompt Builder
  ↓
Stable Prefix + Dynamic Suffix
  ↓
LLM API
  ↓
Structured Output / Tool Call
  ↓
Validation
  ↓
Updated State
```

Czyli prompt caching dotyczy głównie funkcji budującej prompt, nie samej logiki biznesowej.

---

## 4. Czego uczymy się praktycznie

W tej lekcji nie zaczynamy od konkretnego providera. Zamiast tego uczymy się uniwersalnej zasady:

```text
stabilny kontekst ≠ dynamiczne dane
```

Dopiero gdy to rozumiesz, możesz świadomie używać różnych implementacji:

- OpenAI prompt caching,
- Anthropic prompt caching,
- cache w routerach LLM,
- własny cache aplikacyjny,
- przyszły LangGraph z checkpointerem.

Ważne: **prompt caching providera to nie to samo co cache aplikacyjny**.

| Mechanizm | Co przechowuje | Po co |
|---|---|---|
| Prompt caching providera | przetworzony prefiks promptu | mniejszy koszt / mniejsze opóźnienie |
| Cache aplikacyjny | wynik funkcji lub odpowiedzi | unikanie ponownego obliczenia |
| Checkpointer LangGraph | stan workflow | wznowienie pracy po przerwaniu |

---

## 5. Minimalny przykład z pliku `04_prompt_caching.py`

Plik `04_prompt_caching.py` nie wywołuje realnego API LLM. To celowe.

Najpierw uczysz się mechaniki:

```text
stable_blocks → stable_prefix → stable_prefix_hash
```

oraz:

```text
dynamic_blocks → dynamic_suffix
```

### 5.1. Model `PromptBlock`

```python
class PromptBlock(BaseModel):
    name: str
    content: str
    cache_policy: Literal["stable", "dynamic"]
```

Każdy blok promptu ma nazwę, treść i informację, czy jest stabilny, czy dynamiczny.

Przykłady bloków stabilnych:

- instrukcje systemowe,
- kontrakty narzędzi,
- schemat odpowiedzi,
- stała dokumentacja.

Przykłady bloków dynamicznych:

- aktualne pytanie użytkownika,
- wynik ostatniego narzędzia,
- bieżący diff kodu,
- najnowszy błąd walidacji.

---

### 5.2. Model `PromptPlan`

```python
class PromptPlan(BaseModel):
    stable_blocks: list[PromptBlock]
    dynamic_blocks: list[PromptBlock]
    stable_prefix: str
    dynamic_suffix: str
    stable_prefix_hash: str
```

To jest jawny plan promptu. Dzięki temu możesz sprawdzić, co dokładnie trafia do części stabilnej, a co do dynamicznej.

W produkcyjnym systemie taki plan można zapisać w stanie workflow albo logach diagnostycznych.

---

### 5.3. Funkcja `build_prompt_plan(...)`

```python
def build_prompt_plan(user_question: str) -> PromptPlan:
    ...
```

Ta funkcja buduje prompt w dwóch częściach:

1. stabilny prefiks,
2. dynamiczny sufiks.

Ważne: `user_question` trafia dopiero do części dynamicznej.

To jest główny wzorzec projektowy tej lekcji.

---

### 5.4. Funkcja `simulate_provider_cache(...)`

```python
def simulate_provider_cache(
    plan: PromptPlan,
    cache_store: set[str],
) -> SimulatedCacheResult:
    ...
```

Ta funkcja symuluje cache hit i cache miss.

Nie udaje prawdziwego API. Pokazuje tylko zasadę:

```text
ten sam stabilny prefiks → ten sam hash → potencjalny cache hit
zmieniony stabilny prefiks → inny hash → cache miss
```

---

## 6. Jak uruchomić lekcję

W katalogu projektu:

```bash
python 04_prompt_caching.py
```

Oczekiwany efekt:

1. pierwsze zapytanie daje `cache_hit: false`,
2. drugie zapytanie z tym samym stabilnym prefiksem daje `cache_hit: true`,
3. po zmianie instrukcji systemowej wynik wraca do `cache_hit: false`.

To pokazuje najważniejszy problem: nawet niewielka zmiana stabilnej części promptu może zerwać cache.

---

## 7. Profesjonalna zasada układania promptu

Zalecany układ:

```text
1. Stała instrukcja roli agenta
2. Stałe zasady bezpieczeństwa i ograniczenia
3. Stałe kontrakty narzędzi
4. Stałe schematy JSON / Pydantic
5. Stała dokumentacja lub jej fragmenty
6. Zmienny stan workflow
7. Aktualne pytanie użytkownika
```

Unikaj takiego układu:

```text
1. Aktualne pytanie użytkownika
2. Aktualny timestamp
3. Losowy identyfikator requestu
4. Stałe instrukcje
5. Stałe narzędzia
6. Stała dokumentacja
```

Dynamiczne elementy na początku promptu psują stabilny prefiks.

---

## 8. Co najczęściej psuje prompt cache

### 8.1. Timestamp w instrukcji systemowej

Źle:

```text
Dzisiaj jest 2026-05-08. Jesteś asystentem...
```

Każdego dnia prefiks będzie inny.

Lepiej:

```text
Jesteś asystentem...

Aktualna data: 2026-05-08
```

Data powinna być częścią dynamiczną, nie stałą.

---

### 8.2. Losowy identyfikator na początku promptu

Źle:

```text
Request ID: 9f31a...
Jesteś asystentem...
```

Lepiej zapisać identyfikator w stanie/logach, a nie w stabilnym prefiksie.

---

### 8.3. Mieszanie wyników narzędzi z definicjami narzędzi

Definicje narzędzi są stabilne.

Wyniki narzędzi są dynamiczne.

Nie mieszaj ich w jednym bloku.

---

### 8.4. Generowanie promptu z niedeterministyczną kolejnością

Źle:

```python
for key, value in some_unordered_mapping.items():
    ...
```

Lepiej:

```python
for key in sorted(some_mapping):
    ...
```

Prompt powinien być deterministyczny.

---

## 9. Prompt caching a LangGraph

W LangGraph prompt caching będzie szczególnie przydatny, gdy wiele node'ów używa podobnego dużego kontekstu.

Przykład:

```text
support_agent_node
  ↓
billing_policy_node
  ↓
qa_review_node
```

Jeżeli każdy node otrzymuje te same:

- instrukcje systemowe,
- definicje narzędzi,
- schematy Pydantic,
- fragmenty dokumentacji,

to warto dbać o ich stabilną kolejność i identyczny prefiks.

Ale stan workflow powinien nadal być osobny:

```text
StateGraph state ≠ prompt text
```

Stan jest źródłem prawdy. Prompt jest tylko renderowaną reprezentacją tego, co model ma zobaczyć w danym kroku.

---

## 10. Typowe błędy początkującego

### Błąd 1: Jeden wielki prompt składany chaotycznie

Nie rób:

```python
prompt = f"{user_question}\n{tools}\n{schema}\n{context}"
```

Rób:

```python
stable_prefix = render_stable_context(...)
dynamic_suffix = render_dynamic_context(...)
prompt = stable_prefix + "\n\n" + dynamic_suffix
```

---

### Błąd 2: Mylenie prompt caching z pamięcią agenta

Prompt caching nie oznacza, że model „pamięta” fakty.

To tylko optymalizacja techniczna po stronie przetwarzania wejścia.

Pamięć aplikacji powinna być w:

- stanie workflow,
- bazie danych,
- checkpointerze,
- indeksie RAG,
- plikach/logach.

---

### Błąd 3: Wysyłanie całej historii rozmowy jako jedynego stanu

Historia rozmowy jest trudna do walidacji.

Lepszy wzorzec:

```text
jawny stan → deterministyczny prompt builder → LLM
```

---

### Błąd 4: Brak pomiaru cache hit

W produkcji musisz sprawdzać metryki użycia cache, np. liczbę tokenów odczytanych z cache, jeżeli provider ją zwraca.

Bez pomiaru nie wiesz, czy projekt promptu naprawdę działa.

---

## 11. Ćwiczenia praktyczne

### Ćwiczenie 1 — uruchomienie bez zmian

Uruchom:

```bash
python 04_prompt_caching.py
```

Kryterium zaliczenia: widzisz kolejno `cache_hit: false`, `cache_hit: true`, `cache_hit: false`.

---

### Ćwiczenie 2 — dodaj nowy stabilny blok

Dodaj blok:

```python
STABLE_ESCALATION_RULES = """Reguły eskalacji:
- high -> człowiek lub narzędzie priorytetowe
- medium -> standardowa obsługa
- low -> kolejka zwykła
"""
```

Następnie dołącz go do `stable_blocks`.

Kryterium zaliczenia: rozumiesz, że zmiana stabilnego prefiksu tworzy nowy cache key.

---

### Ćwiczenie 3 — przenieś dynamiczny timestamp

Dodaj dynamiczny blok:

```python
PromptBlock(
    name="request_metadata",
    content="request_time=2026-05-08T12:00:00",
    cache_policy="dynamic",
)
```

Kryterium zaliczenia: timestamp nie zmienia `stable_prefix_hash`.

---

### Ćwiczenie 4 — napisz test jednostkowy

Utwórz test:

```python
def test_same_stable_prefix_has_same_hash():
    first = build_prompt_plan("Pytanie A")
    second = build_prompt_plan("Pytanie B")

    assert first.stable_prefix_hash == second.stable_prefix_hash
```

Kryterium zaliczenia: różne pytania użytkownika nie zmieniają stabilnego prefiksu.

---

### Ćwiczenie 5 — sprawdź zerwanie cache

Napisz test:

```python
def test_modified_stable_prefix_changes_hash():
    ...
```

Kryterium zaliczenia: zmiana instrukcji systemowej powoduje zmianę `stable_prefix_hash`.

---

## 12. Pytania kontrolne

1. Czym różni się stabilny prefiks od dynamicznego sufiksu?
2. Dlaczego aktualne pytanie użytkownika powinno być na końcu promptu?
3. Dlaczego timestamp w instrukcji systemowej psuje cache?
4. Czy prompt caching zastępuje pamięć aplikacji?
5. Czy prompt caching zastępuje checkpointer LangGraph?
6. Co powinno być w stanie workflow, a co w promptcie?
7. Dlaczego wynik narzędzia jest częścią dynamiczną?
8. Jak sprawdzić, czy prompt caching naprawdę działa w produkcji?

---

## 13. Kryterium zaliczenia lekcji

Lekcja jest zaliczona, gdy potrafisz:

- wyjaśnić, czym jest prompt caching,
- odróżnić stabilny prefiks od dynamicznego sufiksu,
- zaprojektować prompt builder bez mieszania zmiennych danych z instrukcjami,
- wskazać, co psuje cache hit,
- uruchomić `04_prompt_caching.py`,
- wyjaśnić wynik `cache_hit: false → true → false`,
- powiedzieć, dlaczego prompt caching nie zastępuje jawnego stanu workflow.

---

## 14. Następny krok

Po tej lekcji możemy przejść do pierwszej lekcji LangGraph:

```text
05_langgraph_minimal_stategraph.py
05_langgraph_minimal_stategraph.md
```

Cel następnej lekcji:

```text
przenieść wzorzec state → node → state do prawdziwego StateGraph
```
