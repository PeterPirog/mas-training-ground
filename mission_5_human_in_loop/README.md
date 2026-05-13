# Faza 5: RAG, baza wiedzy i dokumentacja — Knowledge Layer dla systemów agentowych

## Cel fazy

Celem Fazy 5 jest dodanie do systemu agentowego **warstwy wiedzy**, która pozwala agentom korzystać z dokumentów, instrukcji, kodu, notatek, specyfikacji i wcześniejszych decyzji projektowych bez polegania wyłącznie na pamięci kontekstu LLM.

W poprzednich fazach zbudowałeś fundament:

```text
Faza 1 — kontrola nad LLM:
Structured Outputs, Pydantic, Tool Calling, Prompt Caching

Faza 2 — silnik workflow:
LangGraph, state, nodes, edges, conditional edges, retry loops

Faza 3 — środowisko wykonawcze:
subprocess, AST, pytest, ruff, sandbox, raporty narzędzi

Faza 4 — wzorce produkcyjne:
Human-in-the-Loop, checkpointery, thread_id, Reflexion / Actor-Critic
```

W Fazie 5 uczysz się, jak sprawić, aby system agentowy miał dostęp do wiedzy zewnętrznej i potrafił używać jej w kontrolowany sposób.

Najważniejsza zasada:

> RAG nie służy do „wrzucenia wszystkiego do promptu”. RAG służy do selektywnego pobierania właściwych fragmentów wiedzy, cytowania źródeł i zapisywania wyników w jawnych strukturach danych.

---

## Zakres Fazy 5

Faza 5 obejmuje pięć głównych obszarów:

```text
5.1. Ingestia dokumentów
5.2. Chunking i metadane
5.3. Embeddingi i indeks wektorowy
5.4. Retrieval jako narzędzie agenta
5.5. Generowanie dokumentacji i raportów ze źródłami
```

To jest etap, w którym system agentowy zaczyna pracować nie tylko na aktualnym pytaniu użytkownika, ale też na trwałej bazie wiedzy.

---

## 5.1. Ingestia dokumentów

### Co musisz opanować

Musisz umieć wczytać dokumenty z różnych źródeł i zamienić je na jednolity format pośredni.

Przykładowe źródła:

```text
Markdown
TXT
PDF — później
pliki README
dokumentacja projektu
notatki projektowe
komentarze z review
logi z eksperymentów
wyniki testów
raporty QA
```

W tej fazie zaczynamy od Markdown i TXT, bo są najłatwiejsze do kontroli.

### Minimalny model dokumentu

```python
from pydantic import BaseModel, Field


class SourceDocument(BaseModel):
    source_id: str
    path: str
    title: str
    content: str
    document_type: str = Field(description="Np. markdown, txt, report, code_note")
```

### Dlaczego to ważne

Agent nie powinien sam „pamiętać”, co było w dokumentacji. Powinien mieć jawny mechanizm:

```text
wczytaj dokument
podziel na fragmenty
zapisz metadane
wyszukaj właściwy fragment
odpowiedz na podstawie źródeł
```

---

## 5.2. Chunking i metadane

### Co musisz opanować

Musisz umieć dzielić dokumenty na fragmenty, które są:

```text
wystarczająco małe, aby zmieściły się w kontekście,
wystarczająco duże, aby zachować sens,
opisane metadanymi,
łatwe do cytowania,
możliwe do powiązania z oryginalnym plikiem.
```

### Zły chunking

```text
tnij co 1000 znaków bez patrzenia na strukturę
```

Problem: możesz przeciąć definicję, przykład kodu albo tabelę.

### Lepszy chunking

```text
dziel według nagłówków Markdown
zachowuj ścieżkę sekcji
zapisuj numer fragmentu
zapisuj źródło
zapisuj typ dokumentu
```

### Minimalny model chunka

```python
from pydantic import BaseModel


class DocumentChunk(BaseModel):
    chunk_id: str
    source_id: str
    path: str
    heading_path: list[str]
    chunk_index: int
    text: str
    token_estimate: int
    metadata: dict
```

### Kryterium dobrego chunka

Dobry chunk powinien dać się przeczytać samodzielnie i odpowiedzieć na pytanie:

```text
Z jakiego dokumentu pochodzi?
Z jakiej sekcji pochodzi?
Czego dotyczy?
Czy można go zacytować?
```

---

## 5.3. Embeddingi i indeks wektorowy

### Co musisz opanować

Musisz rozumieć, że retrieval zwykle składa się z dwóch etapów:

```text
1. embedding tekstu
2. wyszukiwanie podobnych wektorów
```

Wariant minimalny do nauki:

```text
lokalna lista chunków
proste wyszukiwanie keywordowe
```

Wariant docelowy:

```text
embeddingi
vector store
metadane
filtry
ranking
reranking — później
```

