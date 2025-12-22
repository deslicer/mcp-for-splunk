"""
Security monitoring and runtime protection for MCP Server for Splunk.

Provides real-time security monitoring, threat detection, and SIEM integration.
"""

import json
import logging
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class ThreatLevel(Enum):
    """Threat severity levels."""

    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ThreatType(Enum):
    """Types of security threats."""

    INJECTION_ATTEMPT = "injection_attempt"
    BRUTE_FORCE = "brute_force"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    SUSPICIOUS_PATTERN = "suspicious_pattern"
    UNAUTHORIZED_ACCESS = "unauthorized_access"
    DATA_EXFILTRATION = "data_exfiltration"
    ANOMALOUS_BEHAVIOR = "anomalous_behavior"


@dataclass
class SecurityEvent:
    """Represents a security event detected by the monitoring system."""

    timestamp: datetime
    threat_type: ThreatType
    threat_level: ThreatLevel
    source_ip: str | None
    user: str | None
    description: str
    details: dict[str, Any] = field(default_factory=dict)
    action_taken: str | None = None
    related_query: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for logging/SIEM export."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "threat_type": self.threat_type.value,
            "threat_level": self.threat_level.value,
            "source_ip": self.source_ip,
            "user": self.user,
            "description": self.description,
            "details": self.details,
            "action_taken": self.action_taken,
            "related_query": self.related_query,
        }

    def to_cef(self) -> str:
        """Convert to CEF (Common Event Format) for SIEM ingestion."""
        cef_header = f"CEF:0|MCP-Splunk|MCP-Server|1.0|{self.threat_type.value}|{self.description}|{self._cef_severity()}"

        cef_extensions = []
        if self.source_ip:
            cef_extensions.append(f"src={self.source_ip}")
        if self.user:
            cef_extensions.append(f"suser={self.user}")
        if self.action_taken:
            cef_extensions.append(f"act={self.action_taken}")
        if self.related_query:
            # Escape pipe characters and limit length
            escaped_query = self.related_query.replace("|", "\\|")[:500]
            cef_extensions.append(f"msg={escaped_query}")

        cef_extensions.append(f"rt={int(self.timestamp.timestamp() * 1000)}")

        return f"{cef_header}|{' '.join(cef_extensions)}"

    def _cef_severity(self) -> int:
        """Convert threat level to CEF severity (0-10)."""
        severity_map = {
            ThreatLevel.INFO: 2,
            ThreatLevel.LOW: 4,
            ThreatLevel.MEDIUM: 6,
            ThreatLevel.HIGH: 8,
            ThreatLevel.CRITICAL: 10,
        }
        return severity_map.get(self.threat_level, 5)


