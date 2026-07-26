"""
Market Mechanism - Auction and market-based task allocation.

Implements various auction types and market mechanisms for efficient
resource allocation in the agent society.
"""

import asyncio
import logging
import heapq
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
from collections import defaultdict

logger = logging.getLogger(__name__)


class AuctionType(Enum):
    """Types of auctions."""
    ENGLISH = "english"          # Ascending price
    DUTCH = "dutch"              # Descending price
    SEALED_BID = "sealed_bid"    # First-price sealed bid
    VICKREY = "vickrey"          # Second-price sealed bid
    COMBINATORIAL = "combinatorial"  # Multiple items


class AuctionStatus(Enum):
    """Auction status."""
    PENDING = "pending"
    OPEN = "open"
    CLOSED = "closed"
    SETTLED = "settled"
    CANCELLED = "cancelled"


class BidStatus(Enum):
    """Bid status."""
    ACTIVE = "active"
    WITHDRAWN = "withdrawn"
    OUTBID = "outbid"
    WINNING = "winning"
    LOST = "lost"


@dataclass
class MarketConfig:
    """Configuration for market mechanism."""
    min_bid_increment: Decimal = Decimal("0.01")
    max_bid_duration_hours: int = 24
    min_participants: int = 2
    reserve_price_enabled: bool = True
    anti_sniping_minutes: int = 5
    fee_percentage: Decimal = Decimal("0.025")  # 2.5%
    max_bids_per_agent: int = 10


@dataclass
class Bid:
    """A bid in an auction."""
    bid_id: str
    auction_id: str
    bidder_id: str
    amount: Decimal
    status: BidStatus = BidStatus.ACTIVE
    timestamp: float = field(default_factory=lambda: datetime.now().timestamp())
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # For combinatorial auctions
    bundle: Optional[List[str]] = None
    
    def __lt__(self, other):
        """For heap ordering (higher bids first)."""
        return self.amount > other.amount


@dataclass
class Auction:
    """An auction for resource allocation."""
    auction_id: str
    auction_type: AuctionType
    item_id: str
    item_description: str
    seller_id: str
    
    # Pricing
    starting_price: Decimal
    reserve_price: Optional[Decimal] = None
    current_price: Decimal = Decimal("0")
    
    # Timing
    start_time: float = field(default_factory=lambda: datetime.now().timestamp())
    end_time: Optional[float] = None
    duration_hours: float = 24.0
    
    # Status
    status: AuctionStatus = AuctionStatus.PENDING
    
    # Bids
    bids: List[Bid] = field(default_factory=list)
    winning_bid_id: Optional[str] = None
    winner_id: Optional[str] = None
    
    # Configuration
    config: MarketConfig = field(default_factory=MarketConfig)
    
    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        if self.current_price == Decimal("0"):
            self.current_price = self.starting_price
        if self.end_time is None:
            self.end_time = self.start_time + (self.duration_hours * 3600)
    
    @property
    def is_active(self) -> bool:
        """Check if auction is currently active."""
        now = datetime.now().timestamp()
        return (self.status == AuctionStatus.OPEN and 
                self.start_time <= now < self.end_time)
    
    @property
    def time_remaining(self) -> float:
        """Seconds remaining in auction."""
        if self.end_time is None:
            return 0.0
        return max(0, self.end_time - datetime.now().timestamp())
    
    def get_best_bid(self) -> Optional[Bid]:
        """Get the current best bid."""
        active_bids = [b for b in self.bids if b.status == BidStatus.ACTIVE]
        if not active_bids:
            return None
        return max(active_bids, key=lambda b: b.amount)


