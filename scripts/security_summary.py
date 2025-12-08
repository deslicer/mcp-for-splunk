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
from typing import Any


@dataclass
class Finding:
    """Represents a single security finding."""

    tool: str
    severity: str  # critical, high, medium, low, info
    category: str  # sast, dependency, secret, container
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

    def by_tool(self, tool: str) -> list[Finding]:
        return [f for f in self.findings if f.tool == tool]

    def by_category(self, category: str) -> list[Finding]:
        return [f for f in self.findings if f.category == category]


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
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Warning: Could not parse Bandit results: {e}", file=sys.stderr)
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
                
                if "security" in rule_id.lower():
                    if severity == "medium":
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
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Warning: Could not parse Semgrep results: {e}", file=sys.stderr)
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
                security_severity = props.get("security-severity", "5.0")

                try:
                    score = float(security_severity)
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
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Warning: Could not parse Trivy results: {e}", file=sys.stderr)
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
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Warning: Could not parse Safety results: {e}", file=sys.stderr)
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
                description=leak.get("Description", "Potential secret detected"),
                file=leak.get("File", ""),
                line=leak.get("StartLine", 0),
                remediation="Rotate the exposed secret immediately and remove from history",
            ))
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Warning: Could not parse Gitleaks results: {e}", file=sys.stderr)
    return findings


def parse_pip_audit_json(filepath: str) -> list[Finding]:
    """Parse pip-audit JSON output."""
    findings = []
    try:
        with open(filepath) as f:
            data = json.load(f)

        dependencies = data.get("dependencies", [])
        for dep in dependencies:
            for vuln in dep.get("vulns", []):
                severity = "high" if vuln.get("fix_versions") else "medium"
                findings.append(Finding(
                    tool="pip-audit",
                    severity=severity,
                    category="dependency",
                    title=f"{dep.get('name')}: {vuln.get('id', 'unknown')}",
                    description=vuln.get("description", ""),
                    cve=vuln.get("id", ""),
                    remediation=f"Upgrade to: {', '.join(vuln.get('fix_versions', ['latest']))}",
                ))
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Warning: Could not parse pip-audit results: {e}", file=sys.stderr)
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
        "pip-audit": ["pip-audit-results/pip-audit.json", "pip-audit.json"],
    }

    parsers = {
        "bandit": parse_bandit_json,
        "semgrep": parse_semgrep_sarif,
        "trivy": parse_trivy_sarif,
        "safety": parse_safety_json,
        "gitleaks": parse_gitleaks_json,
        "pip-audit": parse_pip_audit_json,
    }

    for tool, file_patterns in patterns.items():
        found = False
        for pattern in file_patterns:
            filepath = Path(artifact_dir) / pattern
            if filepath.exists():
                findings = parsers[tool](str(filepath))
                result.findings.extend(findings)
                result.tool_status[tool] = f"✅ Parsed ({len(findings)} findings)" if findings else "✅ Clean"
                found = True
                break
        if not found:
            result.tool_status[tool] = "⏭️ No results found"

    return result


def generate_markdown_report(result: ScanResult, verbose: bool = False) -> str:
    """Generate a markdown security report."""
    lines = [
        "# 🔒 Security Scan Report",
        "",
        f"**Generated:** {result.scan_time}",
        "",
        "## 📊 Summary",
        "",
        "| Severity | Count |",
        "|----------|-------|",
        f"| 🔴 Critical | {result.critical_count} |",
        f"| 🟠 High | {result.high_count} |",
        f"| 🟡 Medium | {result.medium_count} |",
        f"| 🟢 Low | {result.low_count} |",
        f"| 🔑 Secrets | {result.secret_count} |",
        f"| **Total** | **{result.total_count}** |",
        "",
        "## 🔧 Tool Status",
        "",
        "| Tool | Status |",
        "|------|--------|",
    ]

    for tool, status in result.tool_status.items():
        lines.append(f"| {tool} | {status} |")

    lines.extend(["", "---", ""])

    # Critical and High findings always shown
    critical_high = [f for f in result.findings if f.severity in ("critical", "high")]
    if critical_high:
        lines.extend(["## 🚨 Critical & High Severity Findings", ""])
        for finding in critical_high:
            emoji = "🔴" if finding.severity == "critical" else "🟠"
            lines.extend([
                f"### {emoji} [{finding.tool.upper()}] {finding.title}",
                "",
                f"**Severity:** {finding.severity.upper()}",
                f"**Category:** {finding.category}",
            ])
            if finding.file:
                loc = f"{finding.file}:{finding.line}" if finding.line else finding.file
                lines.append(f"**Location:** `{loc}`")
            if finding.cve:
                lines.append(f"**CVE:** {finding.cve}")
            lines.extend(["", f"> {finding.description}", ""])
            if finding.remediation:
                lines.extend([f"**Remediation:** {finding.remediation}", ""])
            lines.extend(["---", ""])

    # Secret findings
    secrets = [f for f in result.findings if f.category == "secret"]
    if secrets:
        lines.extend([
            "## 🔑 Secret Leaks Detected",
            "",
            "⚠️ **IMMEDIATE ACTION REQUIRED**: Rotate all exposed secrets!",
            "",
        ])
        for finding in secrets:
            lines.append(f"- **{finding.title}** in `{finding.file}:{finding.line}`")
        lines.extend(["", "---", ""])

    # Medium/Low findings
    medium_low = [f for f in result.findings if f.severity in ("medium", "low")]
    if medium_low and verbose:
        lines.extend([
            "## ℹ️ Medium & Low Severity Findings",
            "",
            "<details>",
            f"<summary>Click to expand ({len(medium_low)} findings)</summary>",
            "",
        ])
        for finding in medium_low:
            emoji = "🟡" if finding.severity == "medium" else "🟢"
            loc = f" (`{finding.file}:{finding.line}`)" if finding.file else ""
            lines.append(f"- {emoji} **[{finding.tool}]** {finding.title}{loc}")
        lines.extend(["", "</details>", ""])
    elif medium_low:
        lines.extend([f"## ℹ️ Medium & Low Severity: {len(medium_low)} findings", "", "_Run with `--verbose` for details_", ""])

    # Recommendations
    lines.extend(["## 📝 Recommendations", ""])
    if result.critical_count > 0 or result.secret_count > 0:
        lines.append("1. 🚨 **BLOCK MERGE**: Critical vulnerabilities or secrets detected")
    if result.high_count > 0:
        lines.append("2. ⚠️ Address high severity findings before release")
    if result.medium_count > 0:
        lines.append("3. 📋 Create tickets for medium severity findings for next sprint")
    if result.total_count == 0:
        lines.append("✅ **All clear!** No security findings detected.")

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
            "secrets": result.secret_count,
            "total": result.total_count,
        },
        "tool_status": result.tool_status,
        "findings": [
            {
                "tool": f.tool,
                "severity": f.severity,
                "category": f.category,
                "title": f.title,
                "description": f.description,
                "file": f.file,
                "line": f.line,
                "cve": f.cve,
                "remediation": f.remediation,
            }
            for f in result.findings
        ],
    }, indent=2)


