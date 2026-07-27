"""
Safety Hypervisor - Continuous monitoring of self-modification.

Provides real-time safety monitoring for autonomous self-modification:
- Event-based monitoring of system changes
- Policy enforcement for self-modification
- Anomaly detection in behavior patterns
- Emergency stop capabilities
"""

import asyncio
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set
from collections import defaultdict

logger = logging.getLogger(__name__)


class SafetyEventType(Enum):
    """Types of safety events."""

    PATCH_APPLIED = "patch_applied"
    PATCH_REJECTED = "patch_rejected"
    TEST_FAILURE = "test_failure"
    CRITICAL_FILE_MODIFIED = "critical_file_modified"
    FORBIDDEN_FILE_MODIFIED = "forbidden_file_modified"
    BLAST_RADIUS_EXCEEDED = "blast_radius_exceeded"
    ANOMALOUS_BEHAVIOR = "anomalous_behavior"
    RESOURCE_EXHAUSTION = "resource_exhaustion"
    UNAUTHORIZED_ACCESS = "unauthorized_access"
    SELF_MODIFICATION_ATTEMPT = "self_modification_attempt"
    SAFETY_GATE_BYPASS = "safety_gate_bypass"
    EMERGENCY_STOP = "emergency_stop"


class SafetySeverity(Enum):
    """Severity levels for safety events."""

    INFO = "info"
    WARNING = "warning"
    HIGH = "high"
    CRITICAL = "critical"
    EMERGENCY = "emergency"


@dataclass
class SafetyEvent:
    """A safety-related event."""

    event_id: str
    event_type: SafetyEventType
    severity: SafetySeverity
    timestamp: float = field(default_factory=lambda: datetime.now().timestamp())
    source: str = "system"
    agent_id: Optional[str] = None
    description: str = ""
    details: Dict[str, Any] = field(default_factory=dict)
    related_events: List[str] = field(default_factory=list)
    acknowledged: bool = False
    acknowledged_by: Optional[str] = None
    acknowledged_at: Optional[float] = None

    def __post_init__(self):
        if not self.event_id:
            self.event_id = f"evt_{uuid.uuid4().hex[:12]}"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "severity": self.severity.value,
            "timestamp": self.timestamp,
            "source": self.source,
            "agent_id": self.agent_id,
            "description": self.description,
            "details": self.details,
            "related_events": self.related_events,
            "acknowledged": self.acknowledged,
        }


@dataclass
class SafetyPolicy:
    """Safety policy rule."""

    policy_id: str
    name: str
    description: str
    event_types: List[SafetyEventType]
    condition: str  # Python expression evaluated against event
    action: str  # alert, block, emergency_stop, log_only
    parameters: Dict[str, Any] = field(default_factory=dict)
    enabled: bool = True
    priority: int = 0  # Higher = more important

    def evaluate(self, event: SafetyEvent) -> bool:
        """Evaluate policy condition against event."""
        try:
            # Create evaluation context
            context = {
                "event": event,
                "event_type": event.event_type.value,
                "severity": event.severity.value,
                "source": event.source,
                "agent_id": event.agent_id,
                **event.details,
            }
            return eval(self.condition, {"__builtins__": {}}, context)
        except Exception as e:
            logger.error(f"Policy evaluation failed: {e}")
            return False


@dataclass
class MonitoringConfig:
    """Configuration for safety monitoring."""

    # Event processing
    max_events_in_memory: int = 10000
    event_retention_days: int = 30

    # Alerting
    alert_on_critical: bool = True
    alert_on_emergency: bool = True
    alert_webhook: Optional[str] = None

    # Anomaly detection
    enable_anomaly_detection: bool = True
    anomaly_threshold: float = 0.8
    anomaly_window_hours: int = 24

    # Rate limiting
    max_events_per_minute: int = 100
    max_patches_per_hour: int = 10

    # Resource monitoring
    monitor_resources: bool = True
    cpu_threshold: float = 90.0
    memory_threshold: float = 90.0
    disk_threshold: float = 90.0

    # Auto-response
    auto_block_on_critical: bool = True
    auto_emergency_stop_on_emergency: bool = True

    # Integrations
    notify_slack: bool = False
    slack_webhook: Optional[str] = None
    notify_email: bool = False


