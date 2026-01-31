# Document Processing Tools Reference

Reference implementations and libraries for the International Student Handbook document pipeline.

## PDF & Document Extraction

### MinerU (OpenDataLab)
**Repository:** https://github.com/opendatalab/MinerU.git
**Purpose:** High-quality PDF/document extraction with layout understanding
**Integration:** `document-skills` plugin - primary extraction engine
**Features:**
- Layout-aware extraction
- Table detection and extraction
- Formula recognition
- Multi-language support

### PDF-Extract-Kit (OpenDataLab)
**Repository:** https://github.com/opendatalab/PDF-Extract-Kit.git
**Purpose:** Comprehensive PDF extraction toolkit
**Integration:** `document-skills` plugin - supplementary extraction
**Features:**
- Text extraction with position info
- Image extraction
- Metadata extraction
- OCR integration

### Docling
**Repository:** https://github.com/docling-project/docling.git
**Purpose:** Document understanding and processing
**Integration:** `document-skills`, `book-writer` plugins
**Features:**
- Document structure analysis
- Semantic chunking
- Multi-format support

### Stirling-PDF
**Repository:** https://github.com/Stirling-Tools/Stirling-PDF
**Purpose:** PDF manipulation (merge, split, convert, OCR)
**Integration:** `document-skills` plugin - PDF operations
**Features:**
- Merge/split PDFs
- Convert to/from PDF
- Add watermarks
- OCR processing
- Form filling

### PaperDebugger (Main Project)
**Repository:** https://github.com/PaperDebugger/paperdebugger.git
**Purpose:** Academic paper debugging and analysis toolkit
**Integration:** `document-skills`, `book-writer` plugins
**Features:**
- Paper structure validation
- Citation verification
- Figure/table checking
- Logical flow analysis
- Academic writing quality checks

### PDFFigures2 (PaperDebugger)
**Repository:** https://github.com/PaperDebugger/pdffigures2.git
**Purpose:** Extract figures, tables, and captions from PDFs
**Integration:** `document-skills` plugin - figure extraction
**Features:**
- Figure detection and extraction
- Table detection
- Caption extraction
- Bounding box coordinates
- Academic paper optimized

### Science Result Extractor (IBM)
**Repository:** https://github.com/IBM/science-result-extractor.git
**Purpose:** Extract scientific results, claims, and findings from papers
**Integration:** `document-skills`, `book-writer` plugins - academic content extraction
**Features:**
- Scientific claim extraction
- Result/finding identification
- Evidence linking
- Structured data output
- NLP-powered analysis

### Claude Scientific Skills (K-Dense AI)
**Repository:** https://github.com/K-Dense-AI/claude-scientific-skills
**Related:** https://github.com/K-Dense-AI/claude-scientific-writer
**Purpose:** 140 ready-to-use scientific skills for Claude
**Stars:** 7.3k GitHub stars
**Integration:** `document-skills`, `compound-engineering`, `insight-engine` plugins
**Features:**
- 140 scientific skills across multiple domains
- Bioinformatics & Genomics (sequence analysis, RNA-seq)
- Chemistry (RDKit, molecular modeling)
- 55+ Python packages integrated
- One-click setup via Claude Code or MCP
- Auto-discovery (Claude finds relevant skills)

**Domains Covered:**
- Biology & Genomics
- Chemistry & Drug Discovery
- Medicine & Clinical Research
- Quantum Computing (PennyLane, Qiskit)
- Machine Learning (PyTorch Lightning, scikit-learn)

**Use Cases for Handbook:**
- Scientific content validation
- Research-backed content generation
- Data analysis for student outcomes
- Academic paper processing

## Writing Quality

### Proselint (Amperser)
**Repository:** https://github.com/amperser/proselint
**Purpose:** Linter for English prose - style and usage checker
**Integration:** `book-writer`, `ralph-wiggum` plugins
**Stars:** 4,500 GitHub stars
**Features:**
- 100+ writing issue detections
- Aggregates advice from renowned authors and style guides
- Configurable checks (enable/disable granularly)
- JSON and text output formats
- Editor integrations (Vim, Emacs, VS Code)
- Pre-commit hook support

