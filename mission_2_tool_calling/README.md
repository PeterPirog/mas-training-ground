# Misja 2: Function Calling (Nadanie Modelowi Rąk)

## Cel Misji

Celem tej misji jest nauczenie LLM, jak nie tylko analizować dane, ale też **działać** w środowisku poprzez wywoływanie funkcji. Zamiast opisywać, co powinno się stać, model będzie mógł bezpośrednio wywoływać zdefiniowane funkcje Pythona.

**Co zbudujemy:** Agent, który analizuje zapytanie użytkownika, decyduje, która funkcja jest odpowiednia, wywołuje ją i zwraca wynik. Przykład: zapytanie "oblicz 5! (silnia)" spowoduje, że model samodzielnie wywoła funkcję `calculate_factorial(n=5)`.

## Wymagania Wstępne

- ✅ Ukończona **Misja 1** – rozumienie strukturalnych wyjść i Pydantic
- Średniozaawansowana znajomość Pythona (dekoratory, *args, **kwargs)
- Podstawowa znajomość modułu `subprocess` (dla symulacji systemowej)

## Kluczowe Koncepcje Technologiczne

- **OpenAI Tools** – deklaracja funkcji jako tooli w API (JSON schema)
- **Function Calling** – mechanizm, w którym model decyдуje o wywołaniu funkcji
- **Subprocess** – symulacja wywoływania zewnętrznych poleceń
- **Typy zdefiniowane jako funkcje** – mapowanie zapytań do konkretnych wywołań
- **Obsługa wyników** – parsowanie i formatowanie odpowiedzi

## Materiały Źródłowe (Knowledge Base)

Przed rozpoczęciem misji przeczytaj pliki z katalogu `docs/ai_workflow/`:

1. `docs/ai_workflow/02_openai_function_calling.md` – pełny przewodnik po Function Calling w OpenAI
2. `docs/ai_workflow/08_python_subprocess_docs.md` – dokumentacja i przykłady użycia `subprocess`

## Kryteria Sukcesu

Na koniec misji będziesz mieć działający agent, który:

- Przyjmuje zapytanie użytkownika (np. "Jaka jest temperatura w Warszawie?")
- Decyduje, którą funkcję (tool) wywołać, analizując zapytanie
- Wywołuje funkcję (np. `get_weather(city="Warsaw")`) z odpowiednimi parametrami
- Zwraca wynik w zrozumiałej formie (np. "Temperatura w Warszawie to 22°C")

**Przykład działania:**
```bash
$ python mission_2.py "Wykonaj obliczenie: 12 * 5 + 8"
Wynik: Obliczyłem 12 * 5 + 8 = 68
```

## Kolejne Kroki

Gdy ukończysz tę misję, przejdź do **Misji 3: LangGraph Basics**, gdzie połączyłeś funkcje w graphy stanów.
