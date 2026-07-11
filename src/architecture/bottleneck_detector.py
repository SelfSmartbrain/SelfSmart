from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Dict, List, Optional
from uuid import UUID, uuid4

import networkx as nx
from pydantic import BaseModel

from src.config.logging import get_logger
from src.architecture.performance_profiler import PerformanceProfiler
from src.architecture.resource_analyzer import ResourceAnalyzer

logger = get_logger(__name__)

class BottleneckIssue(BaseModel):
    model_config = {"from_attributes": True}
    
    node_id: UUID
    issue_type: str
    severity: str
    description: str

class BottleneckReport(BaseModel):
    model_config = {"from_attributes": True}
    
    report_id: UUID
    timestamp: datetime
    issues: List[BottleneckIssue]
    graph_density: float

class BottleneckDetector:
    def __init__(
        self, 
        graph: nx.DiGraph, 
        profiler: PerformanceProfiler, 
        resource_analyzer: ResourceAnalyzer
    ) -> None:
        self.graph = graph
        self.profiler = profiler
        self.resource_analyzer = resource_analyzer

    async def detect_bottlenecks(self) -> BottleneckReport:
        logger.info("Starting bottleneck detection scan across architecture graph")
        issues: List[BottleneckIssue] = []
        
        for node in self.graph.nodes:
            # Check execution time
            avg_time = await self.profiler.get_average_execution_time(node)
            if avg_time > 1000.0:
                issues.append(BottleneckIssue(
                    node_id=node,
                    issue_type="high_execution_time",
                    severity="high",
                    description=f"Average execution time is critically high: {avg_time}ms"
                ))
            
            # Check resource queue
            snapshot = await self.resource_analyzer.get_latest_snapshot(node)
            if snapshot and snapshot.queue_size > 50:
                issues.append(BottleneckIssue(
                    node_id=node,
                    issue_type="queue_buildup",
                    severity="medium",
                    description=f"Queue size is building up: {snapshot.queue_size} items"
                ))
                
        density = nx.density(self.graph) if len(self.graph.nodes) > 1 else 0.0
        
        report = BottleneckReport(
            report_id=uuid4(),
            timestamp=datetime.utcnow(),
            issues=issues,
            graph_density=density
        )
        logger.info(f"Completed bottleneck detection. Found {len(issues)} issues.")
        return report