@dataclass
class MarketOutcome:
    """Result of a market mechanism execution."""
    auction_id: str
    success: bool
    winner_id: Optional[str] = None
    winning_amount: Optional[Decimal] = None
    fee: Optional[Decimal] = None
    cleared_price: Optional[Decimal] = None
    allocated_items: Dict[str, str] = field(default_factory=dict)  # item_id -> winner_id
    error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "auction_id": self.auction_id,
            "success": self.success,
            "winner_id": self.winner_id,
            "winning_amount": float(self.winning_amount) if self.winning_amount else None,
            "fee": float(self.fee) if self.fee else None,
            "cleared_price": float(self.cleared_price) if self.cleared_price else None,
            "allocated_items": self.allocated_items,
            "error": self.error,
        }


class MarketMechanism:
    """
    Market mechanism for resource allocation via auctions.
    
    Supports multiple auction types:
    - English (ascending) auctions
    - Dutch (descending) auctions  
    - Sealed-bid auctions
    - Vickrey (second-price) auctions
    - Combinatorial auctions for bundles
    """
    
    def __init__(self, config: Optional[MarketConfig] = None):
        self.config = config or MarketConfig()
        self._auctions: Dict[str, Auction] = {}
        self._agent_bids: Dict[str, Set[str]] = defaultdict(set)  # agent_id -> auction_ids
        self._settlement_queue: asyncio.Queue = asyncio.Queue()
        
        # Statistics
        self._stats = {
            "auctions_created": 0,
            "auctions_completed": 0,
            "auctions_cancelled": 0,
            "total_volume": Decimal("0"),
            "total_fees": Decimal("0"),
        }
        
        logger.info("MarketMechanism initialized")
    
    async def create_auction(
        self,
        auction_type: AuctionType,
        item_id: str,
        item_description: str,
        seller_id: str,
        starting_price: Decimal,
        duration_hours: float = 24.0,
        reserve_price: Optional[Decimal] = None,
        config: Optional[MarketConfig] = None,
    ) -> Auction:
        """Create a new auction."""
        auction_id = f"auc_{uuid.uuid4().hex[:12]}"
        
        auction = Auction(
            auction_id=auction_id,
            auction_type=auction_type,
            item_id=item_id,
            item_description=item_description,
            seller_id=seller_id,
            starting_price=starting_price,
            reserve_price=reserve_price,
            duration_hours=duration_hours,
            config=config or self.config,
        )
        
        self._auctions[auction_id] = auction
        self._stats["auctions_created"] += 1
        
        logger.info(f"Created auction {auction_id}: {item_description} ({auction_type.value})")
        return auction
    
    async def start_auction(self, auction_id: str) -> bool:
        """Start an auction."""
        auction = self._auctions.get(auction_id)
        if not auction:
            logger.warning(f"Auction not found: {auction_id}")
            return False
        
        if auction.status != AuctionStatus.PENDING:
            logger.warning(f"Auction not in pending state: {auction.status}")
            return False
        
        auction.status = AuctionStatus.OPEN
        auction.start_time = datetime.now().timestamp()
        auction.end_time = auction.start_time + (auction.duration_hours * 3600)
        
        # For Dutch auctions, start at high price
        if auction.auction_type == AuctionType.DUTCH:
            auction.current_price = auction.reserve_price or (auction.starting_price * Decimal("2"))
        
        logger.info(f"Started auction {auction_id}")
        return True
    
    async def place_bid(
        self,
        auction_id: str,
        bidder_id: str,
        amount: Decimal,
        bundle: Optional[List[str]] = None,
    ) -> Optional[Bid]:
        """Place a bid in an auction."""
        auction = self._auctions.get(auction_id)
        if not auction:
            logger.warning(f"Auction not found: {auction_id}")
            return None
        
        if not auction.is_active:
            logger.warning(f"Auction not active: {auction_id}")
            return None
        
        # Check bidder limits
        if len(self._agent_bids[bidder_id]) >= auction.config.max_bids_per_agent:
            logger.warning(f"Bidder {bidder_id} has reached bid limit")
            return None
        
        # Validate bid amount
        if not self._validate_bid(auction, amount):
            logger.warning(f"Invalid bid amount: {amount}")
            return None
        
        # Create bid
        bid = Bid(
            bid_id=f"bid_{uuid.uuid4().hex[:10]}",
            auction_id=auction_id,
            bidder_id=bidder_id,
            amount=amount,
            bundle=bundle,
        )
        
        # Process based on auction type
        success = await self._process_bid(auction, bid)
        
        if success:
            auction.bids.append(bid)
            self._agent_bids[bidder_id].add(auction.auction_id)
            
            # Check anti-sniping
            await self._check_anti_sniping(auction)
        
        return bid if success else None
    
    def _validate_bid(self, auction: Auction, amount: Decimal) -> bool:
        """Validate bid amount based on auction type."""
        if amount <= Decimal("0"):
            return False
        
        if amount < auction.starting_price and auction.auction_type != AuctionType.DUTCH:
            return False
        
        if auction.reserve_price and amount < auction.reserve_price:
            return False
        
        # Check increment
        if auction.current_price > Decimal("0"):
            min_amount = auction.current_price + auction.config.min_bid_increment
            if amount < min_amount:
                return False
        
        return True
    
    async def _process_bid(self, auction: Auction, bid: Bid) -> bool:
        """Process bid based on auction type."""
        if auction.auction_type == AuctionType.ENGLISH:
            # Ascending price - highest bid wins
            best_bid = auction.get_best_bid()
            if best_bid and bid.amount <= best_bid.amount:
                bid.status = BidStatus.OUTBID
                return False
            
            # Update previous best bid
            if best_bid:
                best_bid.status = BidStatus.OUTBID
            
            auction.current_price = bid.amount
            bid.status = BidStatus.WINNING
            auction.winning_bid_id = bid.bid_id
            auction.winner_id = bid.bidder_id
            return True
            
        elif auction.auction_type == AuctionType.DUTCH:
            # Descending price - first bid at or above current price wins
            if bid.amount >= auction.current_price:
                bid.status = BidStatus.WINNING
                auction.winning_bid_id = bid.bid_id
                auction.winner_id = bid.bidder_id
                auction.status = AuctionStatus.CLOSED
                return True
            else:
                bid.status = BidStatus.LOST
                return False
                
        elif auction.auction_type == AuctionType.SEALED_BID:
            # Sealed bid - collect all, evaluate at end
            bid.status = BidStatus.ACTIVE
            return True
            
        elif auction.auction_type == AuctionType.VICKREY:
            # Second-price sealed bid
            bid.status = BidStatus.ACTIVE
            return True
            
        elif auction.auction_type == AuctionType.COMBINATORIAL:
            # Combinatorial - bid on bundles
            bid.status = BidStatus.ACTIVE
            return True
        
        return False
    
    async def _check_anti_sniping(self, auction: Auction):
        """Extend auction if bid placed near end (anti-sniping)."""
        if auction.time_remaining < (auction.config.anti_sniping_minutes * 60):
            extension = auction.config.anti_sniping_minutes * 60
            auction.end_time += extension
            logger.info(f"Extended auction {auction.auction_id} by {auction.config.anti_sniping_minutes} minutes")
    
    async def close_auction(self, auction_id: str) -> MarketOutcome:
        """Close and settle an auction."""
        auction = self._auctions.get(auction_id)
        if not auction:
            return MarketOutcome(auction_id=auction_id, success=False, error="Auction not found")
        
        if auction.status == AuctionStatus.SETTLED:
            return MarketOutcome(auction_id=auction_id, success=False, error="Already settled")
        
        auction.status = AuctionStatus.CLOSED
        
        # Determine winner based on auction type
        if auction.auction_type == AuctionType.ENGLISH:
            outcome = await self._settle_english(auction)
        elif auction.auction_type == AuctionType.DUTCH:
            outcome = await self._settle_dutch(auction)
        elif auction.auction_type == AuctionType.SEALED_BID:
            outcome = await self._settle_sealed_bid(auction)
        elif auction.auction_type == AuctionType.VICKREY:
            outcome = await self._settle_vickrey(auction)
        elif auction.auction_type == AuctionType.COMBINATORIAL:
            outcome = await self._settle_combinatorial(auction)
        else:
            outcome = MarketOutcome(auction_id=auction_id, success=False, error="Unknown auction type")
        
        if outcome.success:
            auction.status = AuctionStatus.SETTLED
            self._stats["auctions_completed"] += 1
            self._stats["total_volume"] += outcome.winning_amount or Decimal("0")
            self._stats["total_fees"] += outcome.fee or Decimal("0")
        else:
            auction.status = AuctionStatus.CANCELLED
            self._stats["auctions_cancelled"] += 1
        
        return outcome
    
    async def _settle_english(self, auction: Auction) -> MarketOutcome:
        """Settle English auction - highest bidder wins at their bid price."""
        best_bid = auction.get_best_bid()
        
        if not best_bid:
            return MarketOutcome(auction_id=auction.auction_id, success=False, error="No bids received")
        
        if auction.reserve_price and best_bid.amount < auction.reserve_price:
            return MarketOutcome(auction_id=auction.auction_id, success=False, error="Reserve price not met")
        
        # First-price: winner pays their bid
        fee = best_bid.amount * auction.config.fee_percentage
        net_amount = best_bid.amount - fee
        
        return MarketOutcome(
            auction_id=auction.auction_id,
            success=True,
            winner_id=best_bid.bidder_id,
            winning_amount=net_amount,
            fee=fee,
            cleared_price=best_bid.amount,
        )
    
    async def _settle_dutch(self, auction: Auction) -> MarketOutcome:
        """Settle Dutch auction - first bidder at or above current price wins."""
        if not auction.winner_id or not auction.winning_bid_id:
            return MarketOutcome(auction_id=auction.auction_id, success=False, error="No winning bid")
        
        winning_bid = next((b for b in auction.bids if b.bid_id == auction.winning_bid_id), None)
        if not winning_bid:
            return MarketOutcome(auction_id=auction.auction_id, success=False, error="Winning bid not found")
        
        fee = winning_bid.amount * auction.config.fee_percentage
        net_amount = winning_bid.amount - fee
        
        return MarketOutcome(
            auction_id=auction.auction_id,
            success=True,
            winner_id=auction.winner_id,
            winning_amount=net_amount,
            fee=fee,
            cleared_price=winning_bid.amount,
        )
    
    async def _settle_sealed_bid(self, auction: Auction) -> MarketOutcome:
        """Settle sealed-bid auction - highest bid wins at their bid price."""
        active_bids = [b for b in auction.bids if b.status == BidStatus.ACTIVE]
        
        if not active_bids:
            return MarketOutcome(auction_id=auction.auction_id, success=False, error="No bids received")
        
        best_bid = max(active_bids, key=lambda b: b.amount)
        
        if auction.reserve_price and best_bid.amount < auction.reserve_price:
            return MarketOutcome(auction_id=auction.auction_id, success=False, error="Reserve price not met")
        
        fee = best_bid.amount * auction.config.fee_percentage
        net_amount = best_bid.amount - fee
        
        return MarketOutcome(
            auction_id=auction.auction_id,
            success=True,
            winner_id=best_bid.bidder_id,
            winning_amount=net_amount,
            fee=fee,
            cleared_price=best_bid.amount,
        )
    
    async def _settle_vickrey(self, auction: Auction) -> MarketOutcome:
        """Settle Vickrey (second-price) auction - highest bidder wins at second-highest price."""
        active_bids = [b for b in auction.bids if b.status == BidStatus.ACTIVE]
        
        if len(active_bids) < 2:
            if len(active_bids) == 1:
                # Only one bidder - they pay reserve or starting price
                best_bid = active_bids[0]
                price = auction.reserve_price or auction.starting_price
            else:
                return MarketOutcome(auction_id=auction.auction_id, success=False, error="Insufficient bids")
        else:
            # Sort by amount descending
            sorted_bids = sorted(active_bids, key=lambda b: b.amount, reverse=True)
            best_bid = sorted_bids[0]
            second_best = sorted_bids[1]
            price = second_best.amount
            
            if auction.reserve_price and price < auction.reserve_price:
                price = auction.reserve_price
        
        fee = price * auction.config.fee_percentage
        net_amount = price - fee
        
        return MarketOutcome(
            auction_id=auction.auction_id,
            success=True,
            winner_id=best_bid.bidder_id,
            winning_amount=net_amount,
            fee=fee,
            cleared_price=price,
        )
    
    async def _settle_combinatorial(self, auction: Auction) -> MarketOutcome:
        """Settle combinatorial auction - allocate bundles to maximize value."""
        # This is a simplified version - full combinatorial optimization is NP-hard
        active_bids = [b for b in auction.bids if b.status == BidStatus.ACTIVE and b.bundle]
        
        if not active_bids:
            return MarketOutcome(auction_id=auction.auction_id, success=False, error="No bundle bids")
        
        # Greedy allocation: sort by value density (amount / bundle size)
        def value_density(bid: Bid) -> Decimal:
            return bid.amount / Decimal(len(bid.bundle))
        
        sorted_bids = sorted(active_bids, key=value_density, reverse=True)
        
        allocated_items = set()
        winners = {}
        total_value = Decimal("0")
        
        for bid in sorted_bids:
            # Check if bundle items are available
            if all(item not in allocated_items for item in bid.bundle):
                for item in bid.bundle:
                    allocated_items.add(item)
                    winners[item] = bid.bidder_id
                total_value += bid.amount
        
        if not winners:
            return MarketOutcome(auction_id=auction.auction_id, success=False, error="No feasible allocation")
        
        fee = total_value * auction.config.fee_percentage
        net_amount = total_value - fee
        
        return MarketOutcome(
            auction_id=auction.auction_id,
            success=True,
            winner_id=list(winners.values())[0] if winners else None,
            winning_amount=net_amount,
            fee=fee,
            cleared_price=total_value,
            allocated_items=winners,
        )
    
    async def cancel_auction(self, auction_id: str) -> bool:
        """Cancel an auction."""
        auction = self._auctions.get(auction_id)
        if not auction:
            return False
        
        if auction.status in (AuctionStatus.SETTLED, AuctionStatus.CANCELLED):
            return False
        
        auction.status = AuctionStatus.CANCELLED
        
        # Refund/return any locked funds
        for bid in auction.bids:
            if bid.status in (BidStatus.WINNING, BidStatus.ACTIVE):
                bid.status = BidStatus.WITHDRAWN
        
        self._stats["auctions_cancelled"] += 1
        logger.info(f"Cancelled auction {auction_id}")
        return True
    
    async def auto_close_expired(self) -> List[MarketOutcome]:
        """Automatically close expired auctions."""
        outcomes = []
        now = datetime.now().timestamp()
        
        for auction in self._auctions.values():
            if auction.is_active and auction.end_time and auction.end_time <= now:
                outcome = await self.close_auction(auction.auction_id)
                outcomes.append(outcome)
        
        return outcomes
    
    def get_auction(self, auction_id: str) -> Optional[Auction]:
        """Get auction by ID."""
        return self._auctions.get(auction_id)
    
    def get_active_auctions(self) -> List[Auction]:
        """Get all active auctions."""
        return [a for a in self._auctions.values() if a.is_active]
    
    def get_agent_auctions(self, agent_id: str) -> List[Auction]:
        """Get auctions an agent has bid on."""
        auction_ids = self._agent_bids.get(agent_id, set())
        return [self._auctions[aid] for aid in auction_ids if aid in self._auctions]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get market statistics."""
        return {
            **self._stats,
            "active_auctions": len(self.get_active_auctions()),
            "total_auctions": len(self._auctions),
            "total_volume": float(self._stats["total_volume"]),
            "total_fees": float(self._stats["total_fees"]),
        }