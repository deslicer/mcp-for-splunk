#!/usr/bin/env python3
"""
Security Summary Generator

Parses security scan outputs (Bandit, Trivy, Safety, etc.) and generates
a consolidated markdown report with severity counts and failure decisions.

Usage:
    python scripts/security_summary.py --output security-report.md
    python scripts/security_summary.py --json --output security-report.json
    python scripts/security_summary.py --fail-on critical,high,secret
"""

import argparse
import json
import os
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path


@dataclass
class Finding:
    """Represents a single security finding."""

    tool: str
    severity: str
    category: str
    title: str
    description: str
    file: str = ""
    line: int = 0
    cve: str = ""
    remediation: str = ""


@dataclass
class ScanResult:
    """Aggregated results from all security scans."""

    findings: list[Finding] = field(default_factory=list)
    tool_status: dict[str, str] = field(default_factory=dict)
    scan_time: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    @property
    def critical_count(self) -> int:
        return len([f for f in self.findings if f.severity == "critical"])

    @property
    def high_count(self) -> int:
        return len([f for f in self.findings if f.severity == "high"])

    @property
    def medium_count(self) -> int:
        return len([f for f in self.findings if f.severity == "medium"])

    @property
    def low_count(self) -> int:
        return len([f for f in self.findings if f.severity == "low"])

    @property
    def secret_count(self) -> int:
        return len([f for f in self.findings if f.category == "secret"])

    @property
    def total_count(self) -> int:
        return len(self.findings)


def parse_bandit_json(filepath: str) -> list[Finding]:
    """Parse Bandit JSON output."""
    findings = []
    try:
        with open(filepath) as f:
            data = json.load(f)

        severity_map = {"HIGH": "high", "MEDIUM": "medium", "LOW": "low"}
        for result in data.get("results", []):
            severity = severity_map.get(result.get("issue_severity", "LOW"), "low")
            if result.get("issue_confidence") == "HIGH" and result.get("issue_severity") == "HIGH":
                severity = "critical"
            findings.append(Finding(
                tool="bandit",
                severity=severity,
                category="sast",
                title=result.get("test_id", "Unknown") + ": " + result.get("test_name", "Unknown"),
                description=result.get("issue_text", ""),
                file=result.get("filename", ""),
                line=result.get("line_number", 0),
                remediation=f"Review code at {result.get('filename')}:{result.get('line_number')}",
            ))
    except (FileNotFoundError, json.JSONDecodeError):
        pass  # File missing or malformed - tool may not have run
    return findings


def parse_semgrep_sarif(filepath: str) -> list[Finding]:
    """Parse Semgrep SARIF output."""
    findings = []
    try:
        with open(filepath) as f:
            data = json.load(f)

        level_map = {"error": "high", "warning": "medium", "note": "low", "none": "info"}
        for run in data.get("runs", []):
            rules = {r["id"]: r for r in run.get("tool", {}).get("driver", {}).get("rules", [])}
            for result in run.get("results", []):
                rule_id = result.get("ruleId", "unknown")
                rule = rules.get(rule_id, {})
                level = result.get("level", "warning")
                severity = level_map.get(level, "medium")
                if "security" in rule_id.lower() and severity == "medium":
                    severity = "high"
                location = result.get("locations", [{}])[0].get("physicalLocation", {})
                findings.append(Finding(
                    tool="semgrep",
                    severity=severity,
                    category="sast",
                    title=rule_id,
                    description=result.get("message", {}).get("text", ""),
                    file=location.get("artifactLocation", {}).get("uri", ""),
                    line=location.get("region", {}).get("startLine", 0),
                    remediation=rule.get("help", {}).get("text", ""),
                ))
    except (FileNotFoundError, json.JSONDecodeError):
        pass  # File missing or malformed - tool may not have run
    return findings