### Dlaczego nie zaczynamy od ciężkiej bazy wektorowej

Na początku ważniejsze jest zrozumienie kontraktu danych niż wybór narzędzia.

Najpierw uczysz się:

```text
czym jest dokument
czym jest chunk
czym jest query
czym jest wynik retrievalu
jak zapisać źródła
jak nie halucynować odpowiedzi
```

Dopiero potem warto dodawać pełny vector store.

### Minimalny model wyniku wyszukiwania

```python
from pydantic import BaseModel, Field


class RetrievalHit(BaseModel):
    chunk_id: str
    source_id: str
    path: str
    heading_path: list[str]
    score: float = Field(ge=0)
    text: str
```

---

## 5.4. Retrieval jako narzędzie agenta

### Co musisz opanować

RAG powinien być traktowany jako **tool**, a nie jako magiczny dodatek do promptu.

Agent powinien móc użyć narzędzia:

```python
search_knowledge_base(query: str, top_k: int) -> list[RetrievalHit]
```

W LangGraph będzie to node albo tool node:

```text
UserQuestion
    ↓
QueryPlannerNode
    ↓
RetrieverNode
    ↓
AnswerGeneratorNode
    ↓
CitationCheckerNode
```

### Dlaczego to jest ważne

Jeżeli retrieval jest narzędziem, możesz go:

```text
testować
logować
ograniczać
walidować
powtarzać
wymieniać na inną implementację
podłączać do routera
zapisywać w stanie
```

### Minimalny stan dla RAG workflow

```python
from typing import Literal, TypedDict


class RagWorkflowState(TypedDict):
    user_question: str
    rewritten_query: str | None
    retrieval_hits: list[dict]
    draft_answer: str | None
    citation_status: Literal["PASS", "FAIL", "NOT_CHECKED"]
    errors_history: list[str]
    next_step: Literal["rewrite_query", "retrieve", "answer", "check", "finish", "human"]
```

---

## 5.5. Generowanie dokumentacji i raportów ze źródłami

### Co musisz opanować

System agentowy powinien generować dokumentację w sposób kontrolowany:

```text
nie z pamięci modelu,
nie z domysłów,
nie z luźnego streszczenia,
ale z jawnych fragmentów źródłowych.
```

Przykładowe artefakty:

```text
raport z analizy dokumentów
README modułu
notatka techniczna
podsumowanie decyzji projektowych
FAQ
instrukcja użytkownika
opis API
raport QA
changelog
```

### Minimalny model odpowiedzi z cytowaniami

```python
from pydantic import BaseModel


class CitedAnswer(BaseModel):
    answer: str
    used_chunk_ids: list[str]
    missing_information: list[str]
    confidence: str
```

### Zasada

Jeżeli system nie znalazł odpowiedzi w źródłach, powinien powiedzieć:

```text
Nie znalazłem tej informacji w dostępnej bazie wiedzy.
```

a nie:

```text
Wymyślę najbardziej prawdopodobną odpowiedź.
```

---

## Rekomendowana struktura lekcji Fazy 5

Zakładamy, że Faza 4 kończy się na lekcji `19`.

```text
20_document_ingestion.py
20_document_ingestion.md

21_markdown_chunking.py
21_markdown_chunking.md

22_keyword_retrieval_baseline.py
22_keyword_retrieval_baseline.md

23_rag_tool_node.py
23_rag_tool_node.md

24_cited_answer_generation.py
24_cited_answer_generation.md

25_rag_evaluation_and_hallucination_checks.py
25_rag_evaluation_and_hallucination_checks.md
```

---

## Lekcja 20 — Document Ingestion

### Cel

Nauczyć się wczytywać dokumenty do jawnej struktury danych.

### Co zbudujemy

Skrypt:

```text
20_document_ingestion.py
```

który:

```text
wczytuje pliki .md i .txt z katalogu docs/
tworzy SourceDocument
waliduje pola przez Pydantic
zapisuje inventory dokumentów jako JSON
```

### Kryteria sukcesu

Uczeń potrafi:

```text
wczytać dokument z dysku
nadać mu source_id
zapisać path, title, content i document_type
obsłużyć pusty dokument
zapisać wynik do JSON
```

---

## Lekcja 21 — Markdown Chunking

### Cel

Nauczyć się dzielić dokument Markdown na fragmenty według struktury nagłówków.

### Co zbudujemy

Skrypt:

```text
21_markdown_chunking.py
```

który:

```text
czyta SourceDocument
dzieli tekst po nagłówkach #, ##, ###
tworzy DocumentChunk
zapisuje heading_path
zapisuje chunk_index
liczy szacunkową długość fragmentu
```

### Kryteria sukcesu

Uczeń potrafi:

```text
wyjaśnić, dlaczego chunking po znakach jest słaby
podzielić dokument według nagłówków
zachować metadane źródła
odtworzyć, z którego miejsca pochodzi chunk
```

---

## Lekcja 22 — Keyword Retrieval Baseline

### Cel

Zbudować pierwszy prosty retriever bez embeddingów.

### Dlaczego zaczynamy od keyword search

Embeddingi są ważne, ale na początku chcemy mieć retriever, który jest:

```text
łatwy do debugowania
deterministyczny
testowalny
niezależny od zewnętrznego modelu
```

### Co zbudujemy

Skrypt:

```text
22_keyword_retrieval_baseline.py
```

który:

```text
przyjmuje pytanie użytkownika
porównuje słowa kluczowe z chunkami
zwraca top_k wyników jako RetrievalHit
```

### Kryteria sukcesu

Uczeń potrafi:

```text
zwrócić top_k chunków
pokazać score
wyjaśnić, dlaczego wynik został zwrócony
zapisać retrieval_hits do stanu workflow
```

---

## Lekcja 23 — RAG Tool Node

### Cel

Połączyć retrieval z workflow agentowym jako narzędzie.

### Co zbudujemy

Node:

```python
def retrieval_node(state: RagWorkflowState) -> dict:
    ...
```

oraz prosty router:

```text
jeśli znaleziono źródła → answer
jeśli nie znaleziono źródeł → human / insufficient_context
```

### Kryteria sukcesu

Uczeń potrafi:

```text
traktować retrieval jako tool
zapisać retrieval_hits w stanie
rozróżnić brak wyników od błędu narzędzia
zdecydować, czy można generować odpowiedź
```

---

## Lekcja 24 — Cited Answer Generation

### Cel

Nauczyć się generować odpowiedzi wyłącznie na podstawie pobranych źródeł.

### Co zbudujemy

Model:

```python
class CitedAnswer(BaseModel):
    answer: str
    used_chunk_ids: list[str]
    missing_information: list[str]
    confidence: str
```

oraz generator odpowiedzi:

```text
retrieval_hits + user_question → CitedAnswer
```

### Kryteria sukcesu

Uczeń potrafi:

```text
wskazać, które chunki zostały użyte
odróżnić odpowiedź źródłową od domysłu
zgłosić brak informacji
wygenerować odpowiedź z listą użytych źródeł
```

---

## Lekcja 25 — RAG Evaluation and Hallucination Checks

### Cel

Nauczyć się testować jakość RAG.

### Co zbudujemy

Proste testy:

```text
pytanie, które ma odpowiedź w źródłach
pytanie, którego nie ma w źródłach
pytanie dwuznaczne
pytanie wymagające dwóch źródeł
```

### Kryteria sukcesu

Uczeń potrafi:

```text
sprawdzić, czy odpowiedź ma źródła
sprawdzić, czy used_chunk_ids istnieją
sprawdzić, czy model przyznaje brak informacji
nie akceptować odpowiedzi bez retrieval_hits
```

---

## Docelowy stan workflow po Fazie 5

```python
from typing import Literal, TypedDict


class KnowledgeWorkflowState(TypedDict):
    user_question: str
    documents_inventory: list[dict]
    chunks: list[dict]
    rewritten_query: str | None
    retrieval_hits: list[dict]
    draft_answer: str | None
    cited_answer: dict | None
    missing_information: list[str]
    citation_status: Literal["PASS", "FAIL", "NOT_CHECKED"]
    retrieval_status: Literal["FOUND", "EMPTY", "ERROR", "NOT_RUN"]
    errors_history: list[str]
    next_step: Literal[
        "ingest",
        "chunk",
        "retrieve",
        "answer",
        "check_citations",
        "human",
        "finish",
    ]
```

---

## Główna pętla Fazy 5

```text
UserQuestion
    ↓
QueryPlannerNode
    ↓
RetrieverNode
    ↓
RetrievalRouter
        ├── EMPTY → InsufficientContextNode
        └── FOUND → AnswerGeneratorNode
                    ↓
              CitationCheckerNode
                    ↓
              AnswerRouter
                  ├── PASS → FinalAnswer
                  ├── FAIL → RetryRetrieval
                  └── NEEDS_HUMAN → HumanReview
```

---

## Kryteria ukończenia Fazy 5

Fazę 5 uznaj za ukończoną, gdy potrafisz:

```text
wczytać dokumenty do SourceDocument
dzielić Markdown na DocumentChunk
zachować heading_path i source_id
zbudować prosty keyword retriever
zwrócić RetrievalHit z metadanymi
zapisać retrieval_hits w stanie workflow
wygenerować CitedAnswer
odmówić odpowiedzi, gdy nie ma źródeł
sprawdzić, czy used_chunk_ids istnieją
odróżnić RAG od prompt caching
odróżnić RAG od checkpointingu
wyjaśnić, kiedy potrzebna jest eskalacja do człowieka
```