class SecurityMonitor:
    """
    Runtime security monitoring and threat detection system.

    Features:
    - Real-time threat detection
    - Rate limiting
    - Anomaly detection
    - SIEM integration (CEF, JSON, Splunk HEC)
    - Security event logging
    """

    def __init__(
        self,
        enable_rate_limiting: bool = True,
        rate_limit_requests: int = 100,
        rate_limit_window: int = 60,
        enable_anomaly_detection: bool = True,
        siem_export_enabled: bool = False,
        siem_export_path: str = "/var/log/mcp-security-events.cef",
    ):
        """
        Initialize security monitor.

        Args:
            enable_rate_limiting: Enable rate limiting per client
            rate_limit_requests: Max requests per window
            rate_limit_window: Time window in seconds
            enable_anomaly_detection: Enable behavioral anomaly detection
            siem_export_enabled: Export events to SIEM
            siem_export_path: Path for SIEM event export
        """
        self.enable_rate_limiting = enable_rate_limiting
        self.rate_limit_requests = rate_limit_requests
        self.rate_limit_window = rate_limit_window
        self.enable_anomaly_detection = enable_anomaly_detection
        self.siem_export_enabled = siem_export_enabled
        self.siem_export_path = siem_export_path

        # Rate limiting tracking
        self.request_counts: dict[str, list[float]] = defaultdict(list)

        # Anomaly detection baselines
        self.user_baselines: dict[str, dict[str, Any]] = defaultdict(lambda: {
            "total_requests": 0,
            "failed_requests": 0,
            "average_query_length": 0,
            "common_indexes": set(),
            "request_times": [],
        })

        # Security events buffer
        self.security_events: list[SecurityEvent] = []
        self.max_events_buffer = 1000

        logger.info(
            f"SecurityMonitor initialized: rate_limiting={enable_rate_limiting}, "
            f"anomaly_detection={enable_anomaly_detection}, siem_export={siem_export_enabled}"
        )

    def check_rate_limit(self, client_id: str, source_ip: str | None = None) -> tuple[bool, SecurityEvent | None]:
        """
        Check if client has exceeded rate limit.

        Args:
            client_id: Unique client identifier
            source_ip: Client IP address

        Returns:
            Tuple of (is_allowed, security_event)
        """
        if not self.enable_rate_limiting:
            return True, None

        current_time = time.time()
        cutoff_time = current_time - self.rate_limit_window

        # Clean old requests
        self.request_counts[client_id] = [
            ts for ts in self.request_counts[client_id] if ts > cutoff_time
        ]

        # Check limit
        request_count = len(self.request_counts[client_id])
        if request_count >= self.rate_limit_requests:
            event = SecurityEvent(
                timestamp=datetime.now(),
                threat_type=ThreatType.RATE_LIMIT_EXCEEDED,
                threat_level=ThreatLevel.MEDIUM,
                source_ip=source_ip,
                user=client_id,
                description=f"Rate limit exceeded: {request_count} requests in {self.rate_limit_window}s",
                details={
                    "request_count": request_count,
                    "limit": self.rate_limit_requests,
                    "window_seconds": self.rate_limit_window,
                },
                action_taken="Request blocked",
            )
            self._record_event(event)
            return False, event

        # Record this request
        self.request_counts[client_id].append(current_time)
        return True, None

    def analyze_query_security(
        self,
        query: str,
        user: str | None = None,
        source_ip: str | None = None,
        violations: list | None = None
    ) -> list[SecurityEvent]:
        """
        Analyze a query for security threats.

        Args:
            query: The SPL query to analyze
            user: Username executing the query
            source_ip: Source IP address
            violations: Security violations from query validator

        Returns:
            List of security events detected
        """
        events = []

        # Check for injection attempts based on violations
        if violations:
            for violation in violations:
                event = SecurityEvent(
                    timestamp=datetime.now(),
                    threat_type=ThreatType.INJECTION_ATTEMPT,
                    threat_level=self._map_severity_to_threat_level(violation.severity),
                    source_ip=source_ip,
                    user=user,
                    description=f"Security violation: {violation.message}",
                    details={
                        "violation_type": violation.violation_type.value,
                        "query_snippet": violation.query_snippet,
                        "remediation": violation.remediation,
                    },
                    action_taken="Query blocked",
                    related_query=query[:500],  # Limit query length
                )
                events.append(event)
                self._record_event(event)

        # Anomaly detection
        if self.enable_anomaly_detection and user:
            anomaly_events = self._detect_query_anomalies(query, user, source_ip)
            events.extend(anomaly_events)

        return events

    def _detect_query_anomalies(self, query: str, user: str, source_ip: str | None = None) -> list[SecurityEvent]:
        """Detect anomalous query patterns for a user."""
        events = []
        baseline = self.user_baselines[user]

        # Update baseline
        baseline["total_requests"] += 1
        query_length = len(query)

        # Calculate average query length
        if baseline["total_requests"] == 1:
            baseline["average_query_length"] = query_length
        else:
            baseline["average_query_length"] = (
                baseline["average_query_length"] * 0.9 + query_length * 0.1
            )

        # Detect abnormally long queries
        if query_length > baseline["average_query_length"] * 3 and query_length > 1000:
            event = SecurityEvent(
                timestamp=datetime.now(),
                threat_type=ThreatType.ANOMALOUS_BEHAVIOR,
                threat_level=ThreatLevel.LOW,
                source_ip=source_ip,
                user=user,
                description=f"Abnormally long query detected: {query_length} chars vs avg {int(baseline['average_query_length'])}",
                details={
                    "query_length": query_length,
                    "average_length": int(baseline["average_query_length"]),
                    "deviation": query_length / baseline["average_query_length"],
                },
                related_query=query[:500],
            )
            events.append(event)
            self._record_event(event)

        # Detect suspicious index patterns (accessing many different indexes)
        import re
        indexes = re.findall(r'index\s*=\s*([a-zA-Z0-9_]+)', query.lower())
        for idx in indexes:
            baseline["common_indexes"].add(idx)

        if len(baseline["common_indexes"]) > 20:  # Suspiciously many indexes
            event = SecurityEvent(
                timestamp=datetime.now(),
                threat_type=ThreatType.DATA_EXFILTRATION,
                threat_level=ThreatLevel.MEDIUM,
                source_ip=source_ip,
                user=user,
                description=f"User accessing {len(baseline['common_indexes'])} different indexes - potential data exfiltration",
                details={
                    "unique_indexes": len(baseline["common_indexes"]),
                    "recent_indexes": list(baseline["common_indexes"])[-10:],
                },
            )
            events.append(event)
            self._record_event(event)

        return events

    def _map_severity_to_threat_level(self, severity: str) -> ThreatLevel:
        """Map security violation severity to threat level."""
        severity_map = {
            "low": ThreatLevel.LOW,
            "medium": ThreatLevel.MEDIUM,
            "high": ThreatLevel.HIGH,
            "critical": ThreatLevel.CRITICAL,
        }
        return severity_map.get(severity.lower(), ThreatLevel.MEDIUM)

    def _record_event(self, event: SecurityEvent):
        """Record a security event."""
        # Add to buffer
        self.security_events.append(event)
        if len(self.security_events) > self.max_events_buffer:
            self.security_events.pop(0)

        # Log event
        logger.warning(
            f"SECURITY EVENT: {event.threat_type.value} - {event.threat_level.value} - {event.description}"
        )

        # Export to SIEM if enabled
        if self.siem_export_enabled:
            self._export_to_siem(event)

    def _export_to_siem(self, event: SecurityEvent):
        """Export event to SIEM in CEF format."""
        try:
            with open(self.siem_export_path, "a") as f:
                f.write(event.to_cef() + "\n")
        except Exception as e:
            logger.error(f"Failed to export security event to SIEM: {e}")

    def get_security_summary(self, hours: int = 24) -> dict[str, Any]:
        """
        Get security summary for the last N hours.

        Args:
            hours: Number of hours to summarize

        Returns:
            Dictionary with security metrics
        """
        cutoff_time = datetime.now() - timedelta(hours=hours)
        recent_events = [e for e in self.security_events if e.timestamp > cutoff_time]

        # Count by threat type and level
        by_type: defaultdict[str, int] = defaultdict(int)
        by_level: defaultdict[str, int] = defaultdict(int)
        by_user: defaultdict[str, int] = defaultdict(int)

        for event in recent_events:
            by_type[event.threat_type.value] += 1
            by_level[event.threat_level.value] += 1
            if event.user:
                by_user[event.user] += 1

        return {
            "time_range_hours": hours,
            "total_events": len(recent_events),
            "events_by_type": dict(by_type),
            "events_by_level": dict(by_level),
            "events_by_user": dict(by_user),
            "top_threats": sorted(by_type.items(), key=lambda x: x[1], reverse=True)[:5],
            "top_users": sorted(by_user.items(), key=lambda x: x[1], reverse=True)[:10],
        }

    def export_events_json(self, filepath: str, hours: int = 24) -> bool:
        """Export security events to JSON file. Returns True on success."""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        recent_events = [e for e in self.security_events if e.timestamp > cutoff_time]

        try:
            with open(filepath, "w") as f:
                json.dump([e.to_dict() for e in recent_events], f, indent=2)
            logger.info(f"Exported {len(recent_events)} security events to {filepath}")
            return True
        except OSError as e:
            logger.error(f"Failed to export security events to {filepath}: {e}")
            return False


