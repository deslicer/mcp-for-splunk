# Security Policy

## Supported Versions

We release security updates for the following versions:

| Version | Supported          |
| ------- | ------------------ |
| 0.4.x   | :white_check_mark: |
| 0.3.x   | :white_check_mark: |
| < 0.3   | :x:                |

## Security Advisories

### Active Mitigations

#### CVE-2025-20381 (SVD-2025-1210) - Subsearch Injection

**Status**: ✅ NOT AFFECTED

**Description**: This vulnerability affects Splunk's official MCP Server which implements an MCP-layer command allowlist that can be bypassed via subsearches.

**Why We're Not Affected**: Our architecture differs fundamentally:
- We do NOT implement an MCP-layer command allowlist
- All SPL queries execute with the authenticated user's Splunk RBAC permissions
- Subsearches and index access are controlled by Splunk's native authorization
- Users can only access data their Splunk credentials permit

**Defense-in-Depth Measures**:
- Implemented SPL query validation in `src/core/security.py`
- Blocked dangerous commands that could modify data or execute external code (`collect`, `outputlookup`, `delete`, `sendemail`, `script`, `run`)
- Query complexity limits to prevent DoS
- Comprehensive security testing suite added

**Upgrade Path**:
```bash
# Update to latest version
git pull origin main
uv sync

# Verify security features are active
python -c "from src.core.security import get_security_config; import json; print(json.dumps(get_security_config(), indent=2))"
```

## Reporting a Vulnerability

We take security vulnerabilities seriously. If you discover a security issue, please report it responsibly.

### Reporting Process

1. **DO NOT** open a public GitHub issue
2. **DO** send a detailed report to: [security@deslicer.com] or use GitHub Security Advisories
3. **Include** in your report:
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact assessment
   - Suggested remediation (if any)

### What to Expect

- **Initial Response**: Within 48 hours
- **Status Update**: Within 7 days
- **Fix Timeline**: 
  - Critical: 1-7 days
  - High: 7-30 days
  - Medium: 30-90 days
  - Low: 90+ days or next release

### Disclosure Policy

- We follow **coordinated disclosure** principles
- Security advisories will be published after fixes are available
- We will credit security researchers (with permission)
- Typical disclosure timeline: 90 days after initial report

## Security Best Practices

### For Users

1. **Keep Updated**: Always use the latest version
   ```bash
   git pull origin main
   uv sync
   ```

2. **Environment Variables**: Never commit credentials
   ```bash
   # Use .env files (already in .gitignore)
   cp env.example .env
   # Edit .env with your credentials
   ```

3. **Network Security**: Run behind firewalls/reverse proxies
   ```yaml
   # Example: Using Traefik for TLS termination
   services:
     mcp-server:
       environment:
         MCP_SERVER_HOST: 0.0.0.0
         MCP_SERVER_PORT: 8001
       networks:
         - internal
   ```

4. **Least Privilege**: Use Splunk service accounts with minimal permissions
   ```spl
   # Create a read-only user for MCP
   | rest /services/authentication/users | search title=mcp_readonly
   ```

5. **Audit Logging**: Enable MCP audit logs
   ```bash
   export MCP_LOG_LEVEL=INFO
   # Check logs
   tail -f logs/mcp_splunk_server.log
   ```

### For Developers

1. **Security Reviews**: All PRs with security implications require review
2. **Dependency Updates**: Keep dependencies updated
   ```bash
   uv lock --upgrade
   ```
3. **Security Testing**: Run security tests before committing
   ```bash
   pytest tests/security/ -v
   ```
4. **Static Analysis**: Use pre-commit hooks
   ```bash
   pre-commit install
   pre-commit run --all-files
   ```

## Security Features

### Query Validation (v0.4.0+)

**Dangerous Command Blocking**
```python
from src.core.security import validate_query, QuerySecurityError

# Data modification commands are blocked
try:
    validate_query("index=main | outputlookup mydata.csv")
except QuerySecurityError:
    print("Blocked - outputlookup can modify data")

# External execution commands are blocked
try:
    validate_query("| script python my_script.py")
except QuerySecurityError:
    print("Blocked - script can execute external code")

# Normal queries are allowed (access controlled by Splunk RBAC)
validate_query("index=main error | stats count")  # OK
validate_query("index=main [ search index=_audit ]")  # OK - user RBAC applies
```

