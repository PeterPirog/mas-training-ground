# Misja 1: Wymuszenie Strukturalnych Wyjść

## Cel Misji

Celem tej misji jest nauczenie LLM generowania czystych, zwalidowanych struktur danych JSON zamiast swobodnego tekstu. Zamiast "gadania", model będzie musiał dostarczać odpowiedzi w postaci skonstruowanej zgodnie z definicją Pydantic.

**Co zbudujemy:** Skrypt przyjmujący tekstowe zapytanie użytkownika i zwracający dokładnie sformatowany, zwalidowany obiekt Pythonowy zdefiniowany jako model Pydantic.

## Wymagania Wstępne

- Podstawowa znajomość Pythona (funkcje, klasy)
- Podstawowa znajomość JSONa
- Brak wymaganych wcześniejszych misji – ta misja jest punktem startowym

## Kluczowe Koncepcje Technologiczne

- **Pydantic Models** – definicja schematów danych jako klas
- **OpenAI Response Format** – użycie parametru `response_format` w API
- **Zwalidowane typy** – konwersja danych wejściowych do zdefiniowanych struktur
- **Zmienne środowiskowe** – konfiguracja API za pomocą `.env`
- **Obsługa błędów walidacji** – try-except z `ValidationError`

## Materiały Źródłowe (Knowledge Base)

Przed rozpoczęciem misji przeczytaj pliki z katalogu `docs/ai_workflow/`:

1. `docs/ai_workflow/01_openai_structured_outputs.md` – dokumentacja funkcji structured outputs OpenAI
2. `docs/ai_workflow/03_pydantic_concepts_models.md` – koncepty modeli Pydantic i ich użycia

## Kryteria Sukcesu

Na koniec misji będziesz mieć działający skrypt, który:

- Pobiera zapytanie od użytkownika (np. "Pokaż dane firmy: nazwa=Acme, miasto=New York")
- Wywołuje OpenAI z ustawionym `response_format` naTwój model Pydantic
- Zwraca zwalidowany obiekt Pythona (nie JSON, a instancję klasy)
- Obsługuje błędy walidacji i wyświetla komunikaty użytkownikowi

**Przykład działania:**
```bash
$ python mission_1.py "Pokaż dane produktu: nazwa=Laptop, cena=2999, kategoria=Elektronika"
Produkt(nazwa='Laptop', cena=2999, kategoria='Elektronika', data_dodania=datetime(...))
```

## Kolejne Kroki

Gdy ukończysz tę misję, przejdź do **Misji 2: Tool Calling**, która rozwija ten koncept, dodając LLM "ręce" w postaci wywoływania funkcji.
