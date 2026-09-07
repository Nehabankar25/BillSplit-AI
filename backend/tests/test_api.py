"""
Automated test suite for BillSplit AI backend.
Tests:
- Health check endpoint
- Bill re-validation endpoint (/api/bills/validate)
- Split calculation endpoint (/api/split/calculate)
- Penny reconciliation rule (₹100 / 3)
- Proportional taxes & service charge allocation
- Mismatch detection on printed vs calculated total
- ItemAssignment unassigned validation
"""

import sys
from pathlib import Path

_repo_root = str(Path(__file__).resolve().parent.parent.parent)
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)

from decimal import Decimal
from fastapi.testclient import TestClient

from backend.main import app
from backend.models.bill import Bill, BillItem
from backend.models.split import Person, ItemAssignment, SplitRequest
from backend.services.calculation_service import calculate_split

client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "BillSplit AI"}


def test_penny_reconciliation_exact_cents():
    """Verify that ₹100 split 3 ways has penny reconciliation: sum(splits) == ₹100."""
    items = [
        BillItem(item_id="item-1", name="Shared Dish", quantity=1, unit_price=Decimal("100.00"), total=Decimal("100.00"), confidence=1.0)
    ]
    bill = Bill(
        items=items,
        subtotal=Decimal("100.00"),
        tax=Decimal("0.00"),
        service_charge=Decimal("0.00"),
        discount=Decimal("0.00"),
        printed_total=Decimal("100.00"),
        calculated_total=Decimal("100.00"),
        total_mismatch=False,
    )
    people = [Person(id="p1", name="P1"), Person(id="p2", name="P2"), Person(id="p3", name="P3")]
    assignments = [ItemAssignment(item_id="item-1", person_ids=[], everyone=True)]
    req = SplitRequest(bill=bill, people=people, assignments=assignments)

    res = calculate_split(req)
    totals = [p.grand_total for p in res.people_splits]
    assert sum(totals) == Decimal("100.00")
    assert res.sum_of_splits == Decimal("100.00")


def test_split_calculate_api():
    payload = {
        "bill": {
            "items": [
                {"item_id": "item-1", "name": "Biryani", "quantity": 1, "unit_price": "500.00", "total": "500.00", "confidence": 0.95},
                {"item_id": "item-2", "name": "Soda", "quantity": 2, "unit_price": "50.00", "total": "100.00", "confidence": 0.98}
            ],
            "subtotal": "600.00",
            "tax": "30.00",
            "service_charge": "60.00",
            "discount": "0.00",
            "printed_total": "690.00",
            "calculated_total": "690.00",
            "total_mismatch": False,
            "currency": "₹"
        },
        "people": [
            {"id": "p1", "name": "Alice"},
            {"id": "p2", "name": "Bob"}
        ],
        "assignments": [
            {"item_id": "item-1", "person_ids": ["p1"], "everyone": False},
            {"item_id": "item-2", "person_ids": ["p2"], "everyone": False}
        ]
    }
    response = client.post("/api/split/calculate", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["bill_calculated_total"] == "690.00"
    assert data["sum_of_splits"] == "690.00"

    # Alice had 500/600 (5/6) of food -> 5/6 of 30 tax = 25, 5/6 of 60 sc = 50 -> 575.00
    alice = next(p for p in data["people_splits"] if p["person"]["name"] == "Alice")
    assert alice["food_total"] == "500.00"
    assert alice["tax_share"] == "25.00"
    assert alice["service_charge_share"] == "50.00"
    assert alice["grand_total"] == "575.00"

    # Bob had 100/600 (1/6) of food -> 1/6 of 30 tax = 5, 1/6 of 60 sc = 10 -> 115.00
    bob = next(p for p in data["people_splits"] if p["person"]["name"] == "Bob")
    assert bob["food_total"] == "100.00"
    assert bob["tax_share"] == "5.00"
    assert bob["service_charge_share"] == "10.00"
    assert bob["grand_total"] == "115.00"


def test_unassigned_item_fails_validation():
    payload = {
        "bill": {
            "items": [
                {"item_id": "item-1", "name": "Biryani", "quantity": 1, "unit_price": "500.00", "total": "500.00", "confidence": 0.95}
            ],
            "subtotal": "500.00",
            "tax": "0.00",
            "service_charge": "0.00",
            "discount": "0.00",
            "printed_total": "500.00",
            "calculated_total": "500.00",
            "total_mismatch": False,
            "currency": "₹"
        },
        "people": [{"id": "p1", "name": "Alice"}],
        "assignments": [
            # Neither person_ids nor everyone=True -> invalid unassigned state
            {"item_id": "item-1", "person_ids": [], "everyone": False}
        ]
    }
    response = client.post("/api/split/calculate", json=payload)
    assert response.status_code == 422
    assert "not assigned to anyone" in response.text


def test_bill_validate_recalculates_total():
    raw_data = {
        "items": [
            {"item_id": "item-a", "name": "Item A", "quantity": 2, "unit_price": "100.00", "total": "200.00", "confidence": 0.9},
            {"item_id": "item-b", "name": "Item B", "quantity": 1, "unit_price": "50.00", "total": "50.00", "confidence": 0.9}
        ],
        "subtotal": "250.00",
        "tax": "25.00",
        "service_charge": "10.00",
        "discount": "20.00",
        "printed_total": "265.00"
    }
    response = client.post("/api/bills/validate", json=raw_data)
    assert response.status_code == 200
    data = response.json()
    # 250 + 25 + 10 - 20 = 265.00
    assert data["calculated_total"] == "265.00"
    assert data["total_mismatch"] is False
    assert data["items"][0]["item_id"] == "item-a"
    assert data["items"][1]["item_id"] == "item-b"


if __name__ == "__main__":
    print("Running tests...")
    test_health()
    print("[PASS] Health check passed")
    test_penny_reconciliation_exact_cents()
    print("[PASS] Penny reconciliation passed")
    test_split_calculate_api()
    print("[PASS] Split calculate API passed")
    test_unassigned_item_fails_validation()
    print("[PASS] Unassigned item 422 validation passed")
    test_bill_validate_recalculates_total()
    print("[PASS] Bill validate recalculate passed")
    print("\nALL 5 TESTS PASSED SUCCESSFULLY!")