**Checks For:**
- Clichés, archaic forms, malapropisms
- Corporate speak, bureaucratese, jargon
- Redundancy and weasel words
- Spelling consistency
- Mixed metaphors and oxymorons
- Social awareness (inclusive language)

**Use Cases for Handbook:**
- Automated prose quality checks
- Consistent writing style enforcement
- Pre-publish quality gates

## Document Conversion

### Pandoc
**Repository:** https://github.com/jgm/pandoc.git
**Purpose:** Universal document converter
**Integration:** `book-writer`, `ralph-wiggum` plugins
**Features:**
- 40+ input formats
- 60+ output formats
- Custom templates
- Citation processing
- Filters and Lua scripting

### Scrivomatic
**Repository:** https://github.com/iandol/scrivomatic.git
**Purpose:** Scrivener to Pandoc workflow automation
**Integration:** `book-writer` plugin - authoring workflow
**Features:**
- Scrivener integration
- Academic writing workflow
- Citation management
- Multi-output publishing

### Quarkdown
**Repository:** https://github.com/iamgio/quarkdown
**Purpose:** Markdown with superpowers - papers, presentations, books, knowledge bases
**Integration:** `book-writer`, `ralph-wiggum` plugins - advanced authoring
**Features:**
- Extended Markdown syntax (CommonMark + GFM + functions)
- Built-in scripting (variables, conditionals, loops)
- Standard library (layout, I/O, math)
- Multi-output: PDF, HTML, slides, books
- Live preview & VS Code extension
- Custom function/library support
- Knowledge base linking
- Fast compilation

**Use Cases for Handbook:**
- Write handbook chapters with dynamic content
- Generate multiple output formats from single source
- Create interactive presentations for orientation
- Build navigable knowledge base for students

## Publishing Platforms

### Ghost
**Repository:** https://github.com/TryGhost/Ghost
**CLI:** https://github.com/TryGhost/Ghost-CLI
**Purpose:** Professional publishing platform (headless CMS)
**Integration:** `book-writer`, `ralph-wiggum`, `frontend-design` plugins
**Features:**
- Modern publishing workflow
- Headless CMS with API
- Newsletter/membership support
- SEO optimized
- Markdown-native editing
- Theme system (Handlebars)
- Content API for custom frontends

**Ghost-CLI Features:**
- One-command install/update
- SSL certificate management
- Nginx configuration
- Systemd service setup
- Multi-environment support (local/production)
- Backup and migration tools

**Use Cases for Handbook:**
- Host handbook as Ghost publication
- API-driven content delivery
- Member-only content sections
- Newsletter updates to students
- Multi-author collaboration

## PDF Generation

### WeasyPrint
**Repository:** https://github.com/Kozea/WeasyPrint.git
**Samples:** https://github.com/CourtBouillon/weasyprint-samples.git
**Purpose:** HTML/CSS to PDF rendering (Python)
**Integration:** `weasyprint-publisher` plugin (implemented)
**Features:**
- CSS Paged Media support
- Professional print quality
- @page rules
- Headers/footers

### Paged.js
**Repository:** https://github.com/pagedjs/pagedjs
**CLI:** https://github.com/pagedjs/pagedjs-cli
**Purpose:** Paginated media in the browser (JavaScript)
**Integration:** `frontend-design`, `weasyprint-publisher` plugins
**Features:**
- W3C Paged Media spec implementation
- CSS-based print layouts
- Running headers/footers
- Page breaks, margins, bleeds
- Table of contents generation
- Footnotes and endnotes
- Cross-references
- Browser-based (no server needed)
- PDF export via browser print

**Paged.js CLI Features:**
- Headless PDF generation (Puppeteer-based)
- Command-line batch processing
- CI/CD pipeline integration
- No browser UI needed
- Automation-friendly

**Advantages over WeasyPrint:**
- Runs in browser (client-side) OR headless (CLI)
- Visual preview before print
- Interactive design workflow
- Same rendering engine for preview & export

**Use Cases for Handbook:**
- Browser-based PDF preview
- Automated PDF generation (via CLI)
- Print stylesheet development
- CI/CD handbook builds

