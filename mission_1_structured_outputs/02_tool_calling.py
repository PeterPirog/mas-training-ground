from pydantic import BaseModel, Field


class RefundArgs(BaseModel):
    """Argumenty narzędzia obliczającego kwotę zwrotu."""

    monthly_price: float = Field(gt=0, description="Cena miesięcznej subskrypcji")
    duplicated_charges: int = Field(
        ge=1,
        le=12,
        description="Liczba nadmiarowo pobranych opłat",
    )


class RefundResult(BaseModel):
    """Wynik obliczenia zwrotu."""

    refund_amount: float
    currency: str = "PLN"


def calculate_refund_amount(args: RefundArgs) -> RefundResult:
    """Oblicza kwotę zwrotu dla klienta."""
    amount = args.monthly_price * args.duplicated_charges

    return RefundResult(
        refund_amount=round(amount, 2),
        currency="PLN",
    )


def main() -> None:
    args = RefundArgs(
        monthly_price=49.99,
        duplicated_charges=1,
    )

    result = calculate_refund_amount(args)

    print(result.model_dump_json(indent=4))


if __name__ == "__main__":
    main()