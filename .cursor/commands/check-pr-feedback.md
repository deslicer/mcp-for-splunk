---
description: Check PR for code review comments and workflow failures, then fix issues
---

# Check PR Feedback and Fix Issues

You are tasked with checking for code review comments and CI workflow failures on a Pull Request, then resolving any issues found.

## Steps to Follow

### 1. Get PR Information
First, identify the current PR number and repository. Use the GitHub CLI or API:

```bash
# Get current branch
git branch --show-current

# List open PRs for this branch
gh pr list --head $(git branch --show-current) --json number,title,url
```

### 2. Check for PR Review Comments
Fetch any code review comments added since PR creation:

```bash
# Get PR comments (replace PR_NUMBER)
gh api repos/OWNER/REPO/pulls/PR_NUMBER/comments --jq '.[] | {user: .user.login, body: .body, path: .path, line: .line}'

# Get PR review comments
gh api repos/OWNER/REPO/pulls/PR_NUMBER/reviews --jq '.[] | {user: .user.login, state: .state, body: .body}'
```

### 3. Check Workflow Status
Check all workflow runs for the latest commit:

```bash
# Get latest commit SHA
LATEST_SHA=$(gh api repos/OWNER/REPO/pulls/PR_NUMBER/commits --jq '.[-1].sha')

# Check workflow runs
gh api "repos/OWNER/REPO/actions/runs?head_sha=$LATEST_SHA" --jq '.workflow_runs[] | {name: .name, status: .status, conclusion: .conclusion, id: .id}'
```

### 4. Get Failed Job Details
For any failed workflows, get the specific job and step that failed:

```bash
# Get jobs for a failed run (replace RUN_ID)
gh api repos/OWNER/REPO/actions/runs/RUN_ID/jobs --jq '.jobs[] | select(.conclusion == "failure") | {name: .name, steps: [.steps[] | select(.conclusion == "failure") | .name]}'
```

### 5. Fix Issues
Based on the feedback:
- **Code review comments**: Address each comment by making the suggested changes
- **Workflow failures**: 
  - Run tests locally first: `uv run pytest -v`
  - Run linting: `uv run ruff check src/ tests/`
  - Run type checking: `uv run mypy src/`
  - Fix any issues found

### 6. Commit and Push
After fixing issues:

```bash
git add -A
git commit -m "fix: address PR feedback

- [Describe changes made]"
git push
```

### 7. Verify
Re-check workflow status to ensure fixes resolved the issues.

## Common Issues and Fixes

### Gitleaks False Positives
Add fingerprints to `.gitleaksignore`:
```
commit:file:rule:line
```

### Test Failures
- Run tests locally to reproduce
- Check if failure is pre-existing (test on main branch)
- Update test expectations if server behavior is valid

### Linting Errors
```bash
uv run ruff check --fix src/ tests/
uv run ruff format src/ tests/
```