def parse_trivy_sarif(filepath: str) -> list[Finding]:
    """Parse Trivy SARIF output."""
    findings = []
    try:
        with open(filepath) as f:
            data = json.load(f)

        for run in data.get("runs", []):
            rules = {r["id"]: r for r in run.get("tool", {}).get("driver", {}).get("rules", [])}
            for result in run.get("results", []):
                rule_id = result.get("ruleId", "unknown")
                rule = rules.get(rule_id, {})
                props = rule.get("properties", {})
                try:
                    score = float(props.get("security-severity", "5.0"))
                    if score >= 9.0:
                        severity = "critical"
                    elif score >= 7.0:
                        severity = "high"
                    elif score >= 4.0:
                        severity = "medium"
                    else:
                        severity = "low"
                except ValueError:
                    severity = "medium"
                location = result.get("locations", [{}])[0].get("physicalLocation", {})
                findings.append(Finding(
                    tool="trivy",
                    severity=severity,
                    category="dependency",
                    title=rule_id,
                    description=result.get("message", {}).get("text", ""),
                    file=location.get("artifactLocation", {}).get("uri", ""),
                    cve=rule_id if rule_id.startswith("CVE-") else "",
                    remediation=rule.get("help", {}).get("text", ""),
                ))
    except (FileNotFoundError, json.JSONDecodeError):
        pass  # File missing or malformed - tool may not have run
    return findings


def parse_safety_json(filepath: str) -> list[Finding]:
    """Parse Safety JSON output."""
    findings = []
    try:
        with open(filepath) as f:
            data = json.load(f)

        vulns = data.get("vulnerabilities", [])
        if not vulns:
            vulns = data if isinstance(data, list) else []

        for vuln in vulns:
            severity = "medium"
            cvss = vuln.get("severity", {})
            if isinstance(cvss, dict):
                score = cvss.get("cvss_score", 5.0)
                if score >= 9.0:
                    severity = "critical"
                elif score >= 7.0:
                    severity = "high"
                elif score >= 4.0:
                    severity = "medium"
                else:
                    severity = "low"
            findings.append(Finding(
                tool="safety",
                severity=severity,
                category="dependency",
                title=f"{vuln.get('package_name', 'unknown')} vulnerability",
                description=vuln.get("advisory", vuln.get("vulnerability_id", "")),
                cve=vuln.get("cve", vuln.get("vulnerability_id", "")),
                remediation=f"Upgrade {vuln.get('package_name')} to latest",
            ))
    except (FileNotFoundError, json.JSONDecodeError):
        pass  # File missing or malformed - tool may not have run
    return findings


def parse_gitleaks_json(filepath: str) -> list[Finding]:
    """Parse Gitleaks JSON output."""
    findings = []
    try:
        with open(filepath) as f:
            data = json.load(f)

        for leak in data if isinstance(data, list) else []:
            findings.append(Finding(
                tool="gitleaks",
                severity="critical",
                category="secret",
                title=f"Secret Leak: {leak.get('RuleID', 'unknown')}",
                description="Potential secret detected",
                file=leak.get("File", ""),
                line=leak.get("StartLine", 0),
                remediation="Rotate the exposed secret immediately",
            ))
    except (FileNotFoundError, json.JSONDecodeError):
        pass  # File missing or malformed - tool may not have run
    return findings


def collect_findings(artifact_dir: str = ".") -> ScanResult:
    """Collect findings from all scan outputs."""
    result = ScanResult()

    patterns = {
        "bandit": ["bandit-results/bandit-results.json", "bandit-results.json"],
        "semgrep": ["semgrep.sarif", "semgrep-results/semgrep.sarif"],
        "trivy": ["trivy-results.sarif", "trivy-python-results/trivy-results.sarif"],
        "safety": ["safety-results/safety-results.json", "safety-results.json"],
        "gitleaks": ["gitleaks-results/gitleaks-results.json", "gitleaks-results.json"],
    }

    parsers = {
        "bandit": parse_bandit_json,
        "semgrep": parse_semgrep_sarif,
        "trivy": parse_trivy_sarif,
        "safety": parse_safety_json,
        "gitleaks": parse_gitleaks_json,
    }

    for tool, file_patterns in patterns.items():
        found = False
        for pattern in file_patterns:
            filepath = Path(artifact_dir) / pattern
            if filepath.exists():
                findings = parsers[tool](str(filepath))
                result.findings.extend(findings)
                result.tool_status[tool] = f"Parsed ({len(findings)} findings)" if findings else "Clean"
                found = True
                break
        if not found:
            result.tool_status[tool] = "No results found"

    return result


