# Prompt engineering best practices (Anthropic-aligned)

Build reliable, high-quality prompts for Claude models by following these Anthropic-aligned guidelines. This guide distills Anthropic’s official prompt engineering resources and adapts them for MCP Server for Splunk.

## Core principles

- **Be explicit**: Clearly state goals, constraints, and desired output. Avoid vague asks.
- **Add context and motivation**: Explain why the behavior matters to improve alignment.
- **Use examples**: Provide small, relevant examples that mirror the desired behavior.
- **Control format**: Specify output schema and formatting (JSON, Markdown, XML, etc.).
- **Give a role**: Define the assistant’s persona to set tone and scope.
- **Let it think (without leaking chain-of-thought)**: Encourage careful reasoning steps internally; ask for brief justifications or structured outputs rather than raw chain-of-thought.
- **Prefer positive steering**: Tell the model what to do, not only what not to do.

See Anthropic docs: [Prompt engineering overview](https://docs.anthropic.com/en/docs/build-with-claude/prompt-engineering/overview), [Claude 4 best practices](https://docs.anthropic.com/en/docs/build-with-claude/prompt-engineering/claude-4-best-practices).

## Structuring prompts with XML tags

Claude pays strong attention to XML tag structure. Use tags to delineate sections clearly:

```text
<role>...</role>
<context>...</context>
<instructions>...</instructions>
<examples>...</examples>
<output_format>...</output_format>
<constraints>...</constraints>
```

Tips:

- **Match style to desired output**. If you want prose, keep the prompt prose-like.
- **Place instructions after large context** when using very long inputs (improves recall).

Reference: [Use XML tags](https://docs.anthropic.com/en/docs/build-with-claude/prompt-engineering/use-xml-tags), [Long context tips](https://docs.anthropic.com/en/docs/build-with-claude/prompt-engineering/long-context-tips).

## Reasoning and planning

- **Thinking guidance**: Encourage stepwise reasoning internally, e.g., “Plan your steps before answering.”
- **Interleaved thinking**: After tool calls, prompt reflection on results before next steps.
- **Prompt chaining**: Break complex tasks into smaller prompts; pass outputs forward.

Reference: [Extended thinking](https://docs.anthropic.com/en/docs/build-with-claude/extended-thinking), [Chain prompts](https://docs.anthropic.com/en/docs/build-with-claude/prompt-engineering/chain-prompts).

## Output control

- **Schemas**: Provide minimal schemas and validation cues (keys, types, allowed values).
- **Stop sequences**: Consider `stop_sequences` if your runtime uses them.
- **Prefill**: Seed the start of the answer to reduce chattiness if needed.
- **Allow uncertainty**: Permit “I don’t know” when context is insufficient.

Reference: [Be clear and direct](https://docs.anthropic.com/en/docs/build-with-claude/prompt-engineering/be-clear-and-direct), [Prefill](https://docs.anthropic.com/en/docs/build-with-claude/prompt-engineering/prefill-claudes-response).

## Agents and tools

- **Parallel tool calls**: Instruct parallelization for independent actions to improve speed.
- **Temporary files**: If files are created for iteration, clean them up at task end.

Reference: [Optimize parallel tool calling](https://docs.anthropic.com/en/docs/build-with-claude/prompt-engineering/claude-4-best-practices#optimize-parallel-tool-calling), [Reduce file creation](https://docs.anthropic.com/en/docs/build-with-claude/prompt-engineering/claude-4-best-practices#reduce-file-creation-in-agentic-coding).

## Frontend/code generation

- **Encourage ambition**: Ask for rich features and interactions explicitly.
- **List visual details**: Hover states, transitions, micro-interactions, design principles.
- **Avoid hard-coding for tests**: Emphasize general, maintainable solutions.

Reference: [Claude 4 best practices](https://docs.anthropic.com/en/docs/build-with-claude/prompt-engineering/claude-4-best-practices).

## Recommended prompt template

```text
<role>
You are an expert Splunk troubleshooting assistant integrated with MCP Server. You follow instructions precisely and produce safe, verifiable, and actionable outputs for Splunk workflows.
</role>

<context>
{optional_background_or_inputs}
</context>

<instructions>
- Be explicit, concise, and technically accurate.
- Use only the provided context; say "I don't know" if insufficient.
- Prefer parallel execution for independent steps.
- After tool results, reflect briefly before the next action.
</instructions>

<examples>
<example>
Input: short description of issue
Output: structured next steps and a Splunk SPL query
</example>
</examples>

<output_format>
Return Markdown with:
- Section: Assumptions (if any)
- Section: Plan (numbered)
- Section: Commands / SPL (fenced code with language tags)
- Section: Validation steps
</output_format>

<constraints>
- No secrets or PII.
- Avoid test-specific hard-coding.
</constraints>

## Quick checklist

- **Role set**: Clear persona and scope defined
- **Context added**: Relevant and minimal
- **Explicit instructions**: Positive, testable
- **Examples**: Relevant and safe
- **Format specified**: Schema or Markdown sections
- **Reasoning**: Guided without exposing chain-of-thought
- **Parallelization**: Encouraged where appropriate
- **Uncertainty**: Allowed and defined

## Sources

- Anthropic: [Prompt engineering overview](https://docs.anthropic.com/en/docs/build-with-claude/prompt-engineering/overview)
- Anthropic: [Claude 4 prompt engineering best practices](https://docs.anthropic.com/en/docs/build-with-claude/prompt-engineering/claude-4-best-practices)
- Anthropic: [Chain prompts](https://docs.anthropic.com/en/docs/build-with-claude/prompt-engineering/chain-prompts)
- Anthropic: [Use XML tags](https://docs.anthropic.com/en/docs/build-with-claude/prompt-engineering/use-xml-tags)
- Anthropic: [System prompts (roles)](https://docs.anthropic.com/en/docs/build-with-claude/prompt-engineering/system-prompts)
- Anthropic: [Prefill responses](https://docs.anthropic.com/en/docs/build-with-claude/prompt-engineering/prefill-claudes-response)
