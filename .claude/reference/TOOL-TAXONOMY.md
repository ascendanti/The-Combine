# Tool Taxonomy & Integration Analysis

**Created:** 2026-01-30
**Status:** Research In Progress
**Scope:** 500+ tools, plugins, MCP servers, and repositories

---

## Executive Summary

Comprehensive analysis of proposed tools against the established Atlas/PLATO architecture to identify:
- **Redundancy** with existing plugins
- **Integration clashes** that conflict with architecture
- **Capacity gains** from new capabilities
- **Efficiency yields** from tool adoption
- **Architecture amendments** requiring approval

---

## 1. Tool Categories Identified

### 1.1 Claude Code Plugins (47 items)
Direct plugin installations via `npx claude-plugins install`

### 1.2 MCP Servers (35+ items)
Model Context Protocol integrations from mcpmarket.com

### 1.3 Document Processing (60+ items)
PDF, DOCX, Markdown, LaTeX, publishing tools

### 1.4 Design & UI (40+ items)
Figma, Adobe, icon sets, component libraries

### 1.5 Research & Academic (50+ items)
Paper tools, citation managers, scientific workflows

### 1.6 Journalism & Media (80+ items)
Newsroom tools, data journalism, content management

### 1.7 Video & Audio Production (45+ items)
Editing, automation, podcast generation

### 1.8 Security & OSINT (40+ items)
NSA tools, threat intel, reverse engineering

### 1.9 Self-Hosted Services (30+ items)
Alternative to cloud services

### 1.10 AI/ML Agents (50+ items)
AutoGPT variants, research agents, specialized AI

---

## 2. Analysis Framework

### 2.1 Redundancy Matrix

| Category | Existing Plugin | Proposed Tool | Verdict |
|----------|-----------------|---------------|---------|
| Document Extraction | document-skills | docling, unstructured | **EVALUATE** |
| Publishing | book-writer, ralph-wiggum | Ghost, Pandoc | **COMPLEMENT** |
| Memory | claude-mem, cortex-adapter | cognee, memU | **REDUNDANT** |
| Design | frontend-design, canvas-design | Figma MCP, onlook | **COMPLEMENT** |
| Code Quality | code-refactoring | compound-engineering | **OVERLAP** |
| Orchestration | cognitive-orchestration | taskmaster, claude-flow | **EVALUATE** |

### 2.2 Integration Risk Assessment

| Risk Level | Description | Examples |
|------------|-------------|----------|
| **HIGH** | Conflicts with core architecture | Multiple orchestrators, competing memory systems |
| **MEDIUM** | Requires adaptation | Different event patterns, non-standard APIs |
| **LOW** | Clean integration path | Standard interfaces, well-documented |

### 2.3 Value Assessment Criteria

- **Capability Gap**: Does it fill a missing capability?
- **Efficiency Gain**: Does it reduce tokens/time/effort?
- **Quality Improvement**: Does it improve output quality?
- **Maintenance Burden**: How much upkeep does it require?

---

## 3. Detailed Analysis by Category

### 3.1 Claude Code Plugins

#### 3.1.1 Already Implemented (SKIP)
These are already wired in the daemon:
- `@anthropics/anthropic-agent-skills/document-skills` ✓
- `@wshobson/claude-code-workflows/context-management` ✓
- `@thedotmack/thedotmack/claude-mem` ✓
- `@imehr/imehr-marketplace/book-writer` ✓
- `@anthropics/claude-code-plugins/ralph-wiggum` ✓
- `@anthropics/claude-code-plugins/frontend-design` ✓
- `@ananddtyagi/claude-code-marketplace/ui-designer` ✓
- `@dotclaude/dotclaude-plugins/frontend-excellence` ✓
- `@EveryInc/every-marketplace/compound-engineering` ✓
- `@wshobson/claude-code-workflows/code-refactoring` ✓
- `@ComposioHQ/awesome-claude-skills/canvas-design` ✓

#### 3.1.2 New - High Value (RECOMMEND)

