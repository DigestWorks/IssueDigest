"""Explicit model/profile and reservation policy shared by storage and runtime."""

from decimal import Decimal

SOL_MODEL = "gpt-6.1-sol"
ASTRA_MODEL = "gpt-6-astra"
EVIDENCE_V5 = "guarded-question-evidence-v5"


def briefing_model_allowed(model: object) -> bool:
    return type(model) is str and model in (SOL_MODEL, ASTRA_MODEL)


def evidence_model_allowed(model: object, profile: object) -> bool:
    if type(model) is not str or type(profile) is not str:
        return False
    return (
        model == SOL_MODEL
        and profile in ("guarded-question-evidence-v2", "guarded-question-evidence-v3", EVIDENCE_V5)
    ) or (model == ASTRA_MODEL and profile == EVIDENCE_V5)


def reservation_allowed(model: object, amount: object) -> bool:
    if not briefing_model_allowed(model) or type(amount) is not Decimal:
        return False
    return (
        amount.is_finite()
        and Decimal("0") < amount <= Decimal("10")
        and amount == amount.quantize(Decimal(".01"))
        and (model != ASTRA_MODEL or amount >= Decimal("1"))
    )
