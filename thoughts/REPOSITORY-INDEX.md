# Repository Index

Curated list of repositories shared by user for integration consideration.

## Priority: LocalAI Stack (Token Reduction)

| Repository | Purpose | Priority |
|------------|---------|----------|
| https://github.com/mudler/LocalAI | Local LLM inference, OpenAI-compatible API | HIGH |
| https://github.com/mudler/LocalAGI | Autonomous agent framework on LocalAI | HIGH |
| https://github.com/mudler/LocalRecall | Semantic memory/recall for LocalAI | HIGH |

**Rationale:** Combined stack could offload token-heavy operations (research ingestion, embeddings, bulk processing) to local models, reserving Claude for high-value reasoning.

---

## Document Ingestion & RAG

| Repository | Focus | Notes |
|------------|-------|-------|
| https://github.com/docling-project/docling | PDF/doc parsing, layout, tables, formulas | Copilot recommended |
| https://github.com/jerryjliu/llama_index | Knowledge indices, graph/tree indexing | Token-efficient retrieval |
| https://github.com/deepset-ai/haystack | Document QA pipelines | Production-ready |
| https://github.com/Future-House/paper-qa | Academic paper ingestion | Section-aware chunking |
| https://github.com/Future-House/robin | Academic assistant | Same org as PaperQA |
| https://github.com/adithya-s-k/omniparse | Unstructured data parsing | RAG-ready |
| https://github.com/OneOffTech/awesome-pdf | PDF tools curation | Reference list |

---

## Semantic & Knowledge Graphs

| Repository | Focus | Notes |
|------------|-------|-------|
| https://github.com/oraios/serena | Semantic retrieval | Compare with LocalRecall |
| https://github.com/shaneholloman/mcp-knowledge-graph | Local knowledge graphs | MCP compatible? |
| https://github.com/ballred/obsidian-claude-pkm | Obsidian knowledge graphs | PKM integration |
| https://github.com/Wildcard-Official/deepcontext-mcp | Deep context MCP | Promising |
| https://github.com/OpenBMB/UltraRAG | Efficient RAG | Token optimization focus |

---

## Skills & Agent Frameworks

| Repository | Focus | Notes |
|------------|-------|-------|
| https://github.com/wshobson/agents | Lazy-load skills | Load when activated, not all at once |
| https://github.com/vanzan01/claude-code-sub-agent-collective | Sub-agent patterns | Collective approach |
| https://github.com/OneWave-AI/claude-skills | Skill library | Qualify performance before ingest |
| https://github.com/ComposioHQ/awesome-claude-skills | Skill curation | Reference list |
| https://github.com/oxygen-fragment/claude-modular | Modular architecture | Promising |
| https://github.com/zechenzhangAGI/AI-research-SKILLs | Research skills | Promising |

---

## Browser & Desktop Automation

| Repository | Focus | Notes |
|------------|-------|-------|
| https://github.com/browser-use/browser-use | Browser automation | Web interaction |
| https://github.com/slopus/happy | Use from anywhere | Universal access |
| https://github.com/khoj-ai/khoj | Personal AI | Promising |

---

## Specialty: Finance

| Repository | Focus | Notes |
|------------|-------|-------|
| https://github.com/quant-sentiment-ai/claude-equity-research | Equity research | Combine with Princeton quant |

---

## Specialty: Content/Publishing

| Repository | Focus | Notes |
|------------|-------|-------|
| https://github.com/TheCraigHewitt/seomachine | SEO automation | Potentially profitable |
| https://github.com/jamditis/claude-skills-journalism | Journalism skills | Public impact/PR |
| https://github.com/fracabu/claude-kdp-agents | KDP publishing | Publishing module |

---

## Personal Modules (Future)

| Repository | Focus | Notes |
|------------|-------|-------|
| https://github.com/palimondo/BookMinder | Book management | Personal module |
| https://github.com/nige-n15/AI-book-buddy | Book ingestion | Compare with LocalRecall |

