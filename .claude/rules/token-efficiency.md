# Token Efficiency Rules

## Parallel Agents by Default

When spawning multiple agents, ALWAYS use parallel execution unless there are explicit dependencies:

```python
# GOOD - Parallel
Task([agent1, agent2, agent3])  # Single message, multiple agents

# BAD - Sequential (unnecessary)
Task(agent1)  # wait
Task(agent2)  # wait
Task(agent3)  # wait
```

## Code Compactness

- No verbose comments
- No redundant docstrings
- Minimal boilerplate
- Prefer composition over inheritance
- One file = one purpose

## Memory Over Context

- Store learnings in OpenMemory instead of repeating in context
- Use handoffs instead of re-explaining
- Reference files by path, don't paste contents

## Agent Selection

| Task Type | Agent | Model |
|-----------|-------|-------|
| Simple search | scout | sonnet |
| Implementation | kraken | inherit |
| Research | oracle | inherit |
| Quick fix | spark | inherit |

Never use Haiku. Default: inherit parent model.

## Output Compression

- Summaries over full outputs
- Tables over prose
- Bullets over paragraphs
- Code snippets over full files