### OpenPDF
**Repository:** https://github.com/LibrePDF/OpenPDF.git
**Purpose:** Java PDF library (iText fork)
**Integration:** Potential Java-based PDF operations
**Features:**
- PDF creation/manipulation
- Digital signatures
- Form handling
- Open source (LGPL/MPL)

## RAG & Retrieval

### Nucleoid (Neuro-Symbolic AI)
**Repository:** https://github.com/NucleoidAI/Nucleoid
**Website:** https://nucleoid.ai/
**Purpose:** Declarative runtime for Neuro-Symbolic AI with Knowledge Graph
**Integration:** `claude-mem`, `insight-engine`, `adaptive-learning` plugins
**Features:**
- Logic Graph (knowledge graph for logic + data)
- Adaptive reasoning with contextual information
- Declarative ES6 syntax
- Built-in datastore
- Explainable AI decisions
- Low-code API development

**Use Cases for Handbook:**
- Knowledge base for handbook content
- Reasoning about student requirements
- Adaptive content recommendations
- Explainable content decisions
- Logic-based content relationships

**Example:**
```javascript
// Declarative logic for handbook
class Student {
  visa_type: string;
  enrollment_status: string;
}

// Rule: F-1 students need work authorization
if (student.visa_type === 'F-1' && student.wants_employment) {
  student.needs_cpt_or_opt = true;
}
```

### RAGFlow
**Repository:** https://github.com/infiniflow/ragflow.git
**Purpose:** RAG workflow orchestration
**Integration:** `claude-mem`, `context-management` plugins
**Features:**
- Document chunking strategies
- Vector store integration
- Retrieval pipelines
- Citation tracking

## Development Workflow

### Claude CodePro (maxritter)
**Repository:** https://github.com/maxritter/claude-codepro
**Purpose:** Production-grade development environment for Claude Code
**Integration:** `dev-accelerator`, `cognitive-orchestration` plugins
**Stars:** 421 GitHub stars
**Features:**
- Spec-Driven Development: Plan → Approve → Implement → Verify cycle
- TDD Enforcement via pre-edit hooks (tests before code)
- Persistent Memory for cross-session knowledge retention
- Semantic Search (local vector-based code search)
- Quality Hooks for Python, TypeScript, Go
- Endless Mode with automatic session handoffs
- Modular System (customizable rules, commands, skills)

**Use Cases for Handbook:**
- Quality automation for plugin development
- Session continuity for long-running handbook tasks
- Token-efficient code retrieval via semantic search
- TDD enforcement for code changes
- Structured development workflow

### Claude Cortex (mkdelta221)
**Repository:** https://github.com/mkdelta221/claude-cortex
**Purpose:** Brain-like memory system for Claude Code
**Integration:** `claude-mem`, `adaptive-learning` plugins
**Stars:** 38 GitHub stars
**Features:**
- Short-term memory (session-level, high detail, fast decay)
- Long-term memory (persistent across sessions)
- Episodic memory with automatic salience detection
- PreCompact hook for memory extraction before context compaction
- Temporal decay and reinforcement (memories fade but strengthen with access)
- Semantic search and filtering across memory types
- 3D brain visualization dashboard
- Multi-platform service auto-start (macOS, Linux, Windows)

**Use Cases for Handbook:**
- Persistent memory for handbook content across sessions
- Context window management for large documents
- Automatic knowledge extraction during compaction

### Agentic Context Engine (Kayba AI)
**Repository:** https://github.com/kayba-ai/agentic-context-engine
**Purpose:** Self-improving AI agents through experience-based learning
**Integration:** `adaptive-learning`, `insight-engine` plugins
**Stars:** 1,800 GitHub stars
**Features:**
- Self-improving agents that learn from execution feedback
- 20-35% performance improvements on complex tasks
- 49% token reduction in browser automation
- Three specialized roles: Agent, Reflector, SkillManager
- Evolving "Skillbook" capturing strategies and failure patterns
- No fine-tuning required
- LangChain, browser-use, Claude Code, LiteLLM integration

**Use Cases for Handbook:**
- Learn from handbook generation iterations
- Optimize token usage over time
- Capture successful content strategies

