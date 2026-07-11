"""
Knowledge Marketplace - Phase 14F

The Knowledge Marketplace allows agents to publish and exchange:
- Concepts
- Theories
- Strategies
- Mental Models

This extends the society runtime to support knowledge sharing.
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict

logger = logging.getLogger(__name__)


class KnowledgeItemType(str, Enum):
    """Types of knowledge items that can be published."""
    CONCEPT = "concept"
    THEORY = "theory"
    STRATEGY = "strategy"
    MENTAL_MODEL = "mental_model"
    INSIGHT = "insight"


class KnowledgeStatus(str, Enum):
    """Status of a knowledge item."""
    DRAFT = "draft"
    PUBLISHED = "published"
    VALIDATED = "validated"
    DEPRECATED = "deprecated"


@dataclass
class KnowledgeItem:
    """A knowledge item in the marketplace."""
    item_id: str
    item_type: KnowledgeItemType
    title: str
    description: str
    content: Dict[str, Any]
    author_id: str
    status: KnowledgeStatus = KnowledgeStatus.DRAFT
    confidence: float = 0.5
    tags: List[str] = field(default_factory=list)
    citations: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=lambda: datetime.now(timezone.utc).timestamp())
    updated_at: float = field(default_factory=lambda: datetime.now(timezone.utc).timestamp())
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class KnowledgeRating:
    """A rating for a knowledge item."""
    rating_id: str
    item_id: str
    rater_id: str
    rating: float  # 0.0 to 1.0
    usefulness: float
    accuracy: float
    timestamp: float = field(default_factory=lambda: datetime.now(timezone.utc).timestamp())
    comments: str = ""


@dataclass
class KnowledgeSubscription:
    """A subscription to knowledge updates."""
    subscription_id: str
    subscriber_id: str
    item_type: Optional[KnowledgeItemType] = None
    tags: List[str] = field(default_factory=list)
    min_confidence: float = 0.0
    created_at: float = field(default_factory=lambda: datetime.now(timezone.utc).timestamp())


class KnowledgeMarketplace:
    """
    Marketplace for knowledge exchange between agents.
    
    Provides:
    - Knowledge publishing and discovery
    - Rating and validation system
    - Subscription to knowledge updates
    - Citation tracking
    """
    
    def __init__(self):
        self._items: Dict[str, KnowledgeItem] = {}
        self._ratings: Dict[str, List[KnowledgeRating]] = defaultdict(list)
        self._subscriptions: Dict[str, List[KnowledgeSubscription]] = defaultdict(list)
        self._agent_items: Dict[str, Set[str]] = defaultdict(set)
        self._item_citations: Dict[str, Set[str]] = defaultdict(set)
        
        # Statistics
        self._items_published = 0
        self._ratings_given = 0
        self._subscriptions_created = 0
    
    async def initialize(self) -> None:
        """Initialize the knowledge marketplace."""
        logger.info("KnowledgeMarketplace initialized")
    
    async def publish_knowledge(
        self,
        item_type: KnowledgeItemType,
        title: str,
        description: str,
        content: Dict[str, Any],
        author_id: str,
        tags: Optional[List[str]] = None,
        confidence: float = 0.5,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> KnowledgeItem:
        """
        Publish a knowledge item.
        
        Args:
            item_type: Type of knowledge item
            title: Item title
            description: Item description
            content: Item content
            author_id: Author agent ID
            tags: Optional tags
            confidence: Initial confidence
            metadata: Additional metadata
            
        Returns:
            Published knowledge item
        """
        item_id = f"{item_type.value}_{datetime.now(timezone.utc).timestamp()}"
        
        item = KnowledgeItem(
            item_id=item_id,
            item_type=item_type,
            title=title,
            description=description,
            content=content,
            author_id=author_id,
            status=KnowledgeStatus.PUBLISHED,
            confidence=confidence,
            tags=tags or [],
            metadata=metadata or {},
        )
        
        self._items[item_id] = item
        self._agent_items[author_id].add(item_id)
        self._items_published += 1
        
        logger.info(f"Published knowledge item {item_id}: {title} by {author_id}")
        return item
    
    async def rate_knowledge(
        self,
        item_id: str,
        rater_id: str,
        rating: float,
        usefulness: float,
        accuracy: float,
        comments: str = "",
    ) -> bool:
        """
        Rate a knowledge item.
        
        Args:
            item_id: Knowledge item ID
            rater_id: Rater agent ID
            rating: Overall rating (0.0 to 1.0)
            usefulness: Usefulness rating (0.0 to 1.0)
            accuracy: Accuracy rating (0.0 to 1.0)
            comments: Optional comments
            
        Returns:
            True if rating accepted
        """
        if item_id not in self._items:
            logger.warning(f"Knowledge item {item_id} not found")
            return False
        
        rating_obj = KnowledgeRating(
            rating_id=f"rating_{datetime.now(timezone.utc).timestamp()}",
            item_id=item_id,
            rater_id=rater_id,
            rating=rating,
            usefulness=usefulness,
            accuracy=accuracy,
            comments=comments,
        )
        
        self._ratings[item_id].append(rating_obj)
        self._ratings_given += 1
        
        # Update item confidence based on ratings
        self._update_item_confidence(item_id)
        
        logger.debug(f"Agent {rater_id} rated item {item_id}: {rating:.2f}")
        return True
    
    def _update_item_confidence(self, item_id: str) -> None:
        """Update item confidence based on ratings."""
        if item_id not in self._ratings:
            return
        
        ratings = self._ratings[item_id]
        if not ratings:
            return
        
        # Average the ratings
        avg_rating = sum(r.rating for r in ratings) / len(ratings)
        avg_accuracy = sum(r.accuracy for r in ratings) / len(ratings)
        
        # Update item confidence (blend of initial and ratings)
        item = self._items[item_id]
        item.confidence = (item.confidence * 0.3) + (avg_rating * 0.4) + (avg_accuracy * 0.3)
        item.updated_at = datetime.now(timezone.utc).timestamp()
        
        # Update status based on confidence
        if item.confidence >= 0.8:
            item.status = KnowledgeStatus.VALIDATED
        elif item.confidence < 0.3:
            item.status = KnowledgeStatus.DEPRECATED
    
    async def cite_knowledge(self, item_id: str, citing_item_id: str) -> bool:
        """
        Record a citation between knowledge items.
        
        Args:
            item_id: Cited item ID
            citing_item_id: Citing item ID
            
        Returns:
            True if citation recorded
        """
        if item_id not in self._items or citing_item_id not in self._items:
            return False
        
        self._item_citations[item_id].add(citing_item_id)
        
        # Add to citations list
        if citing_item_id not in self._items[item_id].citations:
            self._items[item_id].citations.append(citing_item_id)
        
        logger.debug(f"Citation recorded: {citing_item_id} cites {item_id}")
        return True
    
    async def subscribe_to_knowledge(
        self,
        subscriber_id: str,
        item_type: Optional[KnowledgeItemType] = None,
        tags: Optional[List[str]] = None,
        min_confidence: float = 0.0,
    ) -> KnowledgeSubscription:
        """
        Subscribe to knowledge updates.
        
        Args:
            subscriber_id: Subscriber agent ID
            item_type: Optional item type filter
            tags: Optional tag filters
            min_confidence: Minimum confidence threshold
            
        Returns:
            Subscription object
        """
        subscription_id = f"sub_{datetime.now(timezone.utc).timestamp()}"
        
        subscription = KnowledgeSubscription(
            subscription_id=subscription_id,
            subscriber_id=subscriber_id,
            item_type=item_type,
            tags=tags or [],
            min_confidence=min_confidence,
        )
        
        self._subscriptions[subscriber_id].append(subscription)
        self._subscriptions_created += 1
        
        logger.info(f"Agent {subscriber_id} subscribed to knowledge updates")
        return subscription
    
    def get_knowledge_item(self, item_id: str) -> Optional[KnowledgeItem]:
        """Get a knowledge item by ID."""
        return self._items.get(item_id)
    
    def find_knowledge(
        self,
        item_type: Optional[KnowledgeItemType] = None,
        tags: Optional[List[str]] = None,
        author_id: Optional[str] = None,
        min_confidence: float = 0.0,
        status: Optional[KnowledgeStatus] = None,
        limit: int = 50,
    ) -> List[KnowledgeItem]:
        """
        Find knowledge items matching criteria.
        
        Args:
            item_type: Filter by item type
            tags: Filter by tags
            author_id: Filter by author
            min_confidence: Minimum confidence
            status: Filter by status
            limit: Maximum results
            
        Returns:
            List of matching knowledge items
        """
        items = list(self._items.values())
        
        if item_type:
            items = [i for i in items if i.item_type == item_type]
        
        if tags:
            items = [i for i in items if any(tag in i.tags for tag in tags)]
        
        if author_id:
            items = [i for i in items if i.author_id == author_id]
        
        if min_confidence > 0:
            items = [i for i in items if i.confidence >= min_confidence]
        
        if status:
            items = [i for i in items if i.status == status]
        
        # Sort by confidence and recency
        items.sort(key=lambda i: (i.confidence, i.updated_at), reverse=True)
        
        return items[:limit]
    
    def get_agent_knowledge(
        self,
        agent_id: str,
        item_type: Optional[KnowledgeItemType] = None,
    ) -> List[KnowledgeItem]:
        """
        Get knowledge published by an agent.
        
        Args:
            agent_id: Agent identifier
            item_type: Optional item type filter
            
        Returns:
            List of knowledge items
        """
        item_ids = self._agent_items.get(agent_id, set())
        
        items = [self._items[iid] for iid in item_ids if iid in self._items]
        
        if item_type:
            items = [i for i in items if i.item_type == item_type]
        
        return items
    
    def get_item_ratings(self, item_id: str) -> List[KnowledgeRating]:
        """Get ratings for a knowledge item."""
        return self._ratings.get(item_id, [])
    
    def get_item_citations(self, item_id: str) -> List[str]:
        """Get items that cite this item."""
        return list(self._item_citations.get(item_id, set()))
    
    def get_subscriber_updates(
        self,
        subscriber_id: str,
        since: Optional[float] = None,
    ) -> List[KnowledgeItem]:
        """
        Get knowledge updates for a subscriber.
        
        Args:
            subscriber_id: Subscriber agent ID
            since: Optional timestamp to filter updates since
            
        Returns:
            List of new or updated knowledge items
        """
        subscriptions = self._subscriptions.get(subscriber_id, [])
        
        if not subscriptions:
            return []
        
        updates = []
        
        for subscription in subscriptions:
            # Find items matching subscription criteria
            matching = self.find_knowledge(
                item_type=subscription.item_type,
                tags=subscription.tags if subscription.tags else None,
                min_confidence=subscription.min_confidence,
                limit=100,
            )
            
            # Filter by timestamp if specified
            if since:
                matching = [i for i in matching if i.updated_at >= since]
            
            updates.extend(matching)
        
        # Deduplicate
        seen = set()
        unique_updates = []
        for item in updates:
            if item.item_id not in seen:
                seen.add(item.item_id)
                unique_updates.append(item)
        
        return unique_updates
    
    def get_top_knowledge(
        self,
        item_type: Optional[KnowledgeItemType] = None,
        n: int = 10,
    ) -> List[KnowledgeItem]:
        """
        Get top knowledge items by confidence.
        
        Args:
            item_type: Optional item type filter
            n: Number of items to return
            
        Returns:
            List of top knowledge items
        """
        items = self.find_knowledge(item_type=item_type, min_confidence=0.5, limit=100)
        return sorted(items, key=lambda i: i.confidence, reverse=True)[:n]
    
    def get_trending_knowledge(self, n: int = 10) -> List[KnowledgeItem]:
        """
        Get trending knowledge items (recently updated with high ratings).
        
        Args:
            n: Number of items to return
            
        Returns:
            List of trending knowledge items
        """
        # Get recently updated items
        recent = [
            i for i in self._items.values()
            if i.updated_at > datetime.now(timezone.utc).timestamp() - 86400  # Last 24 hours
        ]
        
        # Sort by confidence and citation count
        recent.sort(
            key=lambda i: (i.confidence, len(self._item_citations.get(i.item_id, set()))),
            reverse=True,
        )
        
        return recent[:n]
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get marketplace metrics."""
        type_counts = {}
        for item in self._items.values():
            type_counts[item.item_type.value] = type_counts.get(item.item_type.value, 0) + 1
        
        status_counts = {}
        for item in self._items.values():
            status_counts[item.status.value] = status_counts.get(item.status.value, 0) + 1
        
        return {
            "items_published": self._items_published,
            "ratings_given": self._ratings_given,
            "subscriptions_created": self._subscriptions_created,
            "by_type": type_counts,
            "by_status": status_counts,
            "average_confidence": (
                sum(i.confidence for i in self._items.values()) / len(self._items)
                if self._items else 0.0
            ),
            "total_citations": sum(len(citations) for citations in self._item_citations.values()),
        }
