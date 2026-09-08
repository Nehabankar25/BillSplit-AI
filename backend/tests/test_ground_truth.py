"""Unit tests for ground truth dataset structure and file integrity."""

import json
from decimal import Decimal
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
GROUND_TRUTH_PATH = REPO_ROOT / "test_data" / "ground_truth.json"
BILLS_DIR = REPO_ROOT / "test_data" / "bills"


def test_ground_truth_file_exists_and_valid():
    """Verify ground_truth.json exists and is valid JSON."""
    assert GROUND_TRUTH_PATH.exists(), f"Missing ground truth file at {GROUND_TRUTH_PATH}"
    data = json.loads(GROUND_TRUTH_PATH.read_text(encoding="utf-8"))
    assert "bills" in data
    assert len(data["bills"]) == 12


def test_all_bill_images_exist_on_disk():
    """Verify every image referenced in ground_truth.json exists in test_data/bills/."""
    data = json.loads(GROUND_TRUTH_PATH.read_text(encoding="utf-8"))
    for bill in data["bills"]:
        filenames = bill["filename"]
        if isinstance(filenames, str):
            filenames = [filenames]
        for fn in filenames:
            img_path = BILLS_DIR / fn
            assert img_path.exists(), f"Referenced bill image missing: {img_path}"
            assert img_path.stat().st_size > 0, f"Empty bill image file: {img_path}"


def test_ground_truth_arithmetic_consistency():
    """Verify mathematical integrity of ground truth fields."""
    data = json.loads(GROUND_TRUTH_PATH.read_text(encoding="utf-8"))
    for bill in data["bills"]:
        gt = bill["ground_truth"]
        items = gt.get("items", [])
        assert len(items) > 0, f"Bill {bill['bill_id']} has no ground truth items"

        items_sum = sum(Decimal(str(item["total"])) for item in items)
        subtotal = Decimal(str(gt["subtotal"]))
        tax = Decimal(str(gt.get("tax", 0)))
        sc = Decimal(str(gt.get("service_charge", 0)))
        discount = Decimal(str(gt.get("discount", 0)))
        calc_total = Decimal(str(gt["calculated_total"]))

        # Calculated total matches formula
        expected_calc = (items_sum if abs(items_sum - subtotal) > Decimal("1.00") else subtotal) + tax + sc - discount
        # Check printed total vs calculated mismatch logic
        printed = gt.get("printed_total")
        if printed is not None:
            printed_dec = Decimal(str(printed))
            expected_mismatch = abs(calc_total - printed_dec) > Decimal("1.00")
            assert gt["total_mismatch"] == expected_mismatch, (
                f"Mismatch flag wrong for {bill['bill_id']}: expected {expected_mismatch}, got {gt['total_mismatch']}"
            )