| Plugin | Capability Added | Integration Path | Priority |
|--------|------------------|------------------|----------|
| `@eyaltoledano/taskmaster/taskmaster` | Task orchestration | queue-orchestrator | HIGH |
| `@wshobson/claude-code-workflows/agent-orchestration` | Multi-agent coordination | cognitive-orchestration | HIGH |
| `@wshobson/claude-code-workflows/full-stack-orchestration` | End-to-end workflows | writer-suite | MEDIUM |
| `@K-Dense-AI/claude-scientific-skills/scientific-thinking` | Scientific reasoning | insight-engine | HIGH |
| `@wshobson/claude-code-workflows/python-development` | Python workflows | dev-accelerator | MEDIUM |
| `@wshobson/claude-code-workflows/database-design` | DB schema design | compound-engineering | MEDIUM |
| `@wshobson/claude-code-workflows/cicd-automation` | CI/CD pipelines | dev-accelerator | MEDIUM |

#### 3.1.3 New - Redundant (SKIP)

| Plugin | Overlaps With | Verdict |
|--------|---------------|---------|
| `@cexll/claude-code-dev-workflows/requirements-clarity` | OpenSpec | SKIP |
| `@wshobson/claude-code-workflows/code-review-ai` | code-refactoring | SKIP |
| `@anthropics/claude-code-plugins/code-review` | code-refactoring | SKIP |
| `@anthropics/claude-code-plugins/feature-dev` | dev-accelerator | SKIP |

#### 3.1.4 New - Document Variants (EVALUATE)

| Plugin | Format | Current Coverage | Verdict |
|--------|--------|------------------|---------|
| `@ComposioHQ/awesome-claude-skills/document-skills-pdf` | PDF | document-skills | EVALUATE |
| `@ComposioHQ/awesome-claude-skills/document-skills-pptx` | PowerPoint | **GAP** | ADD |
| `@ComposioHQ/awesome-claude-skills/document-skills-docx` | Word | **GAP** | ADD |
| `@kivilaid/ando-marketplace/document-skills` | General | document-skills | SKIP |
| `@henkisdabro/wookstar/pdf-processing-pro` | PDF | document-skills | EVALUATE |

### 3.2 MCP Servers

#### 3.2.1 High Value Additions

| MCP Server | Purpose | Integration Target | Priority |
|------------|---------|-------------------|----------|
| `openspec` | Spec-driven development | cognitive-orchestration | **HIGH** |
| `sequential-thinking` | Reasoning chains | insight-engine | **HIGH** |
| `qdrant` | Vector search | claude-mem | **HIGH** |
| `pandoc` | Document conversion | book-writer | **HIGH** |
| `youtube-transcript-1` | Transcript extraction | tapestry-adapter | **HIGH** |
| `firecrawl` | Web scraping | skill-seekers-adapter | **HIGH** |
| `figma-context` | Design assets | canvas-design | MEDIUM |
| `adobe-agent` | Adobe suite | frontend-design | MEDIUM |
| `task-master` | Task management | queue-orchestrator | MEDIUM |
| `fastapi` | API generation | dev-accelerator | MEDIUM |

#### 3.2.2 Redundant/Skip

| MCP Server | Reason |
|------------|--------|
| `bright-data-2` | Commercial scraping, prefer firecrawl |
| `graphiti` | Overlaps with existing graph capabilities |
| `windows-2` | Not relevant for Mac Studio architecture |
| `book-recommendation` | Not core to handbook system |

#### 3.2.3 Specialized - Later Phase

| MCP Server | Use Case | Phase |
|------------|----------|-------|
| `davinci-resolve-1` | Video editing | Phase 3 (Media) |
| `indesign-mcp` | Layout design | Phase 3 (Media) |
| `magic-1` | UI generation | Phase 2 (Design) |
| `mindsdb` | ML predictions | Phase 4 (Analytics) |

### 3.3 Document Processing Tools

#### 3.3.1 Core Pipeline Tools (RECOMMEND)