---

## Database & Query

| Repository | Focus | Notes |
|------------|-------|-------|
| https://github.com/bytebase/dbhub | Database capabilities | No semantic PDF search |
| https://github.com/julien040/anyquery | Universal query | Promising |
| https://github.com/microsoft/ContextualSP | Text-to-SQL | Interesting models |
| https://github.com/jkkummerfeld/text2sql-data | Text-to-SQL data | Academic |
| https://github.com/BaeSeulki/NL2LF | NL to logical form | Potential benefit |
| https://github.com/xlang-ai/UnifiedSKG | Unified SKG | Has promise |

---

## NLP & Comprehension

| Repository | Focus | Notes |
|------------|-------|-------|
| https://github.com/explosion/spaCy | Industrial NLP | Production-ready |
| https://github.com/sebastianruder/NLP-progress | NLP developments | Stay current |
| https://github.com/microsoft/nlp-recipes | NLP patterns | Reference |
| https://github.com/CLUEbenchmark/CLUEDatasetSearch | Reading comprehension | ML benchmarks |
| https://github.com/thunlp/RCPapers | RC papers | Must-read list |

---

## Vision & Analytics

| Repository | Focus | Notes |
|------------|-------|-------|
| https://github.com/ultralytics/ultralytics | YOLO object detection | Advanced analytics |
| https://github.com/ultralytics/yolov5 | YOLOv5 | Comparison |
| https://github.com/roboflow/supervision | Vision supervision | Plugs into ultralytics |
| https://github.com/open-mmlab/mmdetection | Detection framework | Future: webcam/robot |

---

## Anthropic Official

| Repository | Purpose |
|------------|---------|
| https://github.com/anthropics/skills | Official skills |
| https://github.com/anthropics/claude-cookbooks | Patterns |
| https://github.com/anthropics/claude-code-action | GitHub Actions |
| https://github.com/anthropics/claude-ai-mcp | MCP reference |
| https://github.com/anthropics/anthropic-retrieval-demo | Retrieval patterns |
| https://github.com/anthropics/claude-code-monitoring-guide | Monitoring |
| https://github.com/anthropics/evals | Evaluation |
| https://github.com/anthropics/prompt-eng-interactive-tutorial | Prompt engineering |
| https://github.com/anthropics/toy-models-of-superposition | Research |
| https://github.com/anthropics/anthropic-tools | Tools |
| https://github.com/anthropics/claude-quickstarts | Quickstarts |
| https://github.com/anthropics/claude-plugins-official | Plugins |
| https://github.com/anthropics/httpcore | HTTP core |

---

## Reference & Learning

| Repository | Focus |
|------------|-------|
| https://github.com/zebbern/claude-code-guide | Claude Code guide |
| https://github.com/Njengah/claude-code-cheat-sheet | Cheat sheet |
| https://github.com/CherryHQ/cherry-studio | Promising studio |
| https://github.com/tractorjuice/Wardley-Map-Library | Wardley maps |
| https://github.com/Kilo-Org/kilocode | Paid - reverse engineer patterns |
| https://github.com/memvid/claude-brain | Persistent without DB |
| https://github.com/pipeshub-ai/pipeshub-ai | Company tooling |
| https://github.com/Asabeneh/30-Days-Of-Python | Python learning |
| https://github.com/microsoft/Data-Science-For-Beginners | Data science |
| https://github.com/chaosen315/AIwork4translator | Translation |

---

## Game Development (Future)

| Repository | Focus |
|------------|-------|
| https://github.com/IvanMurzak/Unity-MCP | Unity integration |

---

## Integration Status

- [ ] LocalAI stack analysis
- [ ] Docling evaluation
- [ ] LlamaIndex integration
- [ ] Lazy-load skill pattern from wshobson/agents

Last Updated: 2026-01-23