class SafetyHypervisor:
    """
    Continuous safety monitoring for autonomous self-modification.

    Features:
    - Real-time event monitoring
    - Policy-based enforcement
    - Anomaly detection
    - Emergency stop capability
    - Resource monitoring
    - Alerting and notifications
    """

    def __init__(
        self,
        config: Optional[MonitoringConfig] = None,
        event_handlers: Optional[Dict[str, Callable]] = None,
    ):
        self.config = config or MonitoringConfig()
        self._events: List[SafetyEvent] = []
        self._policies: Dict[str, SafetyPolicy] = {}
        self._event_handlers: Dict[str, Callable] = event_handlers or {}

        # State
        self._running = False
        self._monitoring_task: Optional[asyncio.Task] = None
        self._anomaly_task: Optional[asyncio.Task] = None
        self._resource_task: Optional[asyncio.Task] = None

        # Rate limiting
        self._event_counts: Dict[str, int] = defaultdict(int)  # event_type -> count
        self._rate_limit_window: Dict[str, float] = {}

        # Anomaly detection
        self._behavior_baselines: Dict[str, Dict[str, float]] = defaultdict(dict)
        self._recent_events: List[SafetyEvent] = []

        # Emergency stop
        self._emergency_stopped = False
        self._emergency_stop_reason: Optional[str] = None

        # Initialize default policies
        self._initialize_default_policies()

        logger.info("SafetyHypervisor initialized")

    def _initialize_default_policies(self):
        """Initialize default safety policies."""
        policies = [
            SafetyPolicy(
                policy_id="critical_file_protection",
                name="Critical File Protection",
                description="Block modifications to critical system files",
                event_types=[SafetyEventType.CRITICAL_FILE_MODIFIED],
                condition="event.details.get('file_path', '').startswith(('src/runtime/', 'src/autonomy/', 'src/safety/', 'src/governance/'))",
                action="block",
                priority=100,
            ),
            SafetyPolicy(
                policy_id="forbidden_file_protection",
                name="Forbidden File Protection",
                description="Block modifications to safety system itself",
                event_types=[SafetyEventType.FORBIDDEN_FILE_MODIFIED],
                condition="True",
                action="emergency_stop",
                priority=200,
            ),
            SafetyPolicy(
                policy_id="blast_radius_limit",
                name="Blast Radius Limit",
                description="Limit blast radius of self-modifications",
                event_types=[SafetyEventType.BLAST_RADIUS_EXCEEDED],
                condition="event.details.get('blast_radius', 0) > 0.5",
                action="block",
                priority=90,
            ),
            SafetyPolicy(
                policy_id="test_failure_prevention",
                name="Test Failure Prevention",
                description="Block patches that fail tests",
                event_types=[SafetyEventType.TEST_FAILURE],
                condition="event.details.get('tests_failed', 0) > 0",
                action="block",
                priority=80,
            ),
            SafetyPolicy(
                policy_id="anomalous_behavior_detection",
                name="Anomalous Behavior Detection",
                description="Detect anomalous modification patterns",
                event_types=[SafetyEventType.ANOMALOUS_BEHAVIOR],
                condition="event.details.get('anomaly_score', 0) > 0.8",
                action="alert",
                priority=50,
            ),
            SafetyPolicy(
                policy_id="resource_exhaustion_prevention",
                name="Resource Exhaustion Prevention",
                description="Prevent resource exhaustion from self-modification",
                event_types=[SafetyEventType.RESOURCE_EXHAUSTION],
                condition="event.details.get('cpu_percent', 0) > 90 or event.details.get('memory_percent', 0) > 90",
                action="emergency_stop",
                priority=95,
            ),
        ]

        for policy in policies:
            self._policies[policy.policy_id] = policy

    async def start(self):
        """Start the safety hypervisor."""
        if self._running:
            logger.warning("SafetyHypervisor already running")
            return

        self._running = True
        self._emergency_stopped = False
        self._emergency_stop_reason = None

        # Start monitoring tasks
        self._monitoring_task = asyncio.create_task(self._monitoring_loop())
        self._anomaly_task = asyncio.create_task(self._anomaly_detection_loop())
        self._resource_task = asyncio.create_task(self._resource_monitoring_loop())

        logger.info("SafetyHypervisor started")

    async def stop(self):
        """Stop the safety hypervisor."""
        self._running = False

        # Cancel tasks
        for task in [self._monitoring_task, self._anomaly_task, self._resource_task]:
            if task:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

        logger.info("SafetyHypervisor stopped")

    def emit_event(self, event: SafetyEvent) -> bool:
        """
        Emit a safety event for processing.

        Returns:
            True if event was accepted, False if blocked
        """
        # Check rate limits
        if not self._check_rate_limit(event.event_type):
            logger.warning(f"Rate limit exceeded for {event.event_type.value}")
            return False

        # Process policies
        for policy in sorted(self._policies.values(), key=lambda p: -p.priority):
            if not policy.enabled:
                continue
            if event.event_type in policy.event_types:
                if policy.evaluate(event):
                    self._execute_policy_action(policy, event)

        # Store event
        self._events.append(event)
        self._recent_events.append(event)

        # Trim old events
        if len(self._events) > self.config.max_events_in_memory:
            self._events = self._events[-self.config.max_events_in_memory :]

        if len(self._recent_events) > 1000:
            self._recent_events = self._recent_events[-1000:]

        # Call handlers
        handler = self._event_handlers.get(event.event_type.value)
        if handler:
            try:
                handler(event)
            except Exception as e:
                logger.error(f"Event handler failed: {e}")

        # Update anomaly baselines
        self._update_baselines(event)

        return True

    def _check_rate_limit(self, event_type: SafetyEventType) -> bool:
        """Check if event type is within rate limits."""
        key = event_type.value
        now = datetime.now().timestamp()

        # Reset window if needed
        if key in self._rate_limit_window:
            if now - self._rate_limit_window[key] > 60:  # 1 minute window
                self._event_counts[key] = 0
                self._rate_limit_window[key] = now
        else:
            self._rate_limit_window[key] = now

        # Check limit
        if key == SafetyEventType.PATCH_APPLIED.value:
            if self._event_counts.get(key, 0) >= self.config.max_patches_per_hour:
                return False
        else:
            if self._event_counts.get(key, 0) >= self.config.max_events_per_minute:
                return False

        self._event_counts[key] += 1
        return True

    def _execute_policy_action(self, policy: SafetyPolicy, event: SafetyEvent):
        """Execute policy action."""
        logger.warning(f"Policy triggered: {policy.name} for event {event.event_id}")

        if policy.action == "alert":
            self._send_alert(policy, event)
        elif policy.action == "block":
            self._block_operation(event)
        elif policy.action == "emergency_stop":
            self._trigger_emergency_stop(f"Policy {policy.policy_id}: {policy.name}")
        elif policy.action == "log_only":
            logger.info(f"Policy {policy.policy_id} logged event {event.event_id}")

    def _send_alert(self, policy: SafetyPolicy, event: SafetyEvent):
        """Send alert notification."""
        alert_msg = f"SAFETY ALERT: {policy.name} - {event.description}"
        logger.warning(alert_msg)

        # Webhook
        if self.config.alert_webhook:
            try:
                import aiohttp

                asyncio.create_task(self._send_webhook(alert_msg, event))
            except Exception:
                pass

        # Slack
        if self.config.notify_slack and self.config.slack_webhook:
            try:
                import aiohttp

                asyncio.create_task(self._send_slack(alert_msg, event))
            except Exception:
                pass

    async def _send_webhook(self, message: str, event: SafetyEvent):
        """Send webhook notification."""
        try:
            import aiohttp

            async with aiohttp.ClientSession() as session:
                await session.post(
                    self.config.alert_webhook,
                    json={
                        "message": message,
                        "event": event.to_dict(),
                    },
                )
        except Exception as e:
            logger.error(f"Webhook failed: {e}")

    async def _send_slack(self, message: str, event: SafetyEvent):
        """Send Slack notification."""
        try:
            import aiohttp

            async with aiohttp.ClientSession() as session:
                await session.post(
                    self.config.slack_webhook,
                    json={
                        "text": message,
                        "attachments": [
                            {
                                "color": (
                                    "danger"
                                    if event.severity
                                    in (SafetySeverity.CRITICAL, SafetySeverity.EMERGENCY)
                                    else "warning"
                                ),
                                "fields": [
                                    {
                                        "title": "Event Type",
                                        "value": event.event_type.value,
                                        "short": True,
                                    },
                                    {
                                        "title": "Severity",
                                        "value": event.severity.value,
                                        "short": True,
                                    },
                                    {
                                        "title": "Agent",
                                        "value": event.agent_id or "system",
                                        "short": True,
                                    },
                                ],
                            }
                        ],
                    },
                )
        except Exception as e:
            logger.error(f"Slack notification failed: {e}")

    def _block_operation(self, event: SafetyEvent):
        """Block an operation (implementation depends on context)."""
        logger.warning(f"Blocking operation due to safety policy: {event.event_id}")
        # In practice, this would integrate with the patch application system

    def _trigger_emergency_stop(self, reason: str):
        """Trigger emergency stop."""
        self._emergency_stopped = True
        self._emergency_stop_reason = reason

        event = SafetyEvent(
            event_type=SafetyEventType.EMERGENCY_STOP,
            severity=SafetySeverity.EMERGENCY,
            source="safety_hypervisor",
            description=f"Emergency stop triggered: {reason}",
            details={"reason": reason},
        )

        self.emit_event(event)

        logger.critical(f"EMERGENCY STOP: {reason}")

    def _update_baselines(self, event: SafetyEvent):
        """Update behavioral baselines for anomaly detection."""
        key = f"{event.agent_id}:{event.event_type.value}"
        self._behavior_baselines[key]["count"] = self._behavior_baselines[key].get("count", 0) + 1
        self._behavior_baselines[key]["last_seen"] = datetime.now().timestamp()

    async def _monitoring_loop(self):
        """Main monitoring loop."""
        while self._running:
            try:
                await asyncio.sleep(10)  # Check every 10 seconds

                # Check for emergency stop
                if self._emergency_stopped:
                    logger.critical(
                        f"System in emergency stop state: {self._emergency_stop_reason}"
                    )

                # Cleanup old events
                cutoff = datetime.now().timestamp() - (self.config.event_retention_days * 86400)
                self._events = [e for e in self._events if e.timestamp > cutoff]

            except Exception as e:
                logger.error(f"Monitoring loop error: {e}")
                await asyncio.sleep(5)

    async def _anomaly_detection_loop(self):
        """Anomaly detection loop."""
        while self._running:
            try:
                await asyncio.sleep(300)  # Every 5 minutes

                if not self.config.enable_anomaly_detection:
                    continue

                await self._detect_anomalies()

            except Exception as e:
                logger.error(f"Anomaly detection error: {e}")
                await asyncio.sleep(60)

    async def _detect_anomalies(self):
        """Detect anomalous behavior patterns."""
        now = datetime.now().timestamp()
        window_start = now - (self.config.anomaly_window_hours * 3600)

        # Analyze recent events
        recent = [e for e in self._recent_events if e.timestamp > window_start]

        # Group by agent and event type
        patterns = defaultdict(list)
        for event in recent:
            key = f"{event.agent_id}:{event.event_type.value}"
            patterns[key].append(event)

        # Detect anomalies
        for pattern_key, events in patterns.items():
            if len(events) < 5:
                continue

            # Calculate rate
            time_span = events[-1].timestamp - events[0].timestamp
            if time_span == 0:
                continue

            rate = len(events) / (time_span / 3600)  # per hour
            baseline = self._behavior_baselines.get(pattern_key, {}).get("rate", 0)

            # Check for spike
            if baseline > 0 and rate > baseline * 5:  # 5x baseline
                anomaly_event = SafetyEvent(
                    event_type=SafetyEventType.ANOMALOUS_BEHAVIOR,
                    severity=SafetySeverity.HIGH,
                    source="anomaly_detector",
                    agent_id=events[0].agent_id,
                    description=f"Anomalous rate detected: {rate:.1f}/hr vs baseline {baseline:.1f}/hr",
                    details={
                        "pattern": pattern_key,
                        "rate": rate,
                        "baseline": baseline,
                        "anomaly_score": min(rate / baseline, 10) / 10,
                        "event_count": len(events),
                    },
                )
                self.emit_event(anomaly_event)

    async def _resource_monitoring_loop(self):
        """Monitor system resources."""
        while self._running:
            try:
                await asyncio.sleep(30)

                if not self.config.monitor_resources:
                    continue

                # Check resources
                import psutil

                cpu = psutil.cpu_percent(interval=1)
                memory = psutil.virtual_memory().percent
                disk = psutil.disk_usage("/").percent

                if cpu > self.config.cpu_threshold:
                    event = SafetyEvent(
                        event_type=SafetyEventType.RESOURCE_EXHAUSTION,
                        severity=SafetySeverity.HIGH,
                        source="resource_monitor",
                        description=f"High CPU usage: {cpu:.1f}%",
                        details={
                            "cpu_percent": cpu,
                            "memory_percent": memory,
                            "disk_percent": disk,
                        },
                    )
                    self.emit_event(event)

                if memory > self.config.memory_threshold:
                    event = SafetyEvent(
                        event_type=SafetyEventType.RESOURCE_EXHAUSTION,
                        severity=SafetySeverity.HIGH,
                        source="resource_monitor",
                        description=f"High memory usage: {memory:.1f}%",
                        details={
                            "cpu_percent": cpu,
                            "memory_percent": memory,
                            "disk_percent": disk,
                        },
                    )
                    self.emit_event(event)

            except Exception as e:
                logger.error(f"Resource monitoring error: {e}")
                await asyncio.sleep(60)

    # Public API

    def add_policy(self, policy: SafetyPolicy) -> bool:
        """Add a safety policy."""
        if policy.policy_id in self._policies:
            return False
        self._policies[policy.policy_id] = policy
        return True

    def remove_policy(self, policy_id: str) -> bool:
        """Remove a safety policy."""
        if policy_id not in self._policies:
            return False
        del self._policies[policy_id]
        return True

    def get_policy(self, policy_id: str) -> Optional[SafetyPolicy]:
        """Get policy by ID."""
        return self._policies.get(policy_id)

    def is_emergency_stopped(self) -> bool:
        """Check if emergency stop is active."""
        return self._emergency_stopped

    def get_emergency_stop_reason(self) -> Optional[str]:
        """Get emergency stop reason."""
        return self._emergency_stop_reason

    def reset_emergency_stop(self, operator: str) -> bool:
        """Reset emergency stop (requires operator)."""
        if not self._emergency_stopped:
            return False

        self._emergency_stopped = False
        self._emergency_stop_reason = None

        event = SafetyEvent(
            event_type=SafetyEventType.EMERGENCY_STOP,
            severity=SafetySeverity.INFO,
            source="operator",
            description=f"Emergency stop reset by {operator}",
            agent_id=operator,
        )
        self.emit_event(event)

        return True

    def acknowledge_event(self, event_id: str, acknowledged_by: str) -> bool:
        """Acknowledge a safety event."""
        for event in self._events:
            if event.event_id == event_id:
                event.acknowledged = True
                event.acknowledged_by = acknowledged_by
                event.acknowledged_at = datetime.now().timestamp()
                return True
        return False

    def get_events(
        self,
        event_type: Optional[SafetyEventType] = None,
        severity: Optional[SafetySeverity] = None,
        agent_id: Optional[str] = None,
        since: Optional[float] = None,
        limit: int = 100,
    ) -> List[SafetyEvent]:
        """Get safety events with filters."""
        events = self._events

        if event_type:
            events = [e for e in events if e.event_type == event_type]
        if severity:
            events = [e for e in events if e.severity == severity]
        if agent_id:
            events = [e for e in events if e.agent_id == agent_id]
        if since:
            events = [e for e in events if e.timestamp >= since]

        return events[-limit:]

    def get_stats(self) -> Dict[str, Any]:
        """Get hypervisor statistics."""
        return {
            "running": self._running,
            "emergency_stopped": self._emergency_stopped,
            "emergency_stop_reason": self._emergency_stop_reason,
            "total_events": len(self._events),
            "recent_events": len(self._recent_events),
            "policies": len(self._policies),
            "active_policies": len([p for p in self._policies.values() if p.enabled]),
            "delegations": len(self._delegations) if hasattr(self, "_delegations") else 0,
        }