def check_failure_policy(result: ScanResult, fail_on: list[str]) -> tuple[bool, str]:
    """Check if the scan should fail based on policy."""
    reasons = []

    if "any" in fail_on and result.total_count > 0:
        return True, f"Policy 'any': {result.total_count} findings detected"

    if "secret" in fail_on and result.secret_count > 0:
        reasons.append(f"{result.secret_count} secret(s)")
    if "critical" in fail_on and result.critical_count > 0:
        reasons.append(f"{result.critical_count} critical")
    if "high" in fail_on and result.high_count > 0:
        reasons.append(f"{result.high_count} high")
    if "medium" in fail_on and result.medium_count > 0:
        reasons.append(f"{result.medium_count} medium")
    if "low" in fail_on and result.low_count > 0:
        reasons.append(f"{result.low_count} low")

    if reasons:
        return True, f"Policy violation: {', '.join(reasons)} findings"
    return False, "All checks passed"


def main():
    parser = argparse.ArgumentParser(description="Generate security scan summary report")
    parser.add_argument("--artifact-dir", default=".", help="Directory containing scan artifacts")
    parser.add_argument("--output", "-o", default="security-report.md", help="Output file path")
    parser.add_argument("--json", action="store_true", help="Output JSON instead of markdown")
    parser.add_argument("--verbose", "-v", action="store_true", help="Include detailed medium/low findings")
    parser.add_argument("--fail-on", type=str, default="", help="Comma-separated severities to fail on (critical,high,medium,low,secret,any)")
    parser.add_argument("--github-output", action="store_true", help="Write outputs for GitHub Actions")

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
    print(f"Report written to: {output_file}")

    if args.github_output:
        github_output = os.environ.get("GITHUB_OUTPUT", "")
        if github_output:
            with open(github_output, "a") as f:
                f.write(f"critical_count={result.critical_count}\n")
                f.write(f"high_count={result.high_count}\n")
                f.write(f"medium_count={result.medium_count}\n")
                f.write(f"low_count={result.low_count}\n")
                f.write(f"secret_count={result.secret_count}\n")
                f.write(f"total_count={result.total_count}\n")
        github_summary = os.environ.get("GITHUB_STEP_SUMMARY", "")
        if github_summary:
            with open(github_summary, "a") as f:
                f.write(generate_markdown_report(result, verbose=True))

    if args.fail_on:
        fail_severities = [s.strip().lower() for s in args.fail_on.split(",")]
        should_fail, reason = check_failure_policy(result, fail_severities)
        if should_fail:
            print(f"\n❌ SECURITY CHECK FAILED: {reason}")
            sys.exit(1)
        else:
            print(f"\n✅ Security check passed: {reason}")

    print("\n" + "=" * 50)
    print("SECURITY SCAN SUMMARY")
    print("=" * 50)
    print(f"Critical: {result.critical_count}")
    print(f"High:     {result.high_count}")
    print(f"Medium:   {result.medium_count}")
    print(f"Low:      {result.low_count}")
    print(f"Secrets:  {result.secret_count}")
    print(f"Total:    {result.total_count}")
    print("=" * 50)


if __name__ == "__main__":
    main()
