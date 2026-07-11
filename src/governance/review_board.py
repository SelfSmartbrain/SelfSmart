"""review_board.py

Phase 16E: Executive Review Board

Provides strategic review for major decisions.
Major decisions must pass review before execution.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from enum import Enum
from dataclasses import dataclass, field

from src.config.logging import get_logger

logger = get_logger(__name__)


class ReviewStatus(str, Enum):
    """Status of a review."""
    PENDING = "pending"
    IN_REVIEW = "in_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    CONDITIONAL = "conditional"
    DEFERRED = "deferred"


class ReviewPriority(str, Enum):
    """Priority of a review."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class ReviewComment:
    """A comment in a review."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    reviewer_id: str = ""
    reviewer_name: str = ""
    comment: str = ""
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "reviewer_id": self.reviewer_id,
            "reviewer_name": self.reviewer_name,
            "comment": self.comment,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
        }


@dataclass
class DecisionReview:
    """A review of a decision."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    decision_id: str = ""
    decision_query: str = ""
    priority: ReviewPriority = ReviewPriority.MEDIUM
    status: ReviewStatus = ReviewStatus.PENDING
    reviewer_id: Optional[str] = None
    reviewer_name: Optional[str] = None
    comments: List[ReviewComment] = field(default_factory=list)
    approval_conditions: List[str] = field(default_factory=list)
    rejection_reasons: List[str] = field(default_factory=list)
    risk_assessment: Dict[str, Any] = field(default_factory=dict)
    strategic_alignment: float = 0.0
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    reviewed_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "decision_id": self.decision_id,
            "decision_query": self.decision_query,
            "priority": self.priority.value,
            "status": self.status.value,
            "reviewer_id": self.reviewer_id,
            "reviewer_name": self.reviewer_name,
            "comments": [c.to_dict() for c in self.comments],
            "approval_conditions": self.approval_conditions,
            "rejection_reasons": self.rejection_reasons,
            "risk_assessment": self.risk_assessment,
            "strategic_alignment": self.strategic_alignment,
            "created_at": self.created_at.isoformat(),
            "reviewed_at": self.reviewed_at.isoformat() if self.reviewed_at else None,
            "metadata": self.metadata,
        }


