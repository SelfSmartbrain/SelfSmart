"""
Token System - Internal currency for agent economy.

Provides a token-based economy for resource allocation, task rewards,
and inter-agent payments within the agent society.
"""

import asyncio
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional, Set
from collections import defaultdict

logger = logging.getLogger(__name__)


class TransactionType(Enum):
    """Types of token transactions."""
    MINT = "mint"                    # New tokens created
    BURN = "burn"                    # Tokens destroyed
    TRANSFER = "transfer"            # Between accounts
    REWARD = "reward"                # Task completion reward
    PENALTY = "penalty"              # Penalty for failure
    STAKE = "stake"                  # Staked for governance
    UNSTAKE = "unstake"              # Unstaked
    FEE = "fee"                      # Transaction fee
    DIVIDEND = "dividend"            # Revenue sharing


class TransactionStatus(Enum):
    """Transaction status."""
    PENDING = "pending"
    CONFIRMED = "confirmed"
    FAILED = "failed"
    REVERTED = "reverted"


@dataclass
class TokenConfig:
    """Configuration for token system."""
    name: str = "AGENT_TOKEN"
    symbol: str = "AGT"
    decimals: int = 18
    initial_supply: Decimal = Decimal("1000000")  # 1M tokens
    max_supply: Optional[Decimal] = Decimal("10000000")  # 10M max
    mint_rate: Decimal = Decimal("0.01")  # 1% per period
    burn_rate: Decimal = Decimal("0.001")  # 0.1% per transaction
    min_balance: Decimal = Decimal("0")
    transfer_fee_bps: int = 10  # 10 basis points = 0.1%
    staking_reward_rate: Decimal = Decimal("0.05")  # 5% APY
    inflation_enabled: bool = True


@dataclass
class Account:
    """Token account for an agent."""
    agent_id: str
    balance: Decimal = Decimal("0")
    staked_balance: Decimal = Decimal("0")
    pending_rewards: Decimal = Decimal("0")
    nonce: int = 0
    created_at: float = field(default_factory=lambda: datetime.now().timestamp())
    updated_at: float = field(default_factory=lambda: datetime.now().timestamp())
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def total_balance(self) -> Decimal:
        return self.balance + self.staked_balance
    
    @property
    def available_balance(self) -> Decimal:
        return self.balance


@dataclass
class Transaction:
    """Token transaction record."""
    tx_id: str
    tx_type: TransactionType
    from_agent: Optional[str]
    to_agent: Optional[str]
    amount: Decimal
    fee: Decimal = Decimal("0")
    status: TransactionStatus = TransactionStatus.PENDING
    timestamp: float = field(default_factory=lambda: datetime.now().timestamp())
    block_number: Optional[int] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        if self.tx_id is None:
            self.tx_id = f"tx_{uuid.uuid4().hex[:12]}"


