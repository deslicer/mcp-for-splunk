# README Writing Guide

> **Use this guide whenever creating or updating README files in the MCP Server for Splunk project**

## 🎯 README Philosophy

### The 3-Layer Principle
1. **Hook** (10 seconds) - Why should I care?
2. **Quick Start** (2 minutes) - Can I get this working?
3. **Navigation** (30 seconds) - Where do I go next?

### Target Audience First
Before writing, define:
- **Primary personas** (evaluators, implementers, integrators)
- **Technical expertise level** (beginner, intermediate, advanced)
- **Time constraints** (5 minutes vs 2 hours)

## 📋 README Structure Template

### 1. Hero Section (Above the Fold)
```markdown
# Project Name

[![Badges](shields.io-badges-here)]

> **One-sentence value proposition that captures the essence**

A concise paragraph explaining what this does, why it matters, and who it's for.

## 🌟 Key Features
- ✅ **Feature 1** - Benefit-focused description
- ✅ **Feature 2** - What user gets, not what it does
- ✅ **Feature 3** - Outcome-oriented language
```

### 2. Quick Start Section
```markdown
## 🚀 Quick Start

### Prerequisites
- Tool 1 (with version)
- Tool 2 (with installation link)

### Installation
```bash
# One-command install when possible
./scripts/build_and_run.sh
```

### First Success
```bash
# Command that proves it works
curl http://localhost:8000/health
# Expected output: {"status": "ok"}
```
```

### 3. Navigation Hub
```markdown
## 📚 Documentation

| Document | Purpose | Audience |
|----------|---------|----------|
| [Getting Started](docs/getting-started/) | First-time setup | New users |
| [User Guide](docs/guides/) | Common tasks | Active users |
| [API Reference](docs/api/) | Integration details | Developers |
| [Contributing](docs/community/contributing.md) | How to help | Contributors |
```

### 4. Community Section
```markdown
## 🤝 Community & Support

- 🐛 **Issues**: [GitHub Issues](link)
- 💬 **Discussions**: [GitHub Discussions](link)
- 📖 **Documentation**: [Full Docs](link)
- 🔧 **Interactive Testing**: [Tool Name](link)
```

## ✅ README Checklist

### Content Requirements
- [ ] **Clear project title** (descriptive, not internal codename)
- [ ] **One-sentence value proposition**
- [ ] **Target audience identified**
- [ ] **Quick start under 5 minutes**
- [ ] **Prerequisites clearly listed**
- [ ] **Installation instructions tested**
- [ ] **First success demonstration**
- [ ] **Links to detailed documentation**
- [ ] **Support/community information**
- [ ] **License information**

### Quality Standards
- [ ] **Length**: 800-1200 words max
- [ ] **Paragraphs**: 3-4 sentences max
- [ ] **Code blocks**: Tested and working
- [ ] **Links**: All functional and current
- [ ] **Images**: Optimized and accessible
- [ ] **Tone**: Welcoming and professional

### Visual Elements
- [ ] **Project logo** (if available)
- [ ] **Badges** (build status, version, license)
- [ ] **Demo GIF or screenshot**
- [ ] **Clear section headers**
- [ ] **Proper Markdown formatting**
- [ ] **Consistent emoji usage**

## 🎨 Style Guidelines

### Writing Style
- **Use active voice**: "Run the command" not "The command should be run"
- **Be specific**: "Takes 2 minutes" not "Quick setup"
- **Show outcomes**: "You'll see a success message" not "The system will respond"
- **Use "you" language**: Direct address to the reader

### Formatting Standards
```markdown
# H1: Document title only
## H2: Major sections
### H3: Subsections (use sparingly)

**Bold**: Important terms, actions
*Italic*: Emphasis, file names
`Code`: Commands, file paths, values

> **Note**: Use callouts for important information
> **Warning**: Use for potential issues
> **Tip**: Use for helpful suggestions
```

### Code Block Standards
```markdown
# Include language for syntax highlighting
```bash
# Comment explaining what this does
command --with-flags value
```

# Always show expected output when helpful
```
Expected output:
✅ Server started successfully
🔗 Access at: http://localhost:8000
```
```

### Visual Hierarchy
- **Maximum 3 heading levels** in README
- **Use emoji sparingly** (1-2 per section max)
- **Break up text** with lists, code blocks, tables
- **White space matters** - don't create walls of text

## 🔧 Technical Guidelines

### Link Strategy
- **Internal links**: Use relative paths (`docs/guide.md`)
- **External links**: Open in new tab for tools/references
- **Link text**: Descriptive ("Installation Guide" not "click here")

### Image Guidelines
- **File size**: <500KB for README images
- **Alt text**: Always include for accessibility
- **Hosting**: Prefer repo-relative paths over external URLs
- **Format**: PNG for screenshots, SVG for diagrams, GIF for demos

### Code Examples
- **Test all code**: Every example must work as written
- **Include context**: Show directory, prerequisites
- **Expected output**: Show what success looks like
- **Error handling**: Mention common failure modes

## 🚨 Common Pitfalls to Avoid

### Content Mistakes
- ❌ **Feature lists without benefits**
- ❌ **Installation without prerequisites**
- ❌ **Code without context or output**
- ❌ **Links to non-existent documentation**
- ❌ **Outdated screenshots or examples**

### Structure Problems
- ❌ **Wall of text without headings**
- ❌ **Too many heading levels (H4, H5, H6)**
- ❌ **Important info buried at bottom**
- ❌ **No clear next steps**
- ❌ **Missing quick start path**

### Technical Issues
- ❌ **Broken internal links**
- ❌ **Untested code examples**
- ❌ **Missing prerequisites**
- ❌ **Platform-specific assumptions**
- ❌ **Outdated version numbers**

## 🎯 Success Metrics

A great README should achieve:
- **10-second hook** - Reader understands value immediately
- **2-minute quick start** - Basic functionality working
- **Clear next steps** - Reader knows where to go for more
- **Self-service support** - Common questions answered
- **Community building** - Encourages participation

## 📝 Templates by Type

### Project README (Main)
Use the full structure above with all sections.

### Module/Component README
```markdown
# Component Name

Brief description of this component's purpose within the larger system.

## Usage
[Quick example of how to use this component]

## API Reference
[Link to detailed docs]

## Related
- [Parent Project](../README.md)
- [Related Component](../other-component/README.md)
```

### Documentation Section README
```markdown
# Section Name

This section contains [type of documentation].

## Contents
- [Document 1](doc1.md) - Purpose
- [Document 2](doc2.md) - Purpose

## Quick Links
- [Getting Started](../getting-started/)
- [Main Project](../../README.md)
```

---

**Remember**: A README is a conversation starter, not a reference manual. Hook them, help them succeed quickly, then guide them to deeper resources. 