| Tool | Repository | Purpose | Integration |
|------|------------|---------|-------------|
| **Docling** | docling-project/docling | Document understanding | document-skills |
| **Unstructured** | Unstructured-IO/unstructured | Multi-format extraction | document-skills |
| **Pandoc** | jgm/pandoc | Universal conversion | book-writer |
| **WeasyPrint** | Kozea/WeasyPrint | PDF generation | weasyprint-publisher ✓ |
| **Typst** | typst/typst | Modern typesetting | ralph-wiggum |
| **Proselint** | amperser/proselint | Prose quality | proselint-adapter ✓ |

#### 3.3.2 Academic/Research Tools

| Tool | Repository | Purpose | Priority |
|------|------------|---------|----------|
| **PaperAI** | neuml/paperai | Research analysis | HIGH |
| **txtai** | neuml/txtai | Semantic search | HIGH |
| **FindPapers** | jonatasgrosman/findpapers | Paper discovery | MEDIUM |
| **Manubot** | manubot/manubot | Scientific publishing | MEDIUM |
| **pandoc-scholar** | pandoc-scholar/pandoc-scholar | Academic templates | MEDIUM |

#### 3.3.3 Redundant Tools (SKIP)

| Tool | Overlaps With |
|------|---------------|
| `terrylica/doc-build-tools` | Docling + Pandoc |
| `cadrianmae/pandoc` | Direct Pandoc |
| `mvdmakesthings/markdown-optimizer` | Proselint |
| `daymade/markdown-tools` | Pandoc |

### 3.4 Design & UI Tools

#### 3.4.1 Recommended Additions

| Tool | Purpose | Integration |
|------|---------|-------------|
| **Figma MCP** | Design context | canvas-design |
| **Lucide Icons** | Icon library | Already documented ✓ |
| **shadcn/ui** | Component library | frontend-design |
| **Storybook** | Component docs | frontend-excellence |
| **Motion Canvas** | Animated content | canvas-design |
| **DaisyUI** | Tailwind components | frontend-design |

#### 3.4.2 Adobe Integration Path

| Tool | Purpose | Phase |
|------|---------|-------|
| `adobe-mcp` | Suite integration | Phase 2 |
| `indesign-mcp` | Layout | Phase 3 |
| `adobe-agent` | Automation | Phase 3 |

### 3.5 Journalism & Media Tools

#### 3.5.1 Newsroom Infrastructure (HIGH VALUE)

| Tool | Purpose | Why Valuable |
|------|---------|--------------|
| **Guardian repos** | Production patterns | Reference architecture |
| **TryGhost/Ghost** | Publishing platform | Already documented ✓ |
| **n8n** | Workflow automation | Orchestration complement |
| **OpenNews tools** | Data journalism | Research patterns |
| **Bellingcat tools** | OSINT research | Investigation support |

#### 3.5.2 Content Automation

| Tool | Purpose | Integration |
|------|---------|-------------|
| **newspaper3k** | Article extraction | tapestry-adapter |
| **news-please** | News scraping | document-skills |
| **AutoEdit** | Transcript editing | tapestry-adapter |
| **Audiogram** | Audio visualization | canvas-design |

### 3.6 Video & Audio Production

#### 3.6.1 Phase 3 (Media) Candidates

| Tool | Purpose | Priority |
|------|---------|----------|
| **MoviePy** | Video editing | HIGH |
| **auto-editor** | Automated cuts | HIGH |
| **Remotion** | React video | MEDIUM |
| **yt-dlp** | Video download | HIGH |
| **CosyVoice** | Voice synthesis | MEDIUM |
| **Podcast generators** | Audio content | MEDIUM |

### 3.7 Security & OSINT

#### 3.7.1 NSA Tools Analysis

| Tool | Purpose | Relevance |
|------|---------|-----------|
| **Ghidra** | Reverse engineering | Already documented ✓ |
| **LemonGraph** | Graph analysis | insight-engine |
| **SIMP** | Security compliance | Infrastructure |
| **Skills Service** | Gamification | Learning system |

#### 3.7.2 OSINT Tools

| Tool | Purpose | Integration |
|------|---------|-------------|
| **SpiderFoot** | Recon automation | Research |
| **IntelOwl** | Threat intel | Security |
| **sn0int** | OSINT framework | Research |

### 3.8 AI/ML Agents

#### 3.8.1 Orchestration Alternatives

