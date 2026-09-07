"""
calculation_service.py — Proportional bill splitting with exact penny reconciliation.

Algorithm
─────────
Step 1: Distribute item costs
  For each item, split its total equally among its assigned people.
  If everyone=True, split among all participants.

Step 2: Proportional charges
  Each person's share of tax, service charge, and discount is proportional
  to the food they consumed — NOT divided equally by headcount.

  Rationale for proportional discount:
    A bill-level discount (e.g. loyalty coupon, negotiated reduction) applies
    to the whole bill. Someone who ate more food ordered more and therefore
    benefits proportionally more from that discount. This is the fairest
    interpretation when no per-item discount information is available.

  Edge case — zero food total:
    If no food is assigned (total_food == 0), charges are split equally.
    This prevents a division-by-zero and is a sensible fallback.

Step 3: Compute raw grand totals
  grand_total = food + tax_share + service_charge_share − discount_share

Step 4: Penny reconciliation
  Raw totals have fractional cents after rounding. We:
    a) Round each person's grand_total to 2 d.p.
    b) Compute remainder = calculated_total − sum(rounded totals)
    c) Add the entire remainder to the first person's total.
  The remainder is always < (0.01 × n_people), so it is at most a few pence.
  This guarantees: sum(all grand_totals) == bill.calculated_total exactly.

Decimal safety:
  All arithmetic uses Decimal. No float is ever converted to Decimal directly.
  Intermediate division uses sufficient precision; final rounding uses
  quantize(Decimal("0.01"), ROUND_HALF_UP).
"""

from decimal import Decimal, ROUND_HALF_UP

from backend.models.bill import Bill
from backend.models.split import (
    ItemAssignment,
    Person,
    PersonBreakdownLine,
    PersonSplit,
    SplitRequest,
    SplitResult,
)

_TWO_DP = Decimal("0.01")


def _round2(v: Decimal) -> Decimal:
    return v.quantize(_TWO_DP, rounding=ROUND_HALF_UP)


def calculate_split(req: SplitRequest) -> SplitResult:
    """
    Compute the exact amount owed by each person.

    Precondition: SplitRequest has already been validated by Pydantic
    (model_validator ensures no unassigned items).

    Returns:
        SplitResult with per-person breakdowns and reconciliation guarantee.
    """
    bill: Bill = req.bill
    people: list[Person] = req.people
    assignments: list[ItemAssignment] = req.assignments
    n = Decimal(len(people))
    people_by_id = {p.id: p for p in people}

    # ── Step 1: Distribute item costs ───────────────────────────────────────
    # food[person_id] = total food cost attributed to this person
    food: dict[str, Decimal] = {p.id: Decimal("0") for p in people}
    # item_lines[person_id] = list of (item_name, share_amount)
    item_lines: dict[str, list[tuple[str, Decimal]]] = {p.id: [] for p in people}

    items_by_id = {item.item_id: item for item in bill.items}

    for assignment in assignments:
        item = items_by_id.get(assignment.item_id)
        if not item:
            continue

        if assignment.everyone:
            recipients = people
        else:
            recipients = [people_by_id[pid] for pid in assignment.person_ids
                          if pid in people_by_id]

        if not recipients:
            # Safety fallback (shouldn't reach here after model_validator)
            continue

        share = item.total / Decimal(len(recipients))
        for person in recipients:
            food[person.id] += share
            item_lines[person.id].append((item.name, share))

    # ── Step 2: Proportional charges ────────────────────────────────────────
    total_food = sum(food.values())

    ratios: dict[str, Decimal] = {}
    for person in people:
        if total_food == Decimal("0"):
            # Edge case: nothing assigned — split charges equally
            ratios[person.id] = Decimal("1") / n
        else:
            ratios[person.id] = food[person.id] / total_food

    tax_shares: dict[str, Decimal] = {
        p.id: bill.tax * ratios[p.id] for p in people
    }
    sc_shares: dict[str, Decimal] = {
        p.id: bill.service_charge * ratios[p.id] for p in people
    }
    # Discount reduces each person's bill proportionally to their food share.
    # See module docstring for rationale.
    disc_shares: dict[str, Decimal] = {
        p.id: bill.discount * ratios[p.id] for p in people
    }

    # ── Step 3: Raw grand totals ─────────────────────────────────────────────
    raw_totals: dict[str, Decimal] = {}
    for person in people:
        raw_totals[person.id] = (
            food[person.id]
            + tax_shares[person.id]
            + sc_shares[person.id]
            - disc_shares[person.id]
        )

    # ── Step 4: Penny reconciliation ─────────────────────────────────────────
    rounded_totals: dict[str, Decimal] = {
        pid: _round2(v) for pid, v in raw_totals.items()
    }
    remainder = bill.calculated_total - sum(rounded_totals.values())
    # Assign the entire remainder (always < 0.01 × n) to the first person
    first_pid = people[0].id
    rounded_totals[first_pid] = _round2(rounded_totals[first_pid] + remainder)

    # ── Build PersonSplit objects ─────────────────────────────────────────────
    person_splits: list[PersonSplit] = []
    for person in people:
        pid = person.id

        # Itemised breakdown lines
        breakdown: list[PersonBreakdownLine] = []
        for name, amount in item_lines[pid]:
            breakdown.append(PersonBreakdownLine(label=name, amount=_round2(amount)))

        if bill.tax > Decimal("0"):
            breakdown.append(PersonBreakdownLine(
                label="Tax / GST", amount=_round2(tax_shares[pid])
            ))
        if bill.service_charge > Decimal("0"):
            breakdown.append(PersonBreakdownLine(
                label="Service Charge", amount=_round2(sc_shares[pid])
            ))
        if bill.discount > Decimal("0"):
            breakdown.append(PersonBreakdownLine(
                label="Discount", amount=_round2(-disc_shares[pid])  # negative = saving
            ))

        person_splits.append(PersonSplit(
            person=person,
            food_total=_round2(food[pid]),
            tax_share=_round2(tax_shares[pid]),
            service_charge_share=_round2(sc_shares[pid]),
            discount_share=_round2(disc_shares[pid]),
            grand_total=rounded_totals[pid],
            breakdown=breakdown,
        ))

    sum_of_splits = sum(ps.grand_total for ps in person_splits)

    # Build mismatch warning string if the printed total differs
    mismatch_warning: str | None = None
    if bill.total_mismatch and bill.printed_total is not None:
        diff = abs(bill.calculated_total - bill.printed_total)
        mismatch_warning = (
            f"The printed total ({bill.currency}{bill.printed_total}) "
            f"does not match the calculated total ({bill.currency}{bill.calculated_total}). "
            f"Difference: {bill.currency}{_round2(diff)}. "
            "The split uses the calculated total."
        )

    return SplitResult(
        people_splits=person_splits,
        bill_calculated_total=bill.calculated_total,
        sum_of_splits=sum_of_splits,
        mismatch_warning=mismatch_warning,
    )