**Forbidden Commands**
The following commands are blocked at the MCP layer as defense-in-depth:
- `collect`, `outputlookup`, `outputcsv` - Data modification
- `delete` - Data deletion
- `sendemail` - External communication
- `script`, `run` - External code execution

**Index Access**
- Index access is controlled by Splunk RBAC, not the MCP layer
- Users can only query indexes their Splunk credentials permit

### Authentication & Authorization

**Current Implementation**:
- Token-based authentication
- Username/password authentication
- HTTP header-based credential passing
- Session-based credential caching

**Planned Enhancements**:
- OAuth 2.0 / OIDC support
- RBAC (Role-Based Access Control)
- API key management
- Multi-factor authentication (MFA)

### Network Security

**TLS/HTTPS**:
```bash
# Run behind a reverse proxy with TLS
# Example with Traefik:
docker-compose -f docker-compose.yml -f docker-compose-traefik.yml up
```

**Rate Limiting** (Planned):
- Request rate limiting per client
- Query complexity limits
- Resource usage monitoring

### Secrets Management

**Current**:
- `.env` files (gitignored)
- Environment variables
- HTTP headers for credentials

**Best Practices**:
```bash
# Use a secrets manager
export SPLUNK_PASSWORD=$(aws secretsmanager get-secret-value --secret-id splunk-password --query SecretString --output text)

# Or use Docker secrets
docker secret create splunk_password password.txt
```

## Compliance

### Standards

We aim to align with:
- **OWASP Top 10**: Protection against common web vulnerabilities
- **CWE Top 25**: Mitigation of dangerous software weaknesses
- **SOC 2 Type II**: Security controls for service organizations
- **HIPAA**: Healthcare data protection (when applicable)
- **PCI-DSS**: Payment card industry standards (when applicable)

### Security Controls

| Control | Status | Description |
|---------|--------|-------------|
| Input Validation | ✅ Implemented | SPL query validation, command filtering |
| Authentication | ✅ Implemented | Token and credential-based auth |
| Authorization | 🔄 Partial | User-based, RBAC planned |
| Encryption in Transit | ✅ Supported | TLS via reverse proxy |
| Encryption at Rest | ⚠️ External | Depends on Splunk configuration |
| Audit Logging | ✅ Implemented | Request and query logging |
| Secrets Management | ✅ Implemented | Environment variables, headers |
| Dependency Scanning | ✅ Automated | Daily scans via GitHub Actions |
| SAST | ✅ Automated | Bandit, Semgrep, CodeQL |
| Secret Scanning | ✅ Automated | Gitleaks, TruffleHog |

## Security Tools & Scanning

### Automated Scans

Our CI/CD pipeline includes:

1. **Bandit**: Python-specific security linter
2. **Semgrep**: Multi-pattern SAST tool
3. **CodeQL**: Advanced semantic analysis
4. **Safety**: Python dependency vulnerability scanner
5. **Trivy**: Container and dependency scanner
6. **Gitleaks**: Secret detection in git history
7. **TruffleHog**: Secret and credential scanner

### Running Scans Locally

```bash
# Install security tools
pip install bandit safety

# Run Bandit scan
bandit -r src/ -ll

# Check dependencies
safety check --file requirements.txt

# Run security tests
pytest tests/security/ -v
```

## Incident Response

### Security Incident Categories

1. **Critical**: Active exploitation, data breach
2. **High**: Vulnerability with high impact
3. **Medium**: Limited impact vulnerability
4. **Low**: Informational, no immediate risk

### Response Process

1. **Detection**: Security scans, user reports, monitoring
2. **Containment**: Disable affected features, deploy hotfix
3. **Investigation**: Root cause analysis, impact assessment
4. **Remediation**: Develop and test fix
5. **Communication**: Notify users, publish advisory
6. **Post-Mortem**: Document lessons learned


## Contact

- **Security Issues**: [security@deslicer.com]
- **General Questions**: [GitHub Discussions](../../discussions)
- **Bug Reports**: [GitHub Issues](../../issues) (non-security only)

## References

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [CWE Top 25](https://cwe.mitre.org/top25/)
- [Splunk Security Advisories](https://advisory.splunk.com/)
- [National Vulnerability Database](https://nvd.nist.gov/)

---

**Last Updated**: December 5, 2025
**Version**: 1.0
