"""governance_memory.py

Phase 16I: Strategic Governance Memory

Stores and retrieves governance-related information.
Manages:
- Governance history
- Audit records
- Review records
- Evolution proposals
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field

from src.config.logging import get_logger

logger = get_logger(__name__)


@dataclass
class GovernanceRecord:
    """A record of governance activity."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    record_type: str = ""  # audit, review, evolution, etc.
    decision_id: str = ""
    data: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "record_type": self.record_type,
            "decision_id": self.decision_id,
            "data": self.data,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
        }


class GovernanceMemory:
    """Memory for governance-related information."""
    
    def __init__(self):
        self.records: Dict[str, GovernanceRecord] = {}
        self.records_by_decision: Dict[str, List[str]] = {}  # decision_id -> record_ids
        self.records_by_type: Dict[str, List[str]] = {}  # record_type -> record_ids
        logger.info("GovernanceMemory initialized")
    
    def store_record(
        self,
        record_type: str,
        decision_id: str,
        data: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> GovernanceRecord:
        """Store a governance record."""
        record = GovernanceRecord(
            record_type=record_type,
            decision_id=decision_id,
            data=data,
            metadata=metadata or {},
        )
        
        self.records[record.id] = record
        
        # Index by decision
        if decision_id not in self.records_by_decision:
            self.records_by_decision[decision_id] = []
        self.records_by_decision[decision_id].append(record.id)
        
        # Index by type
        if record_type not in self.records_by_type:
            self.records_by_type[record_type] = []
        self.records_by_type[record_type].append(record.id)
        
        logger.info(f"Stored governance record: {record_type} for decision {decision_id}")
        
        return record
    
    def get_record(self, record_id: str) -> Optional[GovernanceRecord]:
        """Get a record by ID."""
        return self.records.get(record_id)
    
    def get_records_by_decision(self, decision_id: str) -> List[GovernanceRecord]:
        """Get all records for a decision."""
        record_ids = self.records_by_decision.get(decision_id, [])
        return [self.records[rid] for rid in record_ids if rid in self.records]
    
    def get_records_by_type(self, record_type: str) -> List[GovernanceRecord]:
        """Get all records of a specific type."""
        record_ids = self.records_by_type.get(record_type, [])
        return [self.records[rid] for rid in record_ids if rid in self.records]
    
    def get_records_in_range(
        self,
        start_date: datetime,
        end_date: datetime,
    ) -> List[GovernanceRecord]:
        """Get records within a date range."""
        return [
            r for r in self.records.values()
            if start_date <= r.timestamp <= end_date
        ]
    
    def search_records(
        self,
        query: str,
        record_type: Optional[str] = None,
    ) -> List[GovernanceRecord]:
        """Search records by query."""
        records = self.records.values()
        
        if record_type:
            records = [r for r in records if r.record_type == record_type]
        
        # Simple text search
        query_lower = query.lower()
        results = []
        
        for record in records:
            # Search in data
            data_str = str(record.data).lower()
            if query_lower in data_str:
                results.append(record)
                continue
            
            # Search in metadata
            metadata_str = str(record.metadata).lower()
            if query_lower in metadata_str:
                results.append(record)
        
        return results
    
    def get_memory_statistics(self) -> Dict[str, Any]:
        """Get statistics about governance memory."""
        total_records = len(self.records)
        
        by_type = {
            r_type: len(self.get_records_by_type(r_type))
            for r_type in self.records_by_type.keys()
        }
        
        by_decision = {
            decision_id: len(record_ids)
            for decision_id, record_ids in self.records_by_decision.items()
        }
        
        return {
            "total_records": total_records,
            "by_type": by_type,
            "decisions_with_records": len(by_decision),
            "avg_records_per_decision": (
                sum(by_decision.values()) / len(by_decision)
                if by_decision else 0
            ),
        }
