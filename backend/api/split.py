"""
API routes for split calculation.

Endpoints:
  POST /api/split/calculate — SplitRequest → SplitResult
"""

from fastapi import APIRouter, HTTPException
from pydantic import ValidationError

from backend.models.split import SplitRequest, SplitResult
from backend.services import calculation_service

router = APIRouter(prefix="/api/split", tags=["split"])


@router.post("/calculate", response_model=SplitResult)
async def calculate_split(request: SplitRequest) -> SplitResult:
    """
    Compute proportional split amounts for each person.

    The SplitRequest model_validator runs before this handler and rejects
    any request that has unassigned items (person_ids=[], everyone=False),
    returning a 422 with the specific item names listed.

    Tax, service charge, and discount are distributed proportionally by
    food consumed — not divided equally by headcount.

    Penny reconciliation guarantees:
      sum(person.grand_total for person in result.people_splits)
      == request.bill.calculated_total exactly.
    """
    try:
        result = calculation_service.calculate_split(request)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=exc.errors())
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    return result