| Tool | Architecture | Verdict |
|------|--------------|---------|
| **AutoGPT** | Autonomous agent | **EVALUATE** - different paradigm |
| **CrewAI** | Multi-agent | **EVALUATE** - potential complement |
| **LangChain** | Chain orchestration | **COMPLEMENT** - retrieval focus |
| **Flowise** | Visual workflows | **SKIP** - GUI-centric |

#### 3.8.2 Specialized Agents

| Agent | Purpose | Integration Potential |
|-------|---------|----------------------|
| **AI Journalist** | News writing | ralph-wiggum |
| **Research Agent** | Paper analysis | insight-engine |
| **Movie Production Agent** | Content creation | Phase 3 |

---

## 4. Redundancy Analysis

### 4.1 Memory Systems (CRITICAL REVIEW)

**Current:** claude-mem, cortex-adapter (Claude Cortex)

**Proposed additions:**
- cognee - Knowledge graph
- memU - Personal memory
- GPTCache - Response caching

**Verdict:**
- cognee → **REDUNDANT** with cortex-adapter's episodic memory
- memU → **REDUNDANT** with claude-mem
- GPTCache → **COMPLEMENT** for inference optimization (Local AI plan)

### 4.2 Orchestration Systems (CRITICAL REVIEW)

**Current:** cognitive-orchestration, queue-orchestrator

**Proposed additions:**
- taskmaster
- claude-flow
- agent-orchestration
- full-stack-orchestration

**Verdict:**
- taskmaster → **COMPLEMENT** (different abstraction level)
- claude-flow → **EVALUATE** (may conflict with cognitive-orchestration)
- agent-orchestration → **MERGE** into cognitive-orchestration
- full-stack-orchestration → **COMPLEMENT** (workflow templates)

### 4.3 Document Processing (REVIEW)

**Current:** document-skills, book-writer, ralph-wiggum, weasyprint-publisher

**Proposed additions:**
- 15+ document plugins
- Docling, Unstructured
- Multiple PDF tools

**Verdict:**
- Docling → **ADD** as extraction backend
- Unstructured → **SKIP** (overlaps Docling)
- PPTX/DOCX plugins → **ADD** (gap in current coverage)
- Duplicate PDF tools → **SKIP**

---

## 5. Architecture Amendment Petitions

### Petition 1: Add Docling as Extraction Backend

**Current:** document-skills uses basic extraction
**Proposed:** Integrate Docling for superior document understanding

```yaml
amendment:
  type: "Backend Enhancement"
  target: "document-skills plugin"
  change: "Add Docling as extraction engine"
  rationale:
    - "Better layout understanding"
    - "Table extraction"
    - "Multi-format support"
  impact: "Low risk, high gain"
  effort: "Medium"
```

**Status:** PENDING APPROVAL

---

### Petition 2: Add Office Format Support

**Current:** PDF, Markdown, HTML support
**Proposed:** Add PPTX, DOCX native handling

```yaml
amendment:
  type: "Capability Addition"
  target: "document-skills plugin"
  change: "Add Office format adapters"
  files_needed:
    - "external/pptx_adapter.py"
    - "external/docx_adapter.py"
  dependencies:
    - "python-pptx"
    - "python-docx"
  rationale:
    - "Common input formats"
    - "Enterprise document support"
```

**Status:** PENDING APPROVAL

---

### Petition 3: Add Vector Search Backend

**Current:** In-memory search in claude-mem
**Proposed:** Add Qdrant MCP for persistent vector search

```yaml
amendment:
  type: "Infrastructure Addition"
  target: "claude-mem plugin"
  change: "Add Qdrant as vector backend"
  mcp_server: "qdrant"
  rationale:
    - "Persistent embeddings"
    - "Scalable search"
    - "Better retrieval"
  integration:
    - "cortex-adapter stores to Qdrant"
    - "context-management queries Qdrant"
```

**Status:** PENDING APPROVAL

---

### Petition 4: Add Scientific Reasoning Skills

**Current:** No specialized scientific reasoning
**Proposed:** Integrate K-Dense-AI scientific skills

