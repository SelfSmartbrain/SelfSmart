from __future__ import annotations

from datetime import datetime
from typing import List

from pydantic import BaseModel

class ChartDataPoint(BaseModel):
    timestamp: datetime
    value: float
    model_config = {"from_attributes": True}

class DashboardMetrics(BaseModel):
    total_tasks: int
    success_rate: float
    active_agents: int
    system_health: float
    velocity_chart: List[ChartDataPoint]
    model_config = {"from_attributes": True}
