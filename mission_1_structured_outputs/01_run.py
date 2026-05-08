import os
import json
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from openai import OpenAI
from typing import Literal


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
    summary: str = Field(description="Jednozdaniowe, zwięzłe podsumowanie problemu")


def main() -> None:
    """Główna funkcja wykonująca zapytanie do lokalnego modelu LLM."""
    load_dotenv()

    client = OpenAI(
        base_url=os.getenv("OPENAI_BASE_URL"),
        api_key=os.getenv("OPENAI_API_KEY", "not-needed"),
    )
    model_name = os.getenv("MODEL_NAME")

    # Symulujemy chaotyczną wiadomość e-mail od klienta
    customer_email = (
        "Dzień dobry, piszę do was już trzeci raz! Z mojego konta pobrano podwójną "
        "opłatę za subskrypcję w tym miesiącu. Jestem wściekły, bo potrzebuję tych pieniędzy. "
        "Proszę o natychmiastowy zwrot na moją kartę z końcówką 4432, inaczej rezygnuję z usług."
    )

    schema_json = json.dumps(TicketAnalysis.model_json_schema(), indent=2)

    try:
        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Jesteś analitykiem zgłoszeń. Zwracasz WYŁĄCZNIE czysty tekst w formacie JSON.\n"
                        "Nie dodawaj żadnych powitań, komentarzy ani znaczników markdown.\n\n"
                        f"Twój JSON musi ściśle pasować do tego schematu:\n{schema_json}"
                    ),
                },
                {
                    "role": "user",
                    "content": f"Przeanalizuj poniższą wiadomość i zwróć JSON:\n{customer_email}",
                },
            ],
            response_format={"type": "json_object"},
            temperature=0.1,
        )

        raw_content = response.choices[0].message.content.strip()

        # Zabezpieczenie przed znacznikami markdown
        if raw_content.startswith("```json"):
            raw_content = raw_content[7:]
        if raw_content.startswith("```"):
            raw_content = raw_content[3:]
        if raw_content.endswith("```"):
            raw_content = raw_content[:-3]

        raw_content = raw_content.strip()

        # Walidacja Pydantic
        result = TicketAnalysis.model_validate_json(raw_content)

        print("\nSUKCES. Zgłoszenie zostało przeprocesowane w obiekt Pydantic:")
        print(result.model_dump_json(indent=4))

    except Exception as error:
        print(f"\nBłąd wykonania: {error}")
        if "raw_content" in locals():
            print(f"Surowa odpowiedź modelu:\n{raw_content}")


if __name__ == "__main__":
    main()
