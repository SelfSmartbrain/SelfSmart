"""policy_memory.py

Phase 16I: Policy Memory

Stores and retrieves policy-related information.
Manages:
- Policy versions
- Policy compliance history
- Policy effectiveness data
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field

from src.config.logging import get_logger

logger = get_logger(__name__)


@dataclass
class PolicyVersion:
    """A version of a policy."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    policy_id: str = ""
    version: int = 1
    policy_data: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    created_by: str = ""
    change_description: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "policy_id": self.policy_id,
            "version": self.version,
            "policy_data": self.policy_data,
            "created_at": self.created_at.isoformat(),
            "created_by": self.created_by,
            "change_description": self.change_description,
            "metadata": self.metadata,
        }


@dataclass
class PolicyEffectivenessRecord:
    """A record of policy effectiveness."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    policy_id: str = ""
    period_start: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    period_end: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    compliance_rate: float = 0.0
    violation_count: int = 0
    total_checks: int = 0
    effectiveness_score: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "policy_id": self.policy_id,
            "period_start": self.period_start.isoformat(),
            "period_end": self.period_end.isoformat(),
            "compliance_rate": self.compliance_rate,
            "violation_count": self.violation_count,
            "total_checks": self.total_checks,
            "effectiveness_score": self.effectiveness_score,
            "metadata": self.metadata,
        }


class PolicyMemory:
    """Memory for policy-related information."""
    
    def __init__(self):
        self.versions: Dict[str, PolicyVersion] = {}
        self.versions_by_policy: Dict[str, List[str]] = {}  # policy_id -> version_ids
        self.effectiveness_records: Dict[str, PolicyEffectivenessRecord] = {}
        self.effectiveness_by_policy: Dict[str, List[str]] = {}  # policy_id -> record_ids
        logger.info("PolicyMemory initialized")
    
    def store_version(
        self,
        policy_id: str,
        version: int,
        policy_data: Dict[str, Any],
        created_by: str = "",
        change_description: str = "",
    ) -> PolicyVersion:
        """Store a policy version."""
        policy_version = PolicyVersion(
            policy_id=policy_id,
            version=version,
            policy_data=policy_data,
            created_by=created_by,
            change_description=change_description,
        )
        
        self.versions[policy_version.id] = policy_version
        
        if policy_id not in self.versions_by_policy:
            self.versions_by_policy[policy_id] = []
        self.versions_by_policy[policy_id].append(policy_version.id)
        
        logger.info(f"Stored policy version {version} for policy {policy_id}")
        
        return policy_version
    
    def get_version(self, version_id: str) -> Optional[PolicyVersion]:
        """Get a version by ID."""
        return self.versions.get(version_id)
    
    def get_policy_versions(self, policy_id: str) -> List[PolicyVersion]:
        """Get all versions of a policy."""
        version_ids = self.versions_by_policy.get(policy_id, [])
        versions = [self.versions[vid] for vid in version_ids if vid in self.versions]
        versions.sort(key=lambda v: v.version)
        return versions
    
    def get_latest_version(self, policy_id: str) -> Optional[PolicyVersion]:
        """Get the latest version of a policy."""
        versions = self.get_policy_versions(policy_id)
        return versions[-1] if versions else None
    
    def store_effectiveness(
        self,
        policy_id: str,
        period_start: datetime,
        period_end: datetime,
        compliance_rate: float,
        violation_count: int,
        total_checks: int,
        effectiveness_score: float,
    ) -> PolicyEffectivenessRecord:
        """Store a policy effectiveness record."""
        record = PolicyEffectivenessRecord(
            policy_id=policy_id,
            period_start=period_start,
            period_end=period_end,
            compliance_rate=compliance_rate,
            violation_count=violation_count,
            total_checks=total_checks,
            effectiveness_score=effectiveness_score,
        )
        
        self.effectiveness_records[record.id] = record
        
        if policy_id not in self.effectiveness_by_policy:
            self.effectiveness_by_policy[policy_id] = []
        self.effectiveness_by_policy[policy_id].append(record.id)
        
        logger.info(f"Stored effectiveness record for policy {policy_id}")
        
        return record
    
    def get_effectiveness_records(self, policy_id: str) -> List[PolicyEffectivenessRecord]:
        """Get all effectiveness records for a policy."""
        record_ids = self.effectiveness_by_policy.get(policy_id, [])
        return [self.effectiveness_records[rid] for rid in record_ids if rid in self.effectiveness_records]
    
    def get_effectiveness_trend(self, policy_id: str) -> Dict[str, Any]:
        """Get the effectiveness trend for a policy."""
        records = self.get_effectiveness_records(policy_id)
        
        if len(records) < 2:
            return {"error": "Not enough records to determine trend"}
        
        records.sort(key=lambda r: r.period_start)
        
        scores = [r.effectiveness_score for r in records]
        
        first_score = scores[0]
        last_score = scores[-1]
        
        if last_score > first_score:
            trend = "improving"
        elif last_score < first_score:
            trend = "declining"
        else:
            trend = "stable"
        
        return {
            "policy_id": policy_id,
            "trend": trend,
            "first_score": first_score,
            "last_score": last_score,
            "change": last_score - first_score,
            "record_count": len(records),
        }
    
    def get_policy_statistics(self, policy_id: str) -> Dict[str, Any]:
        """Get statistics for a specific policy."""
        versions = self.get_policy_versions(policy_id)
        effectiveness_records = self.get_effectiveness_records(policy_id)
        
        if effectiveness_records:
            avg_effectiveness = sum(r.effectiveness_score for r in effectiveness_records) / len(effectiveness_records)
            avg_compliance = sum(r.compliance_rate for r in effectiveness_records) / len(effectiveness_records)
        else:
            avg_effectiveness = 0.0
            avg_compliance = 0.0
        
        return {
            "policy_id": policy_id,
            "total_versions": len(versions),
            "latest_version": versions[-1].version if versions else 0,
            "total_effectiveness_records": len(effectiveness_records),
            "average_effectiveness": avg_effectiveness,
            "average_compliance": avg_compliance,
        }
    
    def get_memory_statistics(self) -> Dict[str, Any]:
        """Get statistics about policy memory."""
        total_versions = len(self.versions)
        total_effectiveness_records = len(self.effectiveness_records)
        
        policies_with_versions = len(self.versions_by_policy)
        policies_with_effectiveness = len(self.effectiveness_by_policy)
        
        return {
            "total_versions": total_versions,
            "total_effectiveness_records": total_effectiveness_records,
            "policies_with_versions": policies_with_versions,
            "policies_with_effectiveness": policies_with_effectiveness,
        }