class TokenSystem:
    """
    Internal token system for agent economy.
    
    Features:
    - Account management with balances and staking
    - Transaction processing with fees
    - Minting and burning with supply controls
    - Staking rewards
    - Transaction history and audit trail
    """
    
    def __init__(self, config: Optional[TokenConfig] = None):
        self.config = config or TokenConfig()
        
        # Accounts
        self._accounts: Dict[str, Account] = {}
        
        # Transaction ledger
        self._transactions: List[Transaction] = []
        self._pending_transactions: Dict[str, Transaction] = {}
        
        # Supply tracking
        self._total_supply = Decimal("0")
        self._circulating_supply = Decimal("0")
        self._burned_supply = Decimal("0")
        
        # Block tracking
        self._current_block = 0
        self._blocks: List[Dict[str, Any]] = []
        
        # Statistics
        self._stats = {
            "transactions_processed": 0,
            "total_volume": Decimal("0"),
            "total_fees_collected": Decimal("0"),
            "accounts_created": 0,
            "minting_events": 0,
            "burning_events": 0,
        }
        
        # Initialize genesis
        self._initialize_genesis()
        
        logger.info(f"TokenSystem initialized: {self.config.name} ({self.config.symbol})")
    
    def _initialize_genesis(self):
        """Create genesis accounts and initial supply."""
        # Treasury account
        treasury = Account(
            agent_id="treasury",
            balance=self.config.initial_supply,
            metadata={"type": "treasury", "description": "Initial token supply"},
        )
        self._accounts["treasury"] = treasury
        
        self._total_supply = self.config.initial_supply
        self._circulating_supply = self.config.initial_supply
        self._stats["accounts_created"] = 1
        
        # Record genesis mint
        genesis_tx = Transaction(
            tx_id="genesis",
            tx_type=TransactionType.MINT,
            from_agent=None,
            to_agent="treasury",
            amount=self.config.initial_supply,
            status=TransactionStatus.CONFIRMED,
            block_number=0,
            metadata={"genesis": True},
        )
        self._transactions.append(genesis_tx)
    
    def get_account(self, agent_id: str) -> Optional[Account]:
        """Get account for agent."""
        return self._accounts.get(agent_id)
    
    def create_account(self, agent_id: str, initial_balance: Decimal = Decimal("0")) -> Account:
        """Create new account for agent."""
        if agent_id in self._accounts:
            return self._accounts[agent_id]
        
        account = Account(
            agent_id=agent_id,
            balance=initial_balance,
            metadata={"created_by": "token_system"},
        )
        self._accounts[agent_id] = account
        self._stats["accounts_created"] += 1
        
        logger.debug(f"Created account for {agent_id} with balance {initial_balance}")
        return account
    
    def get_balance(self, agent_id: str) -> Decimal:
        """Get available balance for agent."""
        account = self._accounts.get(agent_id)
        return account.available_balance if account else Decimal("0")
    
    def get_total_balance(self, agent_id: str) -> Decimal:
        """Get total balance (available + staked) for agent."""
        account = self._accounts.get(agent_id)
        return account.total_balance if account else Decimal("0")
    
    async def transfer(
        self,
        from_agent: str,
        to_agent: str,
        amount: Decimal,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Transaction:
        """Transfer tokens between accounts."""
        # Validate
        if amount <= 0:
            raise ValueError("Amount must be positive")
        
        if from_agent == to_agent:
            raise ValueError("Cannot transfer to self")
        
        # Get/create accounts
        from_account = self.get_account(from_agent)
        if not from_account:
            raise ValueError(f"Account not found: {from_agent}")
        
        to_account = self.get_account(to_agent)
        if not to_account:
            to_account = self.create_account(to_agent)
        
        # Calculate fee
        fee = amount * Decimal(self.config.transfer_fee_bps) / Decimal("10000")
        total_cost = amount + fee
        
        # Check balance
        if from_account.available_balance < total_cost:
            raise ValueError(f"Insufficient balance: {from_account.available_balance} < {total_cost}")
        
        # Create transaction
        tx = Transaction(
            tx_id=f"tx_{uuid.uuid4().hex[:12]}",
            tx_type=TransactionType.TRANSFER,
            from_agent=from_agent,
            to_agent=to_agent,
            amount=amount,
            fee=fee,
            status=TransactionStatus.PENDING,
            metadata=metadata or {},
        )
        
        # Execute transfer
        from_account.balance -= total_cost
        to_account.balance += amount
        
        # Burn fee
        self._burned_supply += fee
        self._circulating_supply -= fee
        
        # Update timestamps
        from_account.updated_at = datetime.now().timestamp()
        to_account.updated_at = datetime.now().timestamp()
        from_account.nonce += 1
        
        # Confirm transaction
        tx.status = TransactionStatus.CONFIRMED
        tx.block_number = self._current_block
        
        self._transactions.append(tx)
        self._stats["transactions_processed"] += 1
        self._stats["total_volume"] += amount
        self._stats["total_fees_collected"] += fee
        
        logger.debug(f"Transfer: {from_agent} -> {to_agent}: {amount} (fee: {fee})")
        return tx
    
    async def mint(
        self,
        to_agent: str,
        amount: Decimal,
        reason: str = "mint",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Transaction:
        """Mint new tokens."""
        if amount <= 0:
            raise ValueError("Amount must be positive")
        
        # Check supply cap
        if self.config.max_supply and self._total_supply + amount > self.config.max_supply:
            raise ValueError("Would exceed max supply")
        
        to_account = self.get_account(to_agent)
        if not to_account:
            to_account = self.create_account(to_agent)
        
        tx = Transaction(
            tx_id=f"tx_{uuid.uuid4().hex[:12]}",
            tx_type=TransactionType.MINT,
            from_agent=None,
            to_agent=to_agent,
            amount=amount,
            status=TransactionStatus.CONFIRMED,
            block_number=self._current_block,
            metadata={**metadata, "reason": reason} if metadata else {"reason": reason},
        )
        
        to_account.balance += amount
        to_account.updated_at = datetime.now().timestamp()
        
        self._total_supply += amount
        self._circulating_supply += amount
        self._stats["minting_events"] += 1
        
        self._transactions.append(tx)
        return tx
    
    async def burn(
        self,
        from_agent: str,
        amount: Decimal,
        reason: str = "burn",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Transaction:
        """Burn tokens."""
        if amount <= 0:
            raise ValueError("Amount must be positive")
        
        from_account = self.get_account(from_agent)
        if not from_account:
            raise ValueError(f"Account not found: {from_agent}")
        
        if from_account.available_balance < amount:
            raise ValueError("Insufficient balance")
        
        tx = Transaction(
            tx_id=f"tx_{uuid.uuid4().hex[:12]}",
            tx_type=TransactionType.BURN,
            from_agent=from_agent,
            to_agent=None,
            amount=amount,
            status=TransactionStatus.CONFIRMED,
            block_number=self._current_block,
            metadata={**metadata, "reason": reason} if metadata else {"reason": reason},
        )
        
        from_account.balance -= amount
        from_account.updated_at = datetime.now().timestamp()
        from_account.nonce += 1
        
        self._total_supply -= amount
        self._circulating_supply -= amount
        self._burned_supply += amount
        self._stats["burning_events"] += 1
        
        self._transactions.append(tx)
        return tx
    
    async def reward(
        self,
        to_agent: str,
        amount: Decimal,
        reason: str = "task_reward",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Transaction:
        """Reward agent with tokens (mint + transfer from treasury)."""
        # Mint to treasury then transfer (or direct mint if configured)
        return await self.mint(to_agent, amount, reason, metadata)
    
    async def penalize(
        self,
        from_agent: str,
        amount: Decimal,
        reason: str = "penalty",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Transaction:
        """Penalize agent by burning tokens."""
        return await self.burn(from_agent, amount, reason, metadata)
    
    async def stake(
        self,
        agent_id: str,
        amount: Decimal,
    ) -> Transaction:
        """Stake tokens for governance."""
        account = self.get_account(agent_id)
        if not account:
            raise ValueError(f"Account not found: {agent_id}")
        
        if account.available_balance < amount:
            raise ValueError("Insufficient balance for staking")
        
        account.balance -= amount
        account.staked_balance += amount
        account.updated_at = datetime.now().timestamp()
        
        tx = Transaction(
            tx_id=f"tx_{uuid.uuid4().hex[:12]}",
            tx_type=TransactionType.STAKE,
            from_agent=agent_id,
            to_agent=agent_id,
            amount=amount,
            status=TransactionStatus.CONFIRMED,
            block_number=self._current_block,
        )
        
        self._transactions.append(tx)
        return tx
    
    async def unstake(
        self,
        agent_id: str,
        amount: Decimal,
    ) -> Transaction:
        """Unstake tokens."""
        account = self.get_account(agent_id)
        if not account:
            raise ValueError(f"Account not found: {agent_id}")
        
        if account.staked_balance < amount:
            raise ValueError("Insufficient staked balance")
        
        account.staked_balance -= amount
        account.balance += amount
        account.updated_at = datetime.now().timestamp()
        
        tx = Transaction(
            tx_id=f"tx_{uuid.uuid4().hex[:12]}",
            tx_type=TransactionType.UNSTAKE,
            from_agent=agent_id,
            to_agent=agent_id,
            amount=amount,
            status=TransactionStatus.CONFIRMED,
            block_number=self._current_block,
        )
        
        self._transactions.append(tx)
        return tx
    
    async def claim_staking_rewards(self, agent_id: str) -> Decimal:
        """Calculate and claim staking rewards."""
        account = self.get_account(agent_id)
        if not account or account.staked_balance <= 0:
            return Decimal("0")
        
        # Calculate rewards based on time staked and rate
        # Simplified: assume rewards accrue per block
        rewards = account.staked_balance * self.config.staking_reward_rate / Decimal("100")
        
        if rewards > 0:
            await self.mint(agent_id, rewards, "staking_reward")
            account.pending_rewards = Decimal("0")
        
        return rewards
    
    def get_transaction_history(
        self,
        agent_id: Optional[str] = None,
        tx_type: Optional[TransactionType] = None,
        limit: int = 100,
    ) -> List[Transaction]:
        """Get transaction history."""
        txs = self._transactions
        
        if agent_id:
            txs = [tx for tx in txs if tx.from_agent == agent_id or tx.to_agent == agent_id]
        
        if tx_type:
            txs = [tx for tx in txs if tx.tx_type == tx_type]
        
        return txs[-limit:]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get system statistics."""
        return {
            **self._stats,
            "total_supply": self._total_supply,
            "circulating_supply": self._circulating_supply,
            "burned_supply": self._burned_supply,
            "total_accounts": len(self._accounts),
            "current_block": self._current_block,
        }
    
    def get_supply_info(self) -> Dict[str, Decimal]:
        """Get supply information."""
        return {
            "total_supply": self._total_supply,
            "circulating_supply": self._circulating_supply,
            "burned_supply": self._burned_supply,
            "max_supply": self.config.max_supply or Decimal("0"),
            "remaining_mintable": (self.config.max_supply - self._total_supply) if self.config.max_supply else Decimal("Infinity"),
        }