# Global security monitor instance
_global_monitor: SecurityMonitor | None = None


def get_security_monitor() -> SecurityMonitor:
    """Get or create the global security monitor instance."""
    global _global_monitor
    if _global_monitor is None:
        import os
        _global_monitor = SecurityMonitor(
            enable_rate_limiting=os.getenv("MCP_RATE_LIMITING", "true").lower() == "true",
            rate_limit_requests=int(os.getenv("MCP_RATE_LIMIT", "100")),
            rate_limit_window=int(os.getenv("MCP_RATE_WINDOW", "60")),
            enable_anomaly_detection=os.getenv("MCP_ANOMALY_DETECTION", "true").lower() == "true",
            siem_export_enabled=os.getenv("MCP_SIEM_EXPORT", "false").lower() == "true",
            siem_export_path=os.getenv("MCP_SIEM_PATH", "/var/log/mcp-security-events.cef"),
        )
    return _global_monitor


def monitor_query_execution(query: str, user: str | None = None, source_ip: str | None = None, violations: list | None = None):
    """
    Monitor a query execution for security threats.

    This function should be called before executing any SPL query.

    Args:
        query: The SPL query being executed
        user: Username executing the query
        source_ip: Source IP address
        violations: Security violations from validator
    """
    monitor = get_security_monitor()
    events = monitor.analyze_query_security(query, user, source_ip, violations)

    if events:
        logger.warning(f"Security events detected for query: {len(events)} events")
        for event in events:
            logger.warning(f"  - {event.threat_type.value}: {event.description}")


