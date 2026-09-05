"""
Query API

Receives natural language questions and returns
GraphRAG-powered compliance answers with explainable evidence.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.services.query_service import QueryService

router = APIRouter(
    prefix="/query",
    tags=["GraphRAG Query"]
)


class QueryRequest(BaseModel):
    case_id: str
    question: str = Field(..., min_length=3)
    top_k: int = Field(default=10, ge=1, le=50)


@router.post("/")
async def ask_question(request: QueryRequest):
    try:
        service = QueryService()
        result  = await service.ask(
            case_id=request.case_id,
            question=request.question,
            top_k=request.top_k,
        )
        return {
            "answer":                   result["answer"],
            "evidence":                 result["evidence"],
            "processing_time_seconds":  result["processing_time_seconds"],
            "graph":                    result["graph"],
        }
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
