"""
Pydantic v2 models for bill data.

Two-tier item design:
- BillItemExtract: shape Gemini is constrained to via response_schema.
  Contains only fields that exist on the physical bill.
  No Python-generated fields (no item_id, no manually_added).
- BillItem: extends BillItemExtract with stable item_id (assigned by Python,
  never by Gemini) and manually_added flag (True when user added the row in
  the review screen rather than Gemini extracting it).

Two-tier bill design:
- BillExtract: the shape Gemini returns and is constrained to via
  response_schema. items is list[BillItemExtract].
- Bill: extends BillExtract with Python-computed fields. items is overridden
  to list[BillItem] (richer type with stable IDs).

Decimal rules
─────────────
All money fields use Decimal. Construction always goes through Pydantic's field
validation (which uses str() internally) or explicit Decimal(str(x)).
NEVER write Decimal(some_float) — it inherits binary representation noise.

Serialization
─────────────
@field_serializer ensures every money field comes out as a clean "12.34" string
when the model is serialized to JSON for the frontend.
"""

from decimal import Decimal, ROUND_HALF_UP
from typing import Optional

from pydantic import BaseModel, ConfigDict, field_serializer


def _fmt(v: Optional[Decimal]) -> Optional[str]:
    """Serialize a Decimal money value to a clean 2 d.p. string, or None."""
    if v is None:
        return None
    return str(v.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


class BillItemExtract(BaseModel):
    """
    A single line item exactly as Gemini extracts it — no Python-generated fields.

    Used as the item type inside BillExtract (the Gemini response_schema).
    Gemini MUST NOT be asked to generate item_id or manually_added — those are
    Python concerns assigned after extraction.
    """

    name: str
    quantity: Decimal
    unit_price: Decimal
    total: Decimal
    confidence: float  # 0.0–1.0 — model-estimated extraction confidence

    model_config = ConfigDict(populate_by_name=True)

    @field_serializer("quantity", "unit_price", "total")
    def serialize_decimal(self, v: Decimal) -> str:
        return _fmt(v)  # type: ignore[return-value]


class BillItem(BillItemExtract):
    """
    BillItemExtract enriched by Python with a stable identity and origin flag.

    item_id   — stable 8-char hex string assigned by extraction_service.build_bill().
                Persists through the entire flow (review edits, assign screen,
                split calculation). Replaces the fragile item_index approach:
                deleting an item no longer shifts indices and breaks assignments.

    manually_added — True when the user added this row in the review screen
                     (not extracted by Gemini). The frontend shows a distinct
                     '✏️ Manual' badge rather than an AI confidence badge.
    """

    item_id: str
    manually_added: bool = False


class BillExtract(BaseModel):
    """
    Exactly what Gemini is asked to extract — nothing more.
    Used as response_schema on the Gemini API call so the model is
    constrained to this shape rather than being asked nicely via prompt.

    items uses list[BillItemExtract] (no item_id / manually_added) so the
    Gemini schema stays clean and Gemini is never asked to invent IDs.

    printed_total is Optional because it may be:
      - Present and correct
      - Present but wrong (the interesting test case)
      - Absent or unreadable (smudged thermal print, torn receipt, etc.)
    When None, extraction_service skips the mismatch check entirely,
    preventing false-positive warnings on every illegible-total bill.
    """

    items: list[BillItemExtract]
    subtotal: Decimal
    tax: Decimal
    service_charge: Decimal
    discount: Decimal
    printed_total: Optional[Decimal] = None  # None = unreadable/absent

    model_config = ConfigDict(populate_by_name=True)

    @field_serializer("subtotal", "tax", "service_charge", "discount")
    def serialize_decimal(self, v: Decimal) -> str:
        return _fmt(v)  # type: ignore[return-value]

    @field_serializer("printed_total")
    def serialize_optional_decimal(self, v: Optional[Decimal]) -> Optional[str]:
        return _fmt(v)


class Bill(BillExtract):
    """
    Full bill with Python-computed fields and stable item IDs. Never sent to Gemini.

    Overrides items to list[BillItem] so every item carries a stable item_id
    that persists through review edits, assignment, and split calculation.

    Tax order-of-operations assumption (documented in README):
        calculated_total = subtotal + tax + service_charge − discount
    This assumes tax is applied to the full pre-discount subtotal, and
    discount is a bill-level reduction applied after all charges.
    Bills that compute tax on the post-discount subtotal will produce
    a small total_mismatch that reflects a modeling assumption difference,
    not an extraction error.

    total_mismatch is ONLY True when:
      1. printed_total is not None (we can actually compare), AND
      2. abs(calculated_total − printed_total) > ₹1.00 tolerance
    """

    items: list[BillItem]  # type: ignore[assignment]  # narrowed from list[BillItemExtract]
    printed_subtotal: Optional[Decimal] = None
    items_subtotal: Decimal = Decimal("0.00")
    subtotal_mismatch: bool = False
    calculated_total: Decimal = Decimal("0.00")
    total_mismatch: bool = False
    currency: str = "₹"

    @field_serializer("calculated_total", "items_subtotal")
    def serialize_calculated(self, v: Decimal) -> str:
        return _fmt(v)  # type: ignore[return-value]

    @field_serializer("printed_subtotal")
    def serialize_printed_subtotal(self, v: Optional[Decimal]) -> Optional[str]:
        return _fmt(v)
