"""Lekcja 04: projektowanie promptu pod cache'owanie.

Ten plik nie wywoluje realnego API LLM. Cel jest edukacyjny:
pokazuje, jak dzielic prompt na stabilny prefiks i dynamiczna czesc,
aby przyszle wywolania modelu mogly korzystac z prompt caching.
"""

from __future__ import annotations

from hashlib import sha256
from typing import Literal

from pydantic import BaseModel, Field


CachePolicy = Literal["stable", "dynamic"]


class PromptBlock(BaseModel):
    """Pojedynczy blok promptu.

    Bloki stabilne powinny byc identyczne miedzy wywolaniami.
    Bloki dynamiczne zmieniaja sie dla kazdego zapytania uzytkownika.
    """

    name: str = Field(description="Nazwa bloku, np. system, tools, user_question")
    content: str = Field(description="Tresć bloku promptu")
    cache_policy: CachePolicy = Field(description="Czy blok nalezy do stabilnego prefiksu")


class PromptPlan(BaseModel):
    """Plan promptu przygotowanego pod cache'owanie."""

    stable_blocks: list[PromptBlock]
    dynamic_blocks: list[PromptBlock]
    stable_prefix: str
    dynamic_suffix: str
    stable_prefix_hash: str


class SimulatedCacheResult(BaseModel):
    """Wynik symulacji cache hit / cache miss."""

    stable_prefix_hash: str
    cache_hit: bool
    cached_prefix_chars: int
    dynamic_suffix_chars: int
    explanation: str


STABLE_SYSTEM_INSTRUCTIONS = """Jesteś asystentem do analizy zgłoszeń klientów.
Zwracaj odpowiedzi techniczne, precyzyjne i zgodne z podanym schematem.
Nie zgaduj danych, których nie ma w wejściu.
"""

STABLE_TOOL_CONTRACTS = """Dostępne narzędzia aplikacji:
1. search_knowledge_base(query: str) -> SearchResult
2. classify_ticket(text: str) -> TicketClassification
3. calculate_refund_amount(monthly_price: float, duplicated_charges: int) -> RefundResult

Zasada: model może zaproponować użycie narzędzia, ale funkcję wykonuje aplikacja.
"""

STABLE_OUTPUT_SCHEMA = """Oczekiwany format odpowiedzi:
{
  "intent": "answer" | "tool_call" | "needs_human",
  "summary": "krótkie streszczenie decyzji",
  "tool_name": "nazwa narzędzia albo null",
  "tool_arguments": "argumenty narzędzia albo null"
}
"""

STABLE_KNOWLEDGE_BASE = """Fragment stałej wiedzy domenowej:
- Zgłoszenia billingowe dotyczą płatności, faktur, zwrotów i subskrypcji.
- Zgłoszenia techniczne dotyczą błędów logowania, awarii i problemów z usługą.
- Zgłoszenia sprzedażowe dotyczą ofert, planów i rozszerzeń konta.
"""


def join_blocks(blocks: list[PromptBlock]) -> str:
    """Łączy bloki w deterministycznej kolejności.

    Uwaga: w prawdziwym prompt caching liczy się identyczny prefiks.
    Nie dodawaj tu losowych identyfikatorów, dat ani zmiennych danych.
    """
    return "\n\n".join(f"## {block.name}\n{block.content}" for block in blocks)


def hash_text(text: str) -> str:
    """Zwraca skrócony hash tekstu używany jako dydaktyczny cache key."""
    return sha256(text.encode("utf-8")).hexdigest()[:16]


def build_prompt_plan(user_question: str) -> PromptPlan:
    """Buduje prompt pod cache'owanie: stabilny prefiks + dynamiczny sufiks."""
    stable_blocks = [
        PromptBlock(
            name="system_instructions",
            content=STABLE_SYSTEM_INSTRUCTIONS,
            cache_policy="stable",
        ),
        PromptBlock(
            name="tool_contracts",
            content=STABLE_TOOL_CONTRACTS,
            cache_policy="stable",
        ),
        PromptBlock(
            name="output_schema",
            content=STABLE_OUTPUT_SCHEMA,
            cache_policy="stable",
        ),
        PromptBlock(
            name="knowledge_base",
            content=STABLE_KNOWLEDGE_BASE,
            cache_policy="stable",
        ),
    ]

    dynamic_blocks = [
        PromptBlock(
            name="current_user_question",
            content=user_question,
            cache_policy="dynamic",
        )
    ]

    stable_prefix = join_blocks(stable_blocks)
    dynamic_suffix = join_blocks(dynamic_blocks)

    return PromptPlan(
        stable_blocks=stable_blocks,
        dynamic_blocks=dynamic_blocks,
        stable_prefix=stable_prefix,
        dynamic_suffix=dynamic_suffix,
        stable_prefix_hash=hash_text(stable_prefix),
    )


def simulate_provider_cache(
    plan: PromptPlan,
    cache_store: set[str],
) -> SimulatedCacheResult:
    """Symuluje, czy stabilny prefiks byl juz widziany przez provider cache."""
    cache_hit = plan.stable_prefix_hash in cache_store

    if not cache_hit:
        cache_store.add(plan.stable_prefix_hash)

    explanation = (
        "CACHE HIT: stabilny prefiks byl juz przetworzony. "
        "W realnym API moze to zmniejszyc koszt i opoznienie."
        if cache_hit
        else "CACHE MISS: stabilny prefiks pojawia sie pierwszy raz albo zostal zmieniony."
    )

    return SimulatedCacheResult(
        stable_prefix_hash=plan.stable_prefix_hash,
        cache_hit=cache_hit,
        cached_prefix_chars=len(plan.stable_prefix),
        dynamic_suffix_chars=len(plan.dynamic_suffix),
        explanation=explanation,
    )


def main() -> None:
    """Pokazuje, kiedy cache zostaje trafiony, a kiedy zerwany."""
    cache_store: set[str] = set()

    questions = [
        "Klient pisze, że pobrano mu podwójną opłatę za subskrypcję.",
        "Klient pyta, czy może dostać fakturę za ostatni miesiąc.",
    ]

    for question in questions:
        plan = build_prompt_plan(question)
        result = simulate_provider_cache(plan, cache_store)
        print(result.model_dump_json(indent=4))

    # Dydaktyczny przykład zerwania cache: zmiana stabilnego prefiksu.
    global STABLE_SYSTEM_INSTRUCTIONS
    STABLE_SYSTEM_INSTRUCTIONS = STABLE_SYSTEM_INSTRUCTIONS + "\nNowa instrukcja dodana po czasie."

    changed_plan = build_prompt_plan(questions[0])
    changed_result = simulate_provider_cache(changed_plan, cache_store)
    print(changed_result.model_dump_json(indent=4))


if __name__ == "__main__":
    main()
