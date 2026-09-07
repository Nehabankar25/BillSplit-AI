"""
gemini_service.py — Gemini Vision + OCR + Structured Extraction

This service does three things in one call:
  1. Image understanding  — reads the photograph, handles angles, lighting, crumples
  2. OCR                  — extracts printed text from the bill
  3. Structured extraction — maps that text to the BillExtract schema

It is NOT just an OCR wrapper. Gemini reasons about what each number means
(quantity vs unit price vs total) and sets a per-item confidence score.

Schema constraint strategy (fixes fragile prompt-only JSON):
  response_mime_type="application/json" + response_schema=BillExtract
  forces Gemini to emit schema-valid JSON rather than relying on prompt
  wording alone. This removes an entire class of "random markdown fence"
  parse failures.

Decimal safety:
  All numeric fields flow through Pydantic's model_validate_json(), which
  constructs Decimal values via str() internally — never via float().
  Do NOT add any Decimal(some_float) calls in this file.
"""

import base64
import os
from pathlib import Path

from dotenv import load_dotenv
from google import genai
from google.genai import types

from backend.models.bill import BillExtract

load_dotenv(Path(__file__).parent.parent / ".env")

_cached_api_key: str = ""
_client: genai.Client | None = None


def _get_client(api_key_override: str | None = None) -> genai.Client:
    global _client, _cached_api_key
    # Re-read from .env dynamically with override=True so changes take effect immediately
    load_dotenv(Path(__file__).parent.parent / ".env", override=True)
    api_key = (api_key_override or os.environ.get("GEMINI_API_KEY", "")).strip()
    if not api_key or api_key == "your_gemini_api_key_here":
        raise RuntimeError(
            "GEMINI_API_KEY is not configured. "
            "Please paste your key in the header 'Set API Key' button or add it to backend/.env."
        )
    if _client is None or api_key != _cached_api_key:
        _client = genai.Client(api_key=api_key)
        _cached_api_key = api_key
    return _client


EXTRACTION_PROMPT = """
You are an expert at reading restaurant, café, and shop receipts.

Your job is to extract every line item and charge from the bill photograph
and return structured data. Follow these rules exactly:

1. Return ONLY the JSON object — no markdown fences, no explanation, no preamble.
2. Extract items exactly as printed. Do NOT recompute or infer totals.
3. For `printed_total`: if the total printed on the bill is clearly readable,
   extract it. If it is absent, smudged, torn, or unreadable, return null.
4. For any OTHER numeric field that is absent or unreadable, return 0.
5. Set `confidence` per item (0.0 to 1.0) based on how clearly you could
   read that specific line — consider lighting, angle, smudging, and handwriting.
   0.95+ = very clear, 0.70-0.89 = somewhat legible, below 0.70 = guessed/unclear.
6. If the bill is in a non-English script, still extract numeric values.
7. `quantity` defaults to 1 if not explicitly printed.
8. `unit_price` = the price for one unit of the item.
9. `total` = quantity × unit_price as printed (use the printed value, not your
   calculation — this lets us detect arithmetic errors on the receipt).
10. `service_charge` and `tax`/`GST`/`VAT` are separate fields — do not merge them.
"""


def extract_bill_from_image(
    image_bytes: bytes,
    content_type: str,
    api_key_override: str | None = None,
) -> BillExtract:
    """
    Send a bill image to Gemini and return a validated BillExtract.

    Args:
        image_bytes: Raw bytes of the uploaded image.
        content_type: MIME type (e.g. "image/jpeg", "image/png").
        api_key_override: Optional user-supplied API key from request header.

    Returns:
        BillExtract validated by Pydantic (all Decimals constructed via str()).

    Raises:
        RuntimeError: If the API key is missing or the response cannot be parsed.
        ValidationError: If Gemini returns JSON that doesn't match BillExtract.
    """
    client = _get_client(api_key_override=api_key_override)
    model_name = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

    # Encode image as inline data part
    image_part = types.Part.from_bytes(data=image_bytes, mime_type=content_type)

    try:
        response = client.models.generate_content(
            model=model_name,
            contents=[image_part, EXTRACTION_PROMPT],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=BillExtract,
                temperature=0.0,  # deterministic extraction
            ),
        )
    except Exception as exc:
        raise RuntimeError(f"Gemini API call failed: {exc}") from exc

    raw_text = response.text
    if not raw_text:
        raise RuntimeError("Gemini returned an empty response.")

    # model_validate_json uses Decimal(str(x)) internally — safe from float noise
    try:
        return BillExtract.model_validate_json(raw_text)
    except Exception as exc:
        raise RuntimeError(
            f"Could not parse Gemini response as BillExtract: {exc}\n"
            f"Raw response: {raw_text[:500]}"
        ) from exc


def extract_bill_from_images(
    images: list[tuple[bytes, str]],
    api_key_override: str | None = None,
) -> BillExtract:
    """Extract one structured bill from one or two receipt photographs."""
    if not images:
        raise RuntimeError("At least one bill image is required.")

    client = _get_client(api_key_override=api_key_override)
    model_name = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    image_parts = [
        types.Part.from_bytes(data=image_bytes, mime_type=content_type)
        for image_bytes, content_type in images
    ]
    prompt = (
        EXTRACTION_PROMPT
        + "\nThese photos are consecutive pages of the same bill. Combine their line items "
        "and charges into one BillExtract. Do not duplicate items visible in both photos."
    )

    try:
        response = client.models.generate_content(
            model=model_name,
            contents=[*image_parts, prompt],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=BillExtract,
                temperature=0.0,
            ),
        )
    except Exception as exc:
        raise RuntimeError(f"Gemini API call failed: {exc}") from exc

    raw_text = response.text
    if not raw_text:
        raise RuntimeError("Gemini returned an empty response.")
    try:
        return BillExtract.model_validate_json(raw_text)
    except Exception as exc:
        raise RuntimeError(
            f"Could not parse Gemini response as BillExtract: {exc}\n"
            f"Raw response: {raw_text[:500]}"
        ) from exc