---

## Typowe błędy

### Błąd 1: Wrzucanie całej dokumentacji do promptu

To jest kosztowne, kruche i słabo skalowalne.

Lepszy wzorzec:

```text
wybierz właściwe fragmenty
przekaż tylko potrzebne źródła
zapisz użyte źródła
```

### Błąd 2: Brak metadanych chunków

Chunk bez `source_id`, `path` i `heading_path` jest trudny do audytu.

### Błąd 3: Odpowiedź bez źródeł

Jeżeli workflow ma być RAG, odpowiedź musi wynikać z pobranych fragmentów.

### Błąd 4: Mylenie RAG z pamięcią rozmowy

RAG pobiera wiedzę z bazy dokumentów. Pamięć rozmowy przechowuje kontekst interakcji. To są różne warstwy.

### Błąd 5: Mylenie RAG z checkpointingiem

Checkpoint pozwala wznowić graf. RAG pozwala wyszukać wiedzę. To nie jest to samo.

### Błąd 6: Brak testów dla pytań bez odpowiedzi

Dobry system RAG musi umieć powiedzieć:

```text
Nie wiem na podstawie dostępnych źródeł.
```

---

## Materiały źródłowe do `docs/ai_workflow/`

Przygotuj lub pobierz:

```text
21_rag_overview.md
22_text_splitters_and_chunking.md
23_embeddings_overview.md
24_vector_stores_overview.md
25_retrieval_tool_patterns.md
26_rag_evaluation.md
27_citation_and_grounding.md
```

### Minimalna funkcja każdego źródła

| Plik | Funkcja w szkoleniu |
|---|---|
| `21_rag_overview.md` | podstawy Retrieval-Augmented Generation |
| `22_text_splitters_and_chunking.md` | strategie dzielenia dokumentów |
| `23_embeddings_overview.md` | czym są embeddingi i kiedy ich używać |
| `24_vector_stores_overview.md` | jak przechowywać i przeszukiwać wektory |
| `25_retrieval_tool_patterns.md` | retrieval jako narzędzie agenta |
| `26_rag_evaluation.md` | testowanie jakości odpowiedzi RAG |
| `27_citation_and_grounding.md` | cytowania, grounding i wykrywanie halucynacji |

---

## Arkusz umiejętności Fazy 5 — TSV do Excela

```tsv
Kategoria	Konkretna umiejętność	Priorytet	Status	Czas na naukę	Dowód zaliczenia
RAG	Wczytywanie dokumentów do SourceDocument	Krytyczny	[ ]	1 dzień	Inventory dokumentów zapisane jako JSON
RAG	Chunking Markdown według nagłówków	Krytyczny	[ ]	1-2 dni	Każdy chunk ma source_id, path, heading_path i chunk_index
RAG	Projektowanie metadanych chunków	Krytyczny	[ ]	1 dzień	Można odtworzyć źródło każdego chunka
RAG	Keyword retrieval baseline	Wysoki	[ ]	1 dzień	Retriever zwraca top_k wyników z score
RAG	Embedding retrieval	Średni	[ ]	2-3 dni	Query i chunki są porównywane przez wektory
RAG	Retrieval jako Tool Node	Krytyczny	[ ]	1-2 dni	retrieval_hits trafiają do state
RAG	Generowanie CitedAnswer	Krytyczny	[ ]	1-2 dni	Odpowiedź zawiera used_chunk_ids
RAG	Obsługa braku informacji	Krytyczny	[ ]	1 dzień	System odmawia odpowiedzi bez źródeł
RAG	Citation checking	Wysoki	[ ]	1-2 dni	used_chunk_ids istnieją w retrieval_hits
RAG	Ewaluacja RAG	Wysoki	[ ]	2 dni	Testy obejmują pytania z odpowiedzią i bez odpowiedzi
LangGraph	RAG workflow state	Krytyczny	[ ]	1 dzień	State zawiera retrieval_hits, cited_answer, citation_status
LangGraph	RetrievalRouter	Wysoki	[ ]	1 dzień	Router rozdziela FOUND / EMPTY / ERROR
Dokumentacja	Generowanie raportów ze źródeł	Średni	[ ]	1-2 dni	Raport wskazuje użyte dokumenty i braki informacji
```

---

## Następna faza

Po Fazie 5 przejdź do:

```text
Faza 6: Integracja całości i workflow produkcyjny
```

Tam połączysz:

```text
Structured Outputs
Tool Calling
LangGraph StateGraph
Subprocess / AST
Human-in-the-Loop
Checkpointers
Reflexion
RAG
dokumentację
release workflow
```

w jeden spójny system aplikacyjny.
