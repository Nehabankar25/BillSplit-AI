"""
extraction_service.py — Post-processing and validation of Gemini's raw extraction.

Responsibilities:
  - Receive a BillExtract (Gemini's output, validated by Pydantic)
  - Python computes calculated_total — NEVER delegated to the LLM
  - Python detects total_mismatch — only when printed_total is not None
  - Returns a full Bill model ready for the frontend

Tax order-of-operations assumption (see README for full discussion):
  calculated_total = subtotal + tax + service_charge − discount

This assumes:
  • Tax/GST is computed on the full pre-discount subtotal
  • Discount is a bill-level reduction applied after all charges

Bills that compute tax on the post-discount subtotal will produce a small
mismatch that reflects a modeling assumption difference, not an extraction
error. The UI surfaces this context so the user can make an informed decision.

Mismatch tolerance: ₹1.00
This accommodates rounding in thermal printers and single-digit OCR errors
without producing noisy false-positive warnings.
"""

import uuid
from decimal import Decimal

from backend.models.bill import Bill, BillExtract, BillItem

_MISMATCH_TOLERANCE = Decimal("1.00")


def build_bill(extract: BillExtract) -> Bill:
    """
    Compute calculated_total and total_mismatch, then return a full Bill.

    Args:
        extract: Validated BillExtract from gemini_service.

    Returns:
        Bill with calculated_total set by Python, total_mismatch flag, and stable item IDs.
    """
    items = [
        BillItem(
            **item.model_dump(),
            item_id=str(uuid.uuid4())[:8],
            manually_added=False,
        )
        for item in extract.items
    ]

    printed_subtotal = extract.subtotal
    items_subtotal = sum(item.total for item in items)
    subtotal_mismatch = abs(items_subtotal - printed_subtotal) > _MISMATCH_TOLERANCE

    calculated_total = (
        items_subtotal
        + extract.tax
        + extract.service_charge
        - extract.discount
    )

    if extract.printed_total is not None:
        total_mismatch = (
            abs(calculated_total - extract.printed_total) > _MISMATCH_TOLERANCE
        )
    else:
        total_mismatch = False

    return Bill(
        items=items,
        subtotal=printed_subtotal,
        printed_subtotal=printed_subtotal,
        items_subtotal=items_subtotal,
        subtotal_mismatch=subtotal_mismatch,
        tax=extract.tax,
        service_charge=extract.service_charge,
        discount=extract.discount,
        printed_total=extract.printed_total,
        calculated_total=calculated_total,
        total_mismatch=total_mismatch,
    )


def revalidate_bill(data: dict) -> Bill:
    """
    Re-validate a human-edited bill dict submitted from the review screen.

    The frontend sends back the full bill JSON after the user has corrected
    any mis-extracted values. We re-parse it, recalculate calculated_total,
    and re-run the mismatch check using the corrected numbers while preserving item IDs.

    Args:
        data: Raw dict from the request body (human-edited bill fields).

    Returns:
        Updated Bill with recalculated totals and preserved item IDs.

    Raises:
        ValidationError: If the submitted data doesn't match Bill schema.
    """
    # Ensure every item has an item_id and manually_added flag
    raw_items = data.get("items", [])
    for item in raw_items:
        if isinstance(item, dict):
            if not item.get("item_id"):
                item["item_id"] = str(uuid.uuid4())[:8]
                item["manually_added"] = item.get("manually_added", True)

    # Parse and validate as Bill (raises ValidationError on bad input)
    bill = Bill.model_validate(data)

    printed_subtotal = bill.printed_subtotal or bill.subtotal
    items_subtotal = sum(item.total for item in bill.items)
    subtotal_mismatch = abs(items_subtotal - printed_subtotal) > _MISMATCH_TOLERANCE

    calculated_total = (
        items_subtotal
        + bill.tax
        + bill.service_charge
        - bill.discount
    )

    if bill.printed_total is not None:
        total_mismatch = (
            abs(calculated_total - bill.printed_total) > _MISMATCH_TOLERANCE
        )
    else:
        total_mismatch = False

    return bill.model_copy(update={
        "subtotal": printed_subtotal,
        "printed_subtotal": printed_subtotal,
        "items_subtotal": items_subtotal,
        "subtotal_mismatch": subtotal_mismatch,
        "calculated_total": calculated_total,
        "total_mismatch": total_mismatch,
    })