### Agentic Rules (AINative Studio)
**Repository:** https://github.com/AINative-Studio/agentic-rules
**Purpose:** Machine-readable development standards for AI-assisted XP workflows
**Integration:** `dev-accelerator`, `cognitive-orchestration` plugins
**Stars:** 8 GitHub stars
**Features:**
- Rule documents for backlog, branching, TDD/BDD, CI/CD
- Claude Code templates with placeholder syntax
- MCP integration for GitHub issue management
- HyperScaler deployment guides (AWS, Azure, GCP)
- Pre-built slash commands for TDD, PRs, code reviews
- Agentic prompts library
- 25 specialized agent personas

**Use Cases for Handbook:**
- Standardized development workflows
- Automated GitHub issue classification
- CI/CD pipeline templates

### Skill Seekers (yusufkaraaslan)
**Repository:** https://github.com/yusufkaraaslan/Skill_Seekers
**Purpose:** Auto-convert docs, repos, PDFs into Claude skills
**Integration:** `document-skills`, `dev-accelerator` plugins
**Stars:** 8,500 GitHub stars
**Features:**
- Multi-source scraping (docs, GitHub, PDFs, llms.txt)
- Deep AST parsing for multiple languages
- Conflict detection (docs vs actual code)
- Three-stream GitHub analysis (Code, Docs, Insights)
- Multi-LLM support (Claude, Gemini, OpenAI)
- Smart rate limit management
- Resume capability for interrupted jobs
- MCP integration

**Use Cases for Handbook:**
- Convert handbook docs into Claude skills
- Analyze handbook codebase for skill generation
- Detect documentation drift

### Tapestry Skills (michalparkola)
**Repository:** https://github.com/michalparkola/tapestry-skills-for-claude-code
**Purpose:** Productivity skills for content extraction and action planning
**Integration:** `book-writer`, `document-skills` plugins
**Stars:** 194 GitHub stars
**Features:**
- Unified Tapestry workflow orchestration
- YouTube transcript downloader with deduplication
- Article extractor (removes ads/clutter)
- Ship-Learn-Next action planner
- "DOING over studying" with 5-rep implementation frameworks

**Use Cases for Handbook:**
- Extract content from video tutorials
- Convert articles to handbook content
- Action-oriented learning plans for students

### Content Research Writer (ComposioHQ)
**Repository:** https://github.com/ComposioHQ/awesome-claude-skills
**Path:** `content-research-writer/SKILL.md`
**Purpose:** Collaborative writing assistant with research and citations
**Integration:** `book-writer`, `ralph-wiggum` plugins
**Install:** `npx claude-plugins install @ComposioHQ/awesome-claude-skills/content-research-writer`
**Features:**
- Collaborative outlining and structure development
- Research assistance with source identification
- Citation management (inline, numbered, footnotes)
- Hook improvement with multiple alternatives
- Section-by-section feedback during writing
- Voice preservation and style matching
- Pre-publish quality checklist

**Triggers:**
- Writing blog posts, articles, newsletters
- Creating educational content or tutorials
- Drafting thought leadership pieces
- Research and case studies
- Technical documentation with sources

**Use Cases for Handbook:**
- Research-backed handbook chapters
- Proper citation management
- Iterative content refinement
- Consistent voice across chapters

### OpenSpec (Fission AI)
**Repository:** https://github.com/Fission-AI/OpenSpec
**Purpose:** Spec-Driven Development (SDD) for AI coding assistants
**Integration:** `cognitive-orchestration`, `dev-accelerator` plugins
**Stars:** 18.8k GitHub stars
**Features:**
- "Agree before you build" - spec alignment before code
- Action-based workflow with artifact tracking
- Works with 20+ AI assistants via slash commands
- Per-project configuration
- Proposal → specs → design → tasks workflow
- Artifact graph tracks state automatically

**Use Cases for Handbook:**
- Document handbook chapter specifications
- Coordinate AI-assisted content development
- Track handbook artifacts (chapters, designs, assets)
- Structured development workflow for plugins

**Workflow:**
```
openspec init                    # Initialize project
openspec propose "Add chapter"   # Create proposal
openspec spec                    # Generate specifications
openspec design                  # Create design artifacts
openspec tasks                   # Generate task list
```

## Reverse Engineering & Code Analysis

