# Misja 4: Architektura Actor-Critic (Pętla Auto-Naprawcza Reflexion)

## Cel Misji

Celem tej misji jest budowa **pętli auto-naprawczej** w oparciu o wzorzec **Reflexion**. Zamiast prostego przepływu danych, zbudujesz system, w którym jeden agent (Actor) pisze kod, a drugi (Critic) ocenia jego poprawność. W przypadku błędu graf się "cofa" i prosi Actor o poprawkę – maksymalnie 3 iteracje.

**Co zbudujemy:** System "Koder + Krytyk", który próbuje stworzyć działający kod Pythona. Jeśli kod zawiera błąd składniowy (AST), Critic go wykrywa, a graph automagicznie cofa się do Kodera.

## Wymagania Wstępne

- ✅ Ukończona **Misja 3** – głębokie zrozumienie LangGraph (StateGraph, Nodes, Edges)
- Zaawansowana znajomość Pythona
- Znajomość modułu `ast` (Abstract Syntax Tree) – parsowanie kodu
- Zrozumienie koncepcji pętli feedbackowych

## Kluczowe Koncepcje Technologiczne

- **Conditional Edges** – dynamiczne decydowanie o kierunku przepływu na podstawie stanu
- **Reflexion Pattern** – wzorzec auto-oceny i naprawy wyników
- **Abstract Syntax Tree (AST)** – parsowanie i analiza kodu Pythona
- **Iteration Limit** – mechanizm zabezpieczający przed nieskończoną pętlą
- **Error Handling** – wykrywanie błędów kompilacji i uruchomienia

## Materiały Źródłowe (Knowledge Base)

Przed rozpoczęciem misji przeczytaj pliki z katalogu `docs/ai_workflow/`:

1. `docs/ai_workflow/09_reflexion_paper_concept.md` – opis koncepcji Reflexion z perspektywy AI
2. `docs/ai_workflow/10_langgraph_reflexion_code_example.md` – gotowy przykład implementacji w LangGraph
3. `docs/ai_workflow/07_python_ast_green_tree_snakes.md` – dokumentacja i przykłady modułu `ast`

## Kryteria Sukcesu

Na koniec misji będziesz mieć działający system actor-critic, który:

- Definiuje actora (Kodera) generującego kod z opisu
- Definiuje criticera (Krytyka) sprawdzającego kod za pomocą AST
- Ustawia warunkowe krawędzie: jeśli błąd → powrót do Kodera, jeśli OK → zakończenie
- Ogranicza liczbę iteracji do maksymalnie 3
- Wyświetla historię zmian i końcowy efekt

**Przykład działania:**
```bash
$ python mission_4.py "Napisz funkcję, która zwraca sumę 2 i 3"
[ITER 1] Kod: "def sum(): return 2 + " # brak 3
          -> Błąd AST: SyntaxError
[ITER 2] Kod: "def sum(): return 2 + 3"
          -> OK! Wynik: 5
```

## Kolejne Kroki

Gdy ukończysz tę misję, przejdź do **Misji 5: Human-in-the-Loop**, która integruje człowieka w pętlę decyzyjną.
