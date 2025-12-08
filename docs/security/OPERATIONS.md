# Security Operations Guide

This document describes the detection, triage, and remediation workflow for the MCP for Splunk project.

## Overview

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  Detection  │ -> │   Triage    │ -> │ Remediation │ -> │    Gate     │
│             │    │             │    │             │    │             │
│ • Bandit    │    │ • Parse     │    │ • Fix code  │    │ • Pass/Fail │
│ • Semgrep   │    │ • Summarize │    │ • Update    │    │ • PR block  │
│ • pip-audit │    │ • Classify  │    │   deps      │    │ • Release   │
│ • Trivy     │    │ • Report    │    │ • Rotate    │    │   approval  │
│ • Gitleaks  │    │             │    │   secrets   │    │             │
│ • CodeQL    │    │             │    │             │    │             │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
```

## Detection Tools

### SAST (Static Application Security Testing)

| Tool | Purpose | Output |
|------|---------|--------|
| **Bandit** | Python-specific security issues | `bandit-results.json` |
| **Semgrep** | Multi-language pattern matching | `semgrep.sarif` |
| **CodeQL** | Deep semantic analysis | GitHub Security tab |

### Dependency Scanning

| Tool | Purpose | Output |
|------|---------|--------|
| **pip-audit** | Python CVE database check | `pip-audit.json` |
| **Trivy** | Comprehensive vuln scanner | `trivy-results.json` |

### Secret Detection

| Tool | Purpose | Output |
|------|---------|--------|
| **Gitleaks** | Git history + file scanning | `gitleaks-results.json` |
| **TruffleHog** | Verified secret detection | Workflow logs |

## Triage Process

### Severity Classification

| Severity | CVSS Score | Action Required |
|----------|------------|-----------------|
| 🔴 **Critical** | 9.0+ | Block merge, immediate fix |
| 🟠 **High** | 7.0-8.9 | Fix before release |
| 🟡 **Medium** | 4.0-6.9 | Track, fix in next sprint |
| 🟢 **Low** | 0.1-3.9 | Backlog, address when convenient |
| 🔑 **Secret** | N/A | Block merge, rotate immediately |

### Automated Summary

The `scripts/security_summary.py` script consolidates all findings:

```bash
# Generate markdown report
python scripts/security_summary.py \
  --artifact-dir artifacts \
  --output security-report.md \
  --verbose

# Generate JSON for processing
python scripts/security_summary.py \
  --artifact-dir artifacts \
  --output security-report.json \
  --json

# Check failure policy
python scripts/security_summary.py \
  --artifact-dir artifacts \
  --fail-on critical,secret
```

### PR Comments

When a PR is opened, the security workflow automatically:
1. Runs all detection tools
2. Aggregates findings into a summary
3. Posts a comment on the PR with:
   - Severity breakdown
   - Critical/High findings (detailed)
   - Link to full artifacts

## Failure Policy

### Default Policy (During Initial Cleanup)

```yaml
FAIL_ON_SEVERITY: 'critical,secret'  # Block merge
WARN_ON_SEVERITY: 'high,medium'      # Warning only
```

### Tightened Policy (After Cleanup)

```yaml
FAIL_ON_SEVERITY: 'critical,high,secret'  # Block merge
WARN_ON_SEVERITY: 'medium'                 # Warning only
```

### Strict Policy (High-Security Environments)

```yaml
FAIL_ON_SEVERITY: 'critical,high,medium,secret'  # Block all
WARN_ON_SEVERITY: 'low'
```

### Manual Override

Run the workflow manually with custom settings:

```
Actions → Security Scanning → Run workflow
  fail_on: critical,secret
  verbose: true
```

## Remediation Playbooks

### 1. SAST Findings (Bandit/Semgrep)

```bash
# View findings
cat artifacts/bandit-results/bandit-results.txt

# Common fixes:
# B101: Remove assert in production code
# B105: Hardcoded password → use environment variables
# B301: Pickle usage → use json instead
# B608: SQL injection → use parameterized queries
```

### 2. Dependency Vulnerabilities

```bash
# View vulnerable packages
cat artifacts/pip-audit-results/pip-audit.md

# Update specific package
uv add package@latest

# Update all dependencies
uv lock --upgrade

# Verify fix
uv run pip-audit
```

### 3. Secret Leaks

**CRITICAL: Follow this process exactly**

1. **Do NOT commit a fix that just removes the secret**
   - The secret is already in git history

2. **Rotate the secret immediately**
   ```bash
   # For Splunk tokens
   # Go to Splunk → Settings → Tokens → Regenerate
   
   # For API keys
   # Go to provider dashboard → Regenerate key
   ```

3. **Update secret storage**
   ```bash
   # GitHub Secrets (for CI)
   gh secret set SPLUNK_TOKEN
   
   # Local development
   cp env.example .env
   # Edit .env with new credentials
   ```

4. **Remove from git history (if public)**
   ```bash
   # Use BFG Repo-Cleaner
   bfg --delete-files id_rsa
   bfg --replace-text passwords.txt
   git reflog expire --expire=now --all
   git gc --prune=now --aggressive
   ```

5. **Mark as false positive (if not a real secret)**
   ```bash
   # Add to .gitleaks.toml allowlist
   [[rules.allowlist.regexes]]
   description = "Test fixture"
   regex = '''test_api_key_[a-z]+'''
   ```

### 4. Container Vulnerabilities

```bash
# Rebuild with updated base image
docker build --pull --no-cache -t mcp-splunk .

# Scan locally
trivy image mcp-splunk

# Update Dockerfile base
FROM python:3.10-slim-bookworm  # Use latest patched version
```

## Monitoring & Alerts

### GitHub Security Dashboard

- Navigate to: Repository → Security → Overview
- View: Code scanning alerts, Dependabot alerts, Secret scanning

### Scheduled Scans

Daily scan at 2 AM UTC:
- Full security scan runs automatically
- Results stored as workflow artifacts
- Critical findings create issues (optional)

### Metrics to Track

| Metric | Target | Alert Threshold |
|--------|--------|-----------------|
| Critical findings | 0 | >0 |
| High findings | <5 | >10 |
| Mean time to remediate (critical) | <24h | >48h |
| Secret exposure incidents | 0 | >0 |

## Quick Reference

### Run Local Security Scan

```bash
# Install tools
pip install bandit pip-audit

# Run Bandit
bandit -r src/ -f txt

# Run pip-audit
uv export --no-dev --format requirements-txt > req.txt
pip-audit -r req.txt

# Run Gitleaks
gitleaks detect --source .

# Run security tests
uv run pytest tests/security/ -v
```

### Common Commands

```bash
# Check current security status
python scripts/security_summary.py --artifact-dir . --verbose

# Generate report for meeting
python scripts/security_summary.py -o security-status.md --verbose

# CI-style check (exits non-zero on violations)
python scripts/security_summary.py --fail-on critical,high,secret
```

## Contacts

- **Security Issues**: Create issue with `security` label
- **Urgent (secrets)**: security@your-org.com
- **Vulnerability Disclosure**: See SECURITY.md

## Changelog

| Date | Change |
|------|--------|
| 2025-12-08 | Initial operations guide |
| - | Added detection + remediation loop |
| - | Implemented configurable failure policy |