class ReviewBoard:
    """Executive review board for major decisions."""
    
    def __init__(self):
        self.reviews: Dict[str, DecisionReview] = {}
        self.reviews_by_decision: Dict[str, str] = {}  # decision_id -> review_id
        self.reviewers: Dict[str, Dict[str, Any]] = {}  # reviewer_id -> reviewer info
        self.auto_review_threshold = ReviewPriority.HIGH
        logger.info("ReviewBoard initialized")
    
    def add_reviewer(
        self,
        reviewer_id: str,
        name: str,
        expertise: List[str],
        can_approve: bool = True,
    ) -> None:
        """Add a reviewer to the board."""
        self.reviewers[reviewer_id] = {
            "id": reviewer_id,
            "name": name,
            "expertise": expertise,
            "can_approve": can_approve,
        }
        logger.info(f"Added reviewer: {name}")
    
    def submit_for_review(
        self,
        decision_id: str,
        decision_query: str,
        priority: ReviewPriority = ReviewPriority.MEDIUM,
        risk_assessment: Optional[Dict[str, Any]] = None,
    ) -> DecisionReview:
        """Submit a decision for review."""
        review = DecisionReview(
            decision_id=decision_id,
            decision_query=decision_query,
            priority=priority,
            risk_assessment=risk_assessment or {},
        )
        
        self.reviews[review.id] = review
        self.reviews_by_decision[decision_id] = review.id
        
        logger.info(f"Submitted decision {decision_id} for review")
        
        return review
    
    def assign_reviewer(
        self,
        review_id: str,
        reviewer_id: str,
    ) -> bool:
        """Assign a reviewer to a review."""
        review = self.reviews.get(review_id)
        if review is None:
            return False
        
        if reviewer_id not in self.reviewers:
            logger.warning(f"Reviewer {reviewer_id} not found")
            return False
        
        review.reviewer_id = reviewer_id
        review.reviewer_name = self.reviewers[reviewer_id]["name"]
        review.status = ReviewStatus.IN_REVIEW
        
        logger.info(f"Assigned reviewer {reviewer_id} to review {review_id}")
        
        return True
    
    def add_comment(
        self,
        review_id: str,
        reviewer_id: str,
        comment: str,
    ) -> bool:
        """Add a comment to a review."""
        review = self.reviews.get(review_id)
        if review is None:
            return False
        
        if reviewer_id not in self.reviewers:
            return False
        
        review_comment = ReviewComment(
            reviewer_id=reviewer_id,
            reviewer_name=self.reviewers[reviewer_id]["name"],
            comment=comment,
        )
        
        review.comments.append(review_comment)
        
        logger.info(f"Added comment to review {review_id}")
        
        return True
    
    def approve_review(
        self,
        review_id: str,
        conditions: Optional[List[str]] = None,
        strategic_alignment: float = 0.8,
    ) -> bool:
        """Approve a decision review."""
        review = self.reviews.get(review_id)
        if review is None:
            return False
        
        review.status = ReviewStatus.APPROVED if not conditions else ReviewStatus.CONDITIONAL
        review.approval_conditions = conditions or []
        review.strategic_alignment = strategic_alignment
        review.reviewed_at = datetime.now(timezone.utc)
        
        logger.info(f"Approved review {review_id}")
        
        return True
    
    def reject_review(
        self,
        review_id: str,
        reasons: List[str],
    ) -> bool:
        """Reject a decision review."""
        review = self.reviews.get(review_id)
        if review is None:
            return False
        
        review.status = ReviewStatus.REJECTED
        review.rejection_reasons = reasons
        review.reviewed_at = datetime.now(timezone.utc)
        
        logger.info(f"Rejected review {review_id}")
        
        return True
    
    def defer_review(
        self,
        review_id: str,
        reason: str,
    ) -> bool:
        """Defer a decision review."""
        review = self.reviews.get(review_id)
        if review is None:
            return False
        
        review.status = ReviewStatus.DEFERRED
        review.rejection_reasons = [reason]
        review.reviewed_at = datetime.now(timezone.utc)
        
        logger.info(f"Deferred review {review_id}")
        
        return True
    
    def auto_review(
        self,
        decision_data: Dict[str, Any],
        governance_result: Optional[Dict[str, Any]] = None,
    ) -> DecisionReview:
        """Perform automatic review based on priority and governance."""
        decision_id = decision_data.get("id", "")
        decision_query = decision_data.get("query", "")
        
        # Determine priority based on governance result
        priority = ReviewPriority.MEDIUM
        if governance_result:
            compliance_score = governance_result.get("compliance_score", 0.0)
            if compliance_score < 0.6:
                priority = ReviewPriority.HIGH
            elif compliance_score < 0.8:
                priority = ReviewPriority.MEDIUM
            else:
                priority = ReviewPriority.LOW
        
        # Submit for review
        review = self.submit_for_review(
            decision_id=decision_id,
            decision_query=decision_query,
            priority=priority,
            risk_assessment=decision_data.get("metadata", {}).get("risk_assessment", {}),
        )
        
        # Auto-approve if below threshold
        if priority.value <= self.auto_review_threshold.value:
            self.approve_review(
                review.id,
                conditions=[],
                strategic_alignment=0.8,
            )
        else:
            # Assign to system reviewer
            self.assign_reviewer(review.id, "system")
        
        return review
    
    def get_review(self, review_id: str) -> Optional[DecisionReview]:
        """Get a review by ID."""
        return self.reviews.get(review_id)
    
    def get_review_by_decision(self, decision_id: str) -> Optional[DecisionReview]:
        """Get a review by decision ID."""
        review_id = self.reviews_by_decision.get(decision_id)
        if review_id:
            return self.reviews.get(review_id)
        return None
    
    def list_reviews(self, status: Optional[ReviewStatus] = None) -> List[DecisionReview]:
        """List all reviews, optionally filtered by status."""
        if status:
            return [r for r in self.reviews.values() if r.status == status]
        return list(self.reviews.values())
    
    def get_pending_reviews(self) -> List[DecisionReview]:
        """Get all pending reviews."""
        return self.list_reviews(ReviewStatus.PENDING)
    
    def get_review_statistics(self) -> Dict[str, Any]:
        """Get statistics about reviews."""
        total_reviews = len(self.reviews)
        
        by_status = {
            status.value: len(self.list_reviews(status))
            for status in ReviewStatus
        }
        
        by_priority = {
            priority.value: len([r for r in self.reviews.values() if r.priority == priority])
            for priority in ReviewPriority
        }
        
        approved = len(self.list_reviews(ReviewStatus.APPROVED))
        rejected = len(self.list_reviews(ReviewStatus.REJECTED))
        
        return {
            "total_reviews": total_reviews,
            "by_status": by_status,
            "by_priority": by_priority,
            "approval_rate": approved / total_reviews if total_reviews > 0 else 0.0,
            "rejection_rate": rejected / total_reviews if total_reviews > 0 else 0.0,
        }
