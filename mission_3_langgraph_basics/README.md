# Misja 3: Podstawy LangGraph (Budowa Maszyny Stanów)

## Cel Misji

Celem tej misji jest zrozumienie architektury **LangGraph** – frameworka do budowania grafów stanów (StateGraphs) z wykorzystaniem agentów. Zamiast prostych skryptów, zbudujesz pełną maszynę stanów z węzłami (Nodes), krawędziami (Edges) i przechowywaniem stanu (State).

**Co zbudujemy:** Prosty agent z dwoma węzłami, który przekazuje i modyfikuje globalny stan między sobą. Na przykład: węzeł "Analyzer" czyta dane, węzeł "Formatter" je formatuje, a graph zarządza przepływem danych.

## Wymagania Wstępne

- ✅ Ukończona **Misja 2** – rozumienie Function Calling i integracji z LLM
- Znajomość podstaw grafów (węzły, krawędzie)
- Zrozumienie koncepcji stanu (State) w programowaniu
- Zalecane: podstawowa wiedza o graphach i automatach stanów

## Kluczowe Koncepcje Technologiczne

- **StateGraph** – główny mechanizm budowy grafu w LangGraph
- **Nodes (Węzły)** – funktory, które przetwarzają stan
- **Edges (Krawędzie)** – reguły przechodzenia między węzłami
- **TypedDict** – typowane definicje stanu w Pythonie
- **Persistent Memory** – przechowywanie historii interakcji

## Materiały Źródłowe (Knowledge Base)

Przed rozpoczęciem misji przeczytaj pliki z katalogu `docs/ai_workflow/`:

1. `docs/ai_workflow/05_langgraph_core_tutorials.md` – podstawy budowy grafów i węzłów
2. `docs/ai_workflow/06_langgraph_persistence_memory.md` – mechanizmy zapamiętywania i historii

## Kryteria Sukcesu

Na koniec misji będziesz mieć działający graf agentów, który:

- Definiuje `TypedDict` jako stan globalny
- Tworzy co najmniej dwa węzły (`@node` dekorowane)
- Ustawia krawędzie (Edge) między węzłami
- Przechodzi przez graf, przekazując i modyfikując stan
- Wyświetla wynik końcowy i historię zmian stanu

**Przykład działania:**
```bash
$ python mission_3.py "Przeanalizuj tekst i sformatuj go"
=== STATE HISTORY ===
[Step 0] Input: "Przeanalizuj tekst i sformatuj go"
[Step 1] Analyzer -> Output: {'raw_text': '...', 'length': 30}
[Step 2] Formatter -> Output: {'formatted': '...', 'status': 'OK'}
```

## Kolejne Kroki

Gdy ukończysz tę misję, przejdź do **Misji 4: Actor-Critic Architecture**, gdzie zbudujesz auto-naprawcze pętle.