### Ghidra (NSA)
**Repository:** https://github.com/NationalSecurityAgency/ghidra.git
**Purpose:** Software reverse engineering framework
**Integration:** `compound-engineering` plugin - binary analysis
**Features:**
- Disassembly and decompilation
- Multi-architecture support (x86, ARM, MIPS, etc.)
- Scripting (Java, Python)
- Collaborative analysis
- Extensible plugin system

### GhidraMCP
**Repository:** https://github.com/LaurieWired/GhidraMCP.git
**MCP Server:** https://mcpmarket.com/server/ghidra-1
**Purpose:** MCP integration for Ghidra
**Integration:** Via MCP - enables Claude to analyze binaries
**Features:**
- Binary analysis via Claude
- Decompilation queries
- Function analysis
- Repository onboarding (study existing software)
- Understand compiled code structure

## Visual Assets

### Lucide Icons
**Repository:** https://github.com/lucide-icons/lucide.git
**Purpose:** Beautiful & consistent icon set
**Integration:** `canvas-design`, `frontend-design` plugins
**Features:**
- 1000+ icons
- SVG format
- Customizable (stroke, size)
- Tree-shakeable

---

## Integration Matrix

| Tool | Plugin | Use Case |
|------|--------|----------|
| MinerU | document-skills | PDF extraction |
| PDF-Extract-Kit | document-skills | Layout analysis |
| Docling | document-skills | Structure understanding |
| Stirling-PDF | document-skills | PDF operations |
| PaperDebugger | document-skills, book-writer | Academic analysis |
| PDFFigures2 | document-skills | Figure extraction |
| Science Result Extractor | document-skills, book-writer | Scientific claims |
| Pandoc | book-writer, ralph-wiggum | Format conversion |
| Scrivomatic | book-writer | Authoring workflow |
| Quarkdown | book-writer, ralph-wiggum | Markdown with superpowers |
| Ghost | book-writer, ralph-wiggum, frontend-design | Publishing platform |
| WeasyPrint | weasyprint-publisher | PDF generation (Python) |
| Paged.js | frontend-design, weasyprint-publisher | PDF generation (JS/browser) |
| OpenPDF | (future) | Java PDF ops |
| Nucleoid | claude-mem, insight-engine, adaptive-learning | Neuro-Symbolic AI |
| RAGFlow | claude-mem, context-management | Retrieval |
| Lucide | canvas-design, frontend-design | Icons |
| OpenSpec | cognitive-orchestration, dev-accelerator | Spec-driven development |
| Claude CodePro | dev-accelerator, cognitive-orchestration | Production dev environment |
| Claude Cortex | claude-mem, adaptive-learning | Brain-like memory system |
| Agentic Context Engine | adaptive-learning, insight-engine | Self-improving agents |
| Agentic Rules | dev-accelerator, cognitive-orchestration | XP workflow standards |
| Skill Seekers | document-skills, dev-accelerator | Docs-to-skills converter |
| Tapestry Skills | book-writer, document-skills | Content extraction |
| Content Research Writer | book-writer, ralph-wiggum | Research & citations |
| Proselint | book-writer, ralph-wiggum | Prose linting |
| Ghidra | compound-engineering | Binary analysis |
| GhidraMCP | compound-engineering | MCP binary analysis |
| Claude Scientific Skills | document-skills, compound-engineering, insight-engine | Scientific analysis |
| Nucleoid | claude-mem, insight-engine, adaptive-learning | Neuro-Symbolic AI |

## MCP Server Integration

| MCP Server | Plugin | Use Case |
|------------|--------|----------|
| claude-context | context-management | Codebase context |
| claude-gateway | context-management | Dynamic loading |
| ultrarag | claude-mem, context-management | RAG retrieval |
| basic-memory | claude-mem | Persistent storage |
| paper-debugger | document-skills, book-writer | Academic analysis |
| ghidra-1 | compound-engineering | Binary reverse engineering |

## Installation Notes

