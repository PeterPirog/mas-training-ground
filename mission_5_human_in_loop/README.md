# Misja 5: Człowiek w Pętli (Human-in-the-Loop)

## Cel Misji

Celem tej misji jest zintegrowanie **człowieka w procesie decyzyjnym agentowego**. Zamiast automatycznego wykonania niebezpiecznej akcji, system zatrzyma się i zapyta użytkownika o potwierdzenie. To kluczowy wzorzec bezpieczeństwa w systemach agentowych.

**Co zbudujemy:** Graf agentowy, który w pewnym momencie zatrzymuje się (breakpoint), oczekuje na wpisanie "YES" przez użytkownika w terminalu, a dopiero po potwierdzeniu wznawia działanie i kończy pracę.

## Wymagania Wstępne

- ✅ Ukończona **Misja 3** – rozumienie LangGraph i StateGraph
- ✅ Ukończona **Misja 4** – zrozumienie conditional edges i pętli反馈
- Znajomość interakcji z użytkownikiem w terminalu
- Zrozumienie koncepcji punktów przerwania (breakpoints)

## Kluczowe Koncepcje Technologiczne

- **LangGraph Breakpoints** – mechanizm wstrzymania wykonania grafu
- **Human-in-the-Loop** – interakcja człowiek-agent w real-time
- **Input prompt** – pobieranie danych od użytkownika
- **Conditional Resume** – wznawianie po spełnieniu warunku
- **Safety Mechanisms** – zabezpieczenia przed niezamierzonymi akcjami

## Materiały Źródłowe (Knowledge Base)

Przed rozpoczęciem misji przeczytaj pliki z katalogu `docs/ai_workflow/`:

1. `docs/ai_workflow/05_langgraph_core_tutorials.md` – zaawansowane techniki graphów
2. `docs/ai_workflow/06_langgraph_persistence_memory.md` – zatrzymywanie i wznawianie grafów

## Kryteria Sukcesu

Na koniec misji będziesz mieć działający system, który:

- Buduje pełny graf agentowy (min. 3 węzły)
- Wstawia breakpoint w węźle "Hardware Test" lub "Safe Check"
- Wyświetla komunikat: "Czy chcesz kontynuować? (wpisz YES)"
- Zatrzymuje wykonanie i czeka na input
- Po wpisaniu "YES" wznawia i kończy działanie
- Wyświetla kompletne wyniki

**Przykład działania:**
```bash
$ python mission_5.py "Symuluj test sprzętowy"
=== AGENT WORKFLOW ===
[Node 1] Analiza parametrów systemu
[Node 2] Przygotowanie do testu
[BREAKPOINT] Hardware Test Node
>>> Czy chcesz kontynuować? (wpisz YES)
user input: YES
[Node 3] Wykonanie testu
[Node 4] Generowanie raportu
=== WYNIK: Test zakończony sukcesem ===
```

## Zakończenie

To ostatnia misja w serii szkoleniowej. Po jej ukończeniu jesteś przygotowany do budowania pełnych, bezpiecznych systemów multi-agentowych z wykorzystaniem **LangGraph**, **OpenAI Tools** i wzorców **Reflexion** oraz **Human-in-the-Loop**.
