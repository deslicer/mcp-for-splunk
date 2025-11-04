# Authentication for MCP Server for Splunk

 Make your deployment secure by enabling request authentication without forking this repo. Configure an auth provider via environment variables (dynamic import), or use a Supabase API provider from an external package for development and hosted projects.

## 🚀 Quick Start (2 minutes)

Choose ONE of the following setups.

### Option A: Use your own provider (recommended for production)

1) Install your auth package (pip installable) that exports a callable or class

```bash
pip install your-auth-package
```

2) Export environment variables (bash/zsh)

```bash
export MCP_AUTH_PROVIDER="your_pkg.module:create_verifier"   # or your_pkg.module.ClassName
export MCP_AUTH_PROVIDER_KWARGS='{"issuer":"https://idp","jwks_uri":"https://idp/.well-known/jwks.json","audience":"mcp-api"}'
```

PowerShell (Windows):

```powershell
$env:MCP_AUTH_PROVIDER="your_pkg.module:create_verifier"
$env:MCP_AUTH_PROVIDER_KWARGS='{"issuer":"https://idp","jwks_uri":"https://idp/.well-known/jwks.json","audience":"mcp-api"}'
```

3) Start the server

```bash
uv run mcp-server
```

Expected: Logs include "Using dynamic auth provider: your_pkg.module:create_verifier".

### Option B: Use a Supabase API provider from an external package (great for dev)

1) Export environment variables (bash/zsh)

```bash
# Install your external Supabase auth plugin first, then:
export MCP_AUTH_PROVIDER="your_supabase_auth_pkg.module:SupabaseAuthProvider"
export SUPABASE_URL="https://<project>.supabase.co"
export SUPABASE_ANON_KEY="<anon_key>"
```

PowerShell (Windows):

```powershell
# Install your external Supabase auth plugin first, then:
$env:MCP_AUTH_PROVIDER="your_supabase_auth_pkg.module:SupabaseAuthProvider"
$env:SUPABASE_URL="https://<project>.supabase.co"
$env:SUPABASE_ANON_KEY="<anon_key>"
```

2) Optional dependency

```bash
pip install httpx
```

3) Start the server

```bash
uv run python -m src.server
```

4) Test

Validate the token directly with Supabase (should be 200):

```bash
curl -i \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "apikey: $SUPABASE_ANON_KEY" \
  "$SUPABASE_URL/auth/v1/user"
```

Then hit the server:

```bash
# Valid token → 200
curl -i -H "Authorization: Bearer $ACCESS_TOKEN" http://localhost:8001/health

# Missing/invalid token → 401 with message
curl -i http://localhost:8001/health
```

Notes:

- ACCESS_TOKEN must be a real Supabase access token (not anon/service keys).
- If you use mcp-server --local (stdio), your client must support sending Authorization headers. Prefer HTTP for auth testing.

## 📚 How it works

- Dynamic provider: `src/server.py` reads `MCP_AUTH_PROVIDER` and optional `MCP_AUTH_PROVIDER_KWARGS` to import and initialize any provider at runtime. Use `module:callable` or `module.ClassName` formats. This lets you ship your auth in a separate repository/package.
- Supabase API provider: supplied by an external package you install. The provider typically calls `POST /auth/v1/user` with the bearer token and anon key. If the token is valid, the request is authenticated; otherwise, a 401 is returned with a clear message.
- Disable auth entirely by setting `MCP_AUTH_DISABLED=true`.

## 🔧 Reference configuration

- **Dynamic provider**
  - `MCP_AUTH_PROVIDER`: module:callable or module.ClassName
  - `MCP_AUTH_PROVIDER_KWARGS`: JSON string of kwargs passed to the callable/class
- **Supabase API provider (external)**
  - `MCP_AUTH_PROVIDER="your_supabase_auth_pkg.module:SupabaseAuthProvider"`
  - `SUPABASE_URL`: e.g., `https://<project>.supabase.co`
  - `SUPABASE_ANON_KEY`: project anon key
- **Global**
  - `MCP_AUTH_DISABLED=true` to turn off auth
  - `MCP_LOG_LEVEL=DEBUG` for verbose logs

## 🧪 Expected responses

- **Success**: `200 OK` for authenticated requests (e.g., `/health`).
- **Missing token**: `401 Unauthorized` with a message like `Missing Authorization: Bearer <token> header.`
- **Invalid/expired token**: `401 Unauthorized` with a message like `Bearer token is invalid or expired.`

## 🤝 Community & Support

- Open an issue or join discussions from the project’s main README.
- See our security guidance in [../guides/security.md](../guides/security.md).
- Writing style and README standards: [../readme-guide.md](../readme-guide.md).

---

You can package your auth provider independently and inject it with `MCP_AUTH_PROVIDER`. No forks required; the same server binary runs in dev, staging, and prod with different auth via environment.