### Python Tools
```bash
# MinerU
pip install magic-pdf

# Docling
pip install docling

# WeasyPrint (Python)
pip install weasyprint

# Paged.js (JavaScript/Browser)
npm install pagedjs
# Or via CDN:
# <script src="https://unpkg.com/pagedjs/dist/paged.polyfill.js"></script>

# Paged.js CLI (headless PDF generation)
npm install -g pagedjs-cli
# Usage:
pagedjs-cli index.html -o handbook.pdf
pagedjs-cli https://handbook.example.com -o handbook.pdf

# RAGFlow (Docker recommended)
docker pull infiniflow/ragflow

# PaperDebugger
pip install paperdebugger
# Or from source:
git clone https://github.com/PaperDebugger/paperdebugger.git
cd paperdebugger && pip install -e .

# PDFFigures2 (requires Java)
git clone https://github.com/PaperDebugger/pdffigures2.git
cd pdffigures2 && sbt assembly

# IBM Science Result Extractor
git clone https://github.com/IBM/science-result-extractor.git
cd science-result-extractor && pip install -r requirements.txt

# Claude Scientific Skills (one-click setup)
# Via Claude Code MCP:
claude mcp add claude-scientific-skills -- uvx claude-scientific-skills
# Or manual:
pip install claude-scientific-skills
```

### Writing Quality Tools
```bash
# Proselint
pip install proselint
# Usage: proselint document.md
# Pre-commit: proselint --json document.md
```

### Development Tools
```bash
# Claude CodePro
git clone https://github.com/maxritter/claude-codepro.git
# Follow setup in README for .claude/ directory structure

# Claude Cortex (memory system)
git clone https://github.com/mkdelta221/claude-cortex.git
cd claude-cortex && pip install -e .
# Auto-start services included for macOS/Linux/Windows

# Agentic Context Engine
pip install agentic-context-engine
# Or: git clone https://github.com/kayba-ai/agentic-context-engine.git

# Skill Seekers (docs-to-skills)
git clone https://github.com/yusufkaraaslan/Skill_Seekers.git
cd Skill_Seekers && pip install -r requirements.txt

# Tapestry Skills
git clone https://github.com/michalparkola/tapestry-skills-for-claude-code.git
# Copy skills to .claude/skills/
```

### System Tools
```bash
# Pandoc (Windows)
winget install pandoc

# Quarkdown (requires Java 17+)
# macOS:
brew install iamgio/tap/quarkdown
# Windows:
scoop bucket add iamgio https://github.com/iamgio/scoop-bucket
scoop install quarkdown
# Create new project:
quarkdown create my-handbook

# Stirling-PDF (Docker)
docker pull frooodle/s-pdf

# Lucide Icons (npm)
npm install lucide-react  # For React
npm install lucide        # For vanilla JS

# Ghost CMS (via Ghost-CLI)
# https://github.com/TryGhost/Ghost-CLI
npm install ghost-cli@latest -g
ghost install local      # Local development
ghost install            # Production (requires Ubuntu/Debian)
ghost start / stop       # Manage instance
ghost update             # Update Ghost
ghost backup             # Create backup

# Or Docker:
docker pull ghost:latest
docker run -d -p 2368:2368 ghost

# Nucleoid (Neuro-Symbolic AI)
npm install nucleoidai
# Or Docker:
docker pull nucleoid/nucleoid
```

### MCP Servers
```bash
# PaperDebugger MCP
git clone https://github.com/PaperDebugger/paperdebugger-mcp.git
cd paperdebugger-mcp && npm install

# GhidraMCP (requires Ghidra installed)
git clone https://github.com/LaurieWired/GhidraMCP.git
cd GhidraMCP && pip install -r requirements.txt
```

### Reverse Engineering
```bash
# Ghidra (requires JDK 17+)
# Download from: https://ghidra-sre.org/
# Or clone and build:
git clone https://github.com/NationalSecurityAgency/ghidra.git
cd ghidra && gradle buildGhidra

# Windows (via winget)
winget install NSA.Ghidra
```

---

*WIRED: 2026-01-30 - International Student Handbook Plugin System*

---

## Related Documentation

- **[TOOL-TAXONOMY.md](./TOOL-TAXONOMY.md)** - Comprehensive analysis of 500+ tools, redundancy matrix, and architecture amendment petitions
- **[ARCHITECTURE.md](./ARCHITECTURE.md)** - PLATO system architecture
- **[MCP-INTEGRATION.md](./MCP-INTEGRATION.md)** - MCP server integration guide
