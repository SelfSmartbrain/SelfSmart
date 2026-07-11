from __future__ import annotations

from datetime import datetime
from typing import Optional, Dict, Any
from uuid import UUID

from pydantic import BaseModel

class ReportRequest(BaseModel):
    start_date: datetime
    end_date: datetime
    filters: Optional[Dict[str, Any]] = None
    model_config = {"from_attributes": True}

class ReportResponse(BaseModel):
    id: UUID
    report_type: str
    start_date: datetime
    end_date: datetime
    data: Dict[str, Any]
    generated_at: datetime
    model_config = {"from_attributes": True}
