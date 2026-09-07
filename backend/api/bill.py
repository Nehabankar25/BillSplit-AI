"""
API routes for bill extraction and validation.

Endpoints:
  POST /api/bills/analyze   — Upload image → BillExtract via Gemini → Bill
  POST /api/bills/validate  — Re-validate human-edited bill JSON → Bill
"""

import io

from fastapi import APIRouter, File, Header, HTTPException, UploadFile
from pydantic import ValidationError

from backend.models.bill import Bill, BillExtract
from backend.services import extraction_service, gemini_service

router = APIRouter(prefix="/api/bills", tags=["bills"])

_ALLOWED_CONTENT_TYPES = {
    "image/jpeg",
    "image/jpg",
    "image/png",
    "image/webp",
    "image/heic",
    "image/heif",
}
_MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB


@router.post("/analyze", response_model=Bill)
async def analyze_bill(
    file: UploadFile = File(...),
    x_gemini_key: str | None = Header(default=None),
) -> Bill:
    """
    Accept a bill photograph, extract structured data via Gemini Vision,
    and return a validated Bill with Python-computed totals.

    The image is sent to Gemini with:
      response_mime_type="application/json"
      response_schema=BillExtract

    So Gemini is constrained to the schema rather than relying on prompt
    wording alone — no markdown-fence parsing, no free-text cleanup.
    """
    if file.content_type not in _ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=415,
            detail=(
                f"Unsupported file type: {file.content_type}. "
                f"Accepted: {', '.join(sorted(_ALLOWED_CONTENT_TYPES))}"
            ),
        )

    image_bytes = await file.read()
    if len(image_bytes) > _MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum size is {_MAX_FILE_SIZE_BYTES // (1024*1024)} MB."
        )
    if len(image_bytes) == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    try:
        extract: BillExtract = gemini_service.extract_bill_from_image(
            image_bytes, file.content_type, api_key_override=x_gemini_key
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc))

    return extraction_service.build_bill(extract)


@router.post("/analyze-multiple", response_model=Bill)
async def analyze_multiple_bills(
    files: list[UploadFile] = File(...),
    x_gemini_key: str | None = Header(default=None),
) -> Bill:
    """Combine one or two consecutive bill photos into one extracted bill."""
    if not 1 <= len(files) <= 2:
        raise HTTPException(status_code=400, detail="Upload one or two bill photos.")

    images: list[tuple[bytes, str]] = []
    for file in files:
        if file.content_type not in _ALLOWED_CONTENT_TYPES:
            raise HTTPException(status_code=415, detail=f"Unsupported file type: {file.content_type}")
        image_bytes = await file.read()
        if len(image_bytes) > _MAX_FILE_SIZE_BYTES:
            raise HTTPException(status_code=413, detail="Each file must be 10 MB or smaller.")
        if not image_bytes:
            raise HTTPException(status_code=400, detail="Uploaded file is empty.")
        images.append((image_bytes, file.content_type))

    try:
        extract = gemini_service.extract_bill_from_images(images, api_key_override=x_gemini_key)
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc))

    return extraction_service.build_bill(extract)


@router.post("/validate", response_model=Bill)
async def validate_bill(data: dict) -> Bill:
    """
    Re-validate a human-edited bill and recompute calculated_total.

    The review screen sends back the full bill JSON after the user corrects
    any mis-extracted values. We re-parse, recalculate, and return the
    updated Bill so the frontend always displays Python-computed totals.
    """
    try:
        bill = extraction_service.revalidate_bill(data)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=exc.errors())
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    return bill


@router.get("/demo", response_model=Bill)
async def get_demo_bill() -> Bill:
    """
    Return a realistic sample bill (Biryani, Coke, Paneer Tikka, Naan).
    Allows testing the full review, assignment, and split calculation workflow
    instantly even before configuring a Gemini API key.
    """
    from decimal import Decimal
    from backend.models.bill import BillItemExtract

    items = [
        BillItemExtract(name="Hyderabadi Chicken Biryani", quantity=Decimal("2"), unit_price=Decimal("350.00"), total=Decimal("700.00"), confidence=0.98),
        BillItemExtract(name="Diet Coke (Can)", quantity=Decimal("1"), unit_price=Decimal("60.00"), total=Decimal("60.00"), confidence=0.95),
        BillItemExtract(name="Paneer Tikka Platter", quantity=Decimal("1"), unit_price=Decimal("280.00"), total=Decimal("280.00"), confidence=0.88),
        BillItemExtract(name="Butter Garlic Naan", quantity=Decimal("4"), unit_price=Decimal("40.00"), total=Decimal("160.00"), confidence=0.96),
    ]
    extract = BillExtract(
        items=items,
        subtotal=Decimal("1200.00"),
        tax=Decimal("60.00"),
        service_charge=Decimal("120.00"),
        discount=Decimal("0.00"),
        printed_total=Decimal("1380.00"),
    )
    return extraction_service.build_bill(extract)

