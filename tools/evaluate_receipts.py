"""Developer-only receipt extraction evaluator.

This utility is intentionally separate from the user-facing FastAPI flow.
It sends one local image through the same Gemini extraction service and, when
provided, compares the result with manually recorded ground truth.
"""

from __future__ import annotations

import argparse
import json
import mimetypes
import sys
from decimal import Decimal
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from backend.services.gemini_service import extract_bill_from_image  # noqa: E402

_IMAGE_TYPES = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp", ".heic": "image/heic", ".heif": "image/heif"}


def _normal(value: Any) -> Any:
    if isinstance(value, Decimal):
        return str(value.quantize(Decimal("0.01")))
    if isinstance(value, float):
        return f"{value:.4f}"
    return value


def _diff(expected: Any, actual: Any, path: str, differences: list[dict[str, Any]]) -> None:
    if isinstance(expected, dict) and isinstance(actual, dict):
        for key in sorted(set(expected) | set(actual)):
            _diff(expected.get(key), actual.get(key), f"{path}.{key}".strip("."), differences)
        return
    if isinstance(expected, list) and isinstance(actual, list):
        for index in range(max(len(expected), len(actual))):
            _diff(
                expected[index] if index < len(expected) else None,
                actual[index] if index < len(actual) else None,
                f"{path}[{index}]",
                differences,
            )
        return
    if _normal(expected) != _normal(actual):
        differences.append({"field": path, "expected": _normal(expected), "actual": _normal(actual)})


def _find_ground_truth(path: Path, ground_truth_path: Path | None) -> dict[str, Any] | None:
    if ground_truth_path is None or not ground_truth_path.exists():
        return None
    data = json.loads(ground_truth_path.read_text(encoding="utf-8"))
    filename = path.name
    for entry in data.get("bills", []):
        if entry.get("filename") == filename:
            return entry.get("ground_truth") or None
    return None


def evaluate(image_path: Path, ground_truth_path: Path | None) -> dict[str, Any]:
    content_type = _IMAGE_TYPES.get(image_path.suffix.lower()) or mimetypes.guess_type(image_path.name)[0]
    if content_type not in _IMAGE_TYPES.values():
        raise ValueError(f"Unsupported image type: {image_path.suffix}")

    bill = extract_bill_from_image(image_path.read_bytes(), content_type)
    actual = {
        "items": [
            {
                "name": item.name,
                "quantity": item.quantity,
                "unit_price": item.unit_price,
                "total": item.total,
            }
            for item in bill.items
        ],
        "subtotal": bill.subtotal,
        "tax": bill.tax,
        "service_charge": bill.service_charge,
        "discount": bill.discount,
        "printed_total": bill.printed_total,
        "calculated_total": sum(item.total for item in bill.items) + bill.tax + bill.service_charge - bill.discount,
    }
    expected = _find_ground_truth(image_path, ground_truth_path)
    result: dict[str, Any] = {
        "image": str(image_path),
        "ground_truth_found": expected is not None,
        "extracted": actual,
    }
    if expected is not None:
        differences: list[dict[str, Any]] = []
        _diff(expected, actual, "", differences)
        result["differences"] = differences
        result["match"] = not differences
    else:
        result["message"] = "No ground truth exists for this image; extraction was reported without scoring."
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate one receipt through the BillSplit Gemini pipeline.")
    parser.add_argument("image", type=Path, help="Receipt image path")
    parser.add_argument("--ground-truth", type=Path, default=_REPO_ROOT / "test_data" / "ground_truth.json")
    args = parser.parse_args()
    print(json.dumps(evaluate(args.image, args.ground_truth), indent=2, ensure_ascii=False, default=_normal))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