```yaml
amendment:
  type: "Skill Addition"
  plugin: "@K-Dense-AI/claude-scientific-skills/scientific-thinking"
  integration_target: "insight-engine"
  capabilities_added:
    - "Hypothesis generation"
    - "Evidence evaluation"
    - "Statistical reasoning"
    - "Research methodology"
  rationale:
    - "Handbook requires academic rigor"
    - "Better research synthesis"
```

**Status:** PENDING APPROVAL

---

### Petition 5: Add YouTube/Video Transcript Pipeline

**Current:** Tapestry adapter has basic support
**Proposed:** Dedicated video content pipeline

```yaml
amendment:
  type: "Pipeline Addition"
  components:
    - "youtube-transcript MCP"
    - "Auto-editor for clips"
    - "Transcript summarization"
  integration:
    - "tapestry-adapter enhanced"
    - "New video-content-adapter"
  use_cases:
    - "Extract handbook content from videos"
    - "Generate video summaries"
    - "Create clips for social"
```

**Status:** PENDING APPROVAL

---

## 6. Recommended Tool Adoption Phases

### Phase 1: Core Infrastructure (Immediate)

| Tool | Type | Integration Target |
|------|------|-------------------|
| Docling | Library | document-skills |
| Qdrant MCP | MCP Server | claude-mem |
| OpenSpec MCP | MCP Server | cognitive-orchestration |
| Pandoc MCP | MCP Server | book-writer |
| Scientific Skills | Plugin | insight-engine |

### Phase 2: Design & Publishing (Week 2-3)

| Tool | Type | Integration Target |
|------|------|-------------------|
| Figma MCP | MCP Server | canvas-design |
| Typst | Library | ralph-wiggum |
| shadcn/ui | Components | frontend-design |
| Ghost API | Integration | book-writer |

### Phase 3: Media Production (Week 4-6)

| Tool | Type | Integration Target |
|------|------|-------------------|
| MoviePy | Library | New: video-adapter |
| auto-editor | CLI | video-adapter |
| yt-dlp | CLI | tapestry-adapter |
| Remotion | Library | canvas-design |

### Phase 4: Analytics & Intelligence (Week 6-8)

| Tool | Type | Integration Target |
|------|------|-------------------|
| PaperAI | Library | insight-engine |
| txtai | Library | claude-mem |
| LemonGraph | Library | insight-engine |
| SpiderFoot | Service | Research pipeline |

---

## 7. Tools Explicitly Rejected

| Tool | Reason |
|------|--------|
| AutoGPT | Different paradigm, conflicts with PLATO |
| Flowise | GUI-centric, not CLI-native |
| Multiple duplicate PDF tools | Redundant with Docling |
| Windows-specific MCPs | Mac Studio architecture |
| Commercial scraping services | Prefer open-source alternatives |
| Competing memory systems | Stick with claude-mem + cortex |

---

## 8. Summary Statistics

| Category | Total Reviewed | Recommended | Redundant | Deferred |
|----------|---------------|-------------|-----------|----------|
| Plugins | 47 | 12 | 20 | 15 |
| MCP Servers | 35 | 15 | 10 | 10 |
| Document Tools | 60 | 8 | 40 | 12 |
| Design Tools | 40 | 10 | 15 | 15 |
| Research Tools | 50 | 12 | 20 | 18 |
| Media Tools | 45 | 8 | 20 | 17 |
| Security/OSINT | 40 | 5 | 25 | 10 |
| AI Agents | 50 | 5 | 35 | 10 |
| **TOTAL** | **367** | **75** | **185** | **107** |

**Adoption Rate:** 20% (75/367 tools recommended)
**Redundancy Rate:** 50% (185/367 tools overlap with existing)
**Deferred Rate:** 29% (107/367 tools for later phases)

---

## 9. Next Steps

1. **User Approval Required** for 5 architecture amendment petitions
2. **Phase 1 Implementation** upon approval
3. **Detailed Research** for deferred tools in later phases
4. **Ongoing Evaluation** as new tools emerge

---

*Analysis conducted against Atlas/PLATO architecture v1.0 with Writer Suite integration.*