def generate_markdown_report(result: ScanResult, verbose: bool = False) -> str:
    """Generate a markdown security report."""
    has_secrets = result.secret_count > 0
    lines = [
        "# Security Scan Report",
        "",
        f"**Generated:** {result.scan_time}",
        "",
        "## Summary",
        "",
        "| Severity | Count |",
        "|----------|-------|",
        f"| Critical | {result.critical_count} |",
        f"| High | {result.high_count} |",
        f"| Medium | {result.medium_count} |",
        f"| Low | {result.low_count} |",
        f"| Secrets | {'Yes' if has_secrets else 'No'} |",
        f"| **Total** | **{result.total_count}** |",
        "",
        "## Tool Status",
        "",
    ]

    for tool, status in result.tool_status.items():
        lines.append(f"- {tool}: {status}")

    lines.append("")

    critical_high = [f for f in result.findings if f.severity in ("critical", "high")]
    if critical_high:
        lines.extend(["## Critical & High Severity Findings", ""])
        for finding in critical_high:
            lines.extend([
                f"### [{finding.tool.upper()}] {finding.title}",
                f"- **Severity:** {finding.severity.upper()}",
                f"- **Category:** {finding.category}",
            ])
            if finding.file:
                lines.append(f"- **Location:** `{finding.file}:{finding.line}`")
            if finding.cve:
                lines.append(f"- **CVE:** {finding.cve}")
            if finding.remediation:
                lines.append(f"- **Remediation:** {finding.remediation}")
            lines.append("")

    if has_secrets:
        lines.extend([
            "## Secrets Detected",
            "",
            "**IMMEDIATE ACTION REQUIRED**: Rotate all exposed secrets!",
            "",
        ])

    if result.total_count == 0:
        lines.append("**All clear!** No security findings detected.")

    return "\n".join(lines)


def generate_json_report(result: ScanResult) -> str:
    """Generate a JSON security report."""
    return json.dumps({
        "scan_time": result.scan_time,
        "summary": {
            "critical": result.critical_count,
            "high": result.high_count,
            "medium": result.medium_count,
            "low": result.low_count,
            "has_secrets": result.secret_count > 0,
            "total": result.total_count,
        },
        "tool_status": result.tool_status,
        "findings": [
            {
                "tool": f.tool,
                "severity": f.severity,
                "category": f.category,
                "title": f.title,
                "file": f.file,
                "line": f.line,
                "cve": f.cve,
            }
            for f in result.findings
            if f.category != "secret"  # Don't include secret details in JSON
        ],
    }, indent=2)


def check_failure_policy(result: ScanResult, fail_on: list[str]) -> tuple[bool, str]:
    """Check if the scan should fail based on policy."""
    if "any" in fail_on and result.total_count > 0:
        return True, "findings detected"

    has_failure = False
    if "secret" in fail_on and result.secret_count > 0:
        has_failure = True
    if "critical" in fail_on and result.critical_count > 0:
        has_failure = True
    if "high" in fail_on and result.high_count > 0:
        has_failure = True
    if "medium" in fail_on and result.medium_count > 0:
        has_failure = True

    if has_failure:
        return True, "policy violation"
    return False, "passed"


def main():
    parser = argparse.ArgumentParser(description="Generate security scan summary report")
    parser.add_argument("--artifact-dir", default=".", help="Directory containing scan artifacts")
    parser.add_argument("--output", "-o", default="security-report.md", help="Output file path")
    parser.add_argument("--json", action="store_true", help="Output JSON instead of markdown")
    parser.add_argument("--verbose", "-v", action="store_true", help="Include detailed findings")
    parser.add_argument("--fail-on", type=str, default="", help="Severities to fail on")
    parser.add_argument("--github-output", action="store_true", help="Write GitHub Actions outputs")

    args = parser.parse_args()
    result = collect_findings(args.artifact_dir)

    if args.json:
        report = generate_json_report(result)
        output_file = args.output if args.output.endswith(".json") else args.output + ".json"
    else:
        report = generate_markdown_report(result, verbose=args.verbose)
        output_file = args.output

    with open(output_file, "w") as f:
        f.write(report)

    if args.github_output:
        github_output = os.environ.get("GITHUB_OUTPUT", "")
        if github_output:
            with open(github_output, "a") as f:
                f.write(f"critical_count={result.critical_count}\n")
                f.write(f"high_count={result.high_count}\n")
                f.write(f"total_count={result.total_count}\n")

    if args.fail_on:
        fail_severities = [s.strip().lower() for s in args.fail_on.split(",")]
        should_fail, reason = check_failure_policy(result, fail_severities)
        if should_fail:
            sys.exit(1)

    # Print non-sensitive summary
    print(f"Critical: {result.critical_count}, High: {result.high_count}, Total: {result.total_count}")


if __name__ == "__main__":
    main()
