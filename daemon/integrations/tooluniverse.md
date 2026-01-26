# Integration Analysis: ToolUniverse

**Source:** https://github.com/mims-harvard/ToolUniverse
**Status:** Integrated
**Priority:** High
**Date:** 2026-01-26

## Overview

ToolUniverse from Harvard MIMS is an ecosystem for creating AI scientist systems. It provides 700+ scientific tools including ML models, datasets, APIs, and scientific packages for data analysis, knowledge retrieval, and experimental design.

## Key Features

### 1. AI-Tool Interaction Protocol
Standardized interface for how LLMs identify and call tools.

### 2. 700+ Scientific Tools
Categories include:
- Bioinformatics (UniProt, BLAST, PDB)
- Drug Discovery (FDA, DrugBank, OpenTargets)
- Genomics (GnomAD, ClinVar, Ensembl)
- Literature (PubMed, arXiv, Europe PMC)
- Chemistry (RDKit, ChEMBL, CompTox)
- Proteomics (AlphaFold, InterPro)

### 3. MCP Support
Native Model Context Protocol integration:
```bash
# Launch MCP server
tooluniverse-smcp
```

### 4. Multiple Calling Methods
```python
from tooluniverse import ToolUniverse
tu = ToolUniverse()
tu.load_tools()

# Method 1: Direct function-style
result = tu.tools.UniProt_get_entry_by_accession(accession="P05067")

# Method 2: JSON-based
result = tu.run_one_function({
    "name": "UniProt_get_entry_by_accession",
    "arguments": {"accession": "P05067"}
})

# Method 3: Tool discovery
tools = tu.run({
    "name": "Tool_Finder_Keyword",
    "arguments": {"description": "protein structure", "limit": 10}
})
```

### 5. Tool Composition & Workflows
Chain tools for sequential or parallel execution in scientific workflows.

### 6. Hooks System
Intelligent output processing with:
- File Save Hook
- Summarization Hook
- Server Stdio Hooks

### 7. Caching
Built-in caching for repeated calls:
```python
result = tu.tools.UniProt_get_entry_by_accession(
    accession="P05067",
    use_cache=True
)
```

## Integration Points

### MCP Server Configuration
```json
{
  "mcpServers": {
    "tooluniverse": {
      "command": "uv",
      "args": [
        "--directory", "/path/to/tooluniverse-env",
        "run", "tooluniverse-smcp-stdio"
      ]
    }
  }
}
```

### Python SDK Integration
```python
# Install
pip install tooluniverse

# Usage
from tooluniverse import ToolUniverse
tu = ToolUniverse()
tu.load_tools()  # Load 700+ tools
```

### Tool Discovery Integration
Can be integrated with our deterministic router for tool selection.

## Adopted Patterns

1. **MCP Server** - Add to mcp.json for scientific tools access
2. **Tool Discovery** - Use Tool_Finder_Keyword for dynamic tool selection
3. **Caching Pattern** - Adopt their caching approach for API calls
4. **Hooks System** - Reference for output processing hooks

## Files Copied

```
.claude/reference/tooluniverse/
├── MCP_for_Claude.md        # MCP integration guide
├── function_calling.py      # Calling examples
└── tool_list.txt            # Available tools reference
```

## Use Cases for Our Architecture

### Scientific Research
- Drug target identification
- Protein structure prediction
- Literature search and analysis
- Clinical trial data

### Data Analysis
- Genomic variant analysis
- Chemical property calculation
- Pathway analysis

### Knowledge Retrieval
- Cross-database entity resolution
- Citation network analysis
- Expert feedback integration

## Implementation Notes

### Adding to MCP Configuration
```json
// In .claude/mcp.json or settings.local.json
{
  "enabledMcpjsonServers": [
    "tooluniverse"
  ]
}
```

### Tool Selection via Router
```python
# Extend deterministic_router.py
SCIENTIFIC_TOOLS = {
    'protein': 'UniProt_*',
    'drug': 'FDA_*|DrugBank_*',
    'genomics': 'GnomAD_*|ClinVar_*',
    'literature': 'PubMed_*|arXiv_*',
}
```

## Quality Assessment

| Aspect | Rating | Notes |
|--------|--------|-------|
| Code Quality | A | Well-documented, typed |
| Documentation | A+ | Comprehensive tutorials |
| Tool Coverage | A+ | 700+ scientific tools |
| MCP Support | A | Native integration |
| Maintainability | A | Active Harvard team |

## Related Work

- TxAgent: AI Agent for Therapeutic Reasoning (uses ToolUniverse)
- Hypercholesterolemia Drug Discovery Tutorial

## Next Steps

1. Add tooluniverse MCP server to configuration
2. Create scientific research agent using ToolUniverse tools
3. Integrate Tool_Finder into deterministic router
4. Set up caching for frequently used tools
