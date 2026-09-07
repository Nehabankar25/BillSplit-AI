"""
Pydantic v2 models for bill splitting.

Key design decision — ItemAssignment.everyone flag
───────────────────────────────────────────────────
An empty person_ids list is ambiguous: it could mean "everyone" or "nobody
assigned yet". We use an explicit `everyone: bool` flag to disambiguate:

  person_ids=["a","b"], everyone=False  → split between a and b
  person_ids=[],        everyone=True   → split among all participants
  person_ids=[],        everyone=False  → NOT YET ASSIGNED (validation error)

The model_validator on SplitRequest enforces that no item reaches the
calculation engine in the "not yet assigned" state. The API returns a 422
with a clear message listing which item indices are unassigned.
"""

from decimal import Decimal, ROUND_HALF_UP
from typing import Optional

from pydantic import BaseModel, ConfigDict, field_serializer, model_validator

from backend.models.bill import Bill


def _fmt(v: Optional[Decimal]) -> Optional[str]:
    if v is None:
        return None
    return str(v.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


class Person(BaseModel):
    id: str
    name: str


class ItemAssignment(BaseModel):
    """
    Assignment of a single bill item to participants.

    everyone=True  → item is shared equally among all req.people
    everyone=False → item is shared among the listed person_ids
    If neither person_ids nor everyone is set → validation error (unassigned)
    """

    item_id: str
    person_ids: list[str] = []
    everyone: bool = False


class SplitRequest(BaseModel):
    bill: Bill
    people: list[Person]
    assignments: list[ItemAssignment]

    model_config = ConfigDict(populate_by_name=True)

    @model_validator(mode="after")
    def check_all_items_assigned(self) -> "SplitRequest":
        items_by_id = {item.item_id: item for item in self.bill.items}
        unassigned = [
            a.item_id
            for a in self.assignments
            if not a.everyone and not a.person_ids
        ]
        if unassigned:
            names = [
                items_by_id[item_id].name
                for item_id in unassigned
                if item_id in items_by_id
            ]
            raise ValueError(
                f"Items with IDs {unassigned} ({', '.join(names)}) are not "
                "assigned to anyone. Assign each item to specific people or mark "
                "it as 'Everyone'."
            )
        if not self.people:
            raise ValueError("At least one person is required.")
        if len(self.assignments) != len(self.bill.items):
            raise ValueError(
                f"Expected {len(self.bill.items)} assignments, "
                f"got {len(self.assignments)}."
            )
        return self


class PersonBreakdownLine(BaseModel):
    """A single line in a person's itemised breakdown."""

    label: str
    amount: Decimal

    @field_serializer("amount")
    def serialize_decimal(self, v: Decimal) -> str:
        return _fmt(v)  # type: ignore[return-value]


class PersonSplit(BaseModel):
    """Full split result for one person."""

    person: Person
    food_total: Decimal
    tax_share: Decimal
    service_charge_share: Decimal
    discount_share: Decimal
    grand_total: Decimal
    breakdown: list[PersonBreakdownLine]  # per-item lines for the summary card

    @field_serializer("food_total", "tax_share", "service_charge_share",
                      "discount_share", "grand_total")
    def serialize_decimal(self, v: Decimal) -> str:
        return _fmt(v)  # type: ignore[return-value]


class SplitResult(BaseModel):
    """
    Final result returned to the frontend.

    Guarantee: sum(p.grand_total for p in people_splits) == bill_calculated_total
    (enforced by the penny reconciliation step in calculation_service).
    """

    people_splits: list[PersonSplit]
    bill_calculated_total: Decimal
    sum_of_splits: Decimal  # should equal bill_calculated_total exactly
    mismatch_warning: Optional[str] = None

    @field_serializer("bill_calculated_total", "sum_of_splits")
    def serialize_decimal(self, v: Decimal) -> str:
        return _fmt(v)  # type: ignore[return-value]
