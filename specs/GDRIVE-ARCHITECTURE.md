# Google Drive Integration Architecture

## Vision
Seamless bidirectional access to Google Drive with intelligent organization, automatic categorization, and deep integration with the knowledge system.

---

## Layer 1: Access Infrastructure

### Authentication
```
┌─────────────────────────────────────────────────────────┐
│ OAuth2 Flow (Service Account recommended)               │
│                                                         │
│ credentials.json → Token refresh → Access token cache   │
│                                                         │
│ Storage: Dragonfly cache (TTL: 55 minutes)             │
│ Fallback: .atlas/gdrive_tokens.json                    │
└─────────────────────────────────────────────────────────┘
```

### API Layer
```python
# daemon/gdrive/client.py
class GDriveClient:
    def __init__(self, credentials_path: Path):
        self.service = build('drive', 'v3', credentials=creds)
        self.cache = DragonflyCache()  # Existing infrastructure

    # Core operations
    def list_folder(self, folder_id: str) -> List[FileMetadata]
    def read_file(self, file_id: str) -> bytes | str
    def move_file(self, file_id: str, new_parent: str)
    def create_folder(self, name: str, parent: str) -> str
    def search(self, query: str) -> List[FileMetadata]
    def get_metadata(self, file_id: str) -> FileMetadata
```

---

## Layer 2: Indexing & Caching

### File Index (SQLite → `.atlas/gdrive_index.db`)
```sql
CREATE TABLE files (
    id TEXT PRIMARY KEY,           -- Google Drive file ID
    name TEXT,
    mime_type TEXT,
    parent_id TEXT,
    size INTEGER,
    modified_time TEXT,
    md5_checksum TEXT,
    indexed_at TEXT,
    category TEXT,                 -- Auto-assigned category
    tags TEXT,                     -- JSON array of tags
    summary TEXT,                  -- LLM-generated summary
    local_cache_path TEXT          -- If downloaded locally
);

CREATE TABLE folders (
    id TEXT PRIMARY KEY,
    name TEXT,
    parent_id TEXT,
    path TEXT,                     -- Full path like /Documents/Work/Projects
    file_count INTEGER,
    total_size INTEGER
);

CREATE TABLE sync_state (
    folder_id TEXT PRIMARY KEY,
    last_sync TEXT,
    change_token TEXT              -- Google Drive change token
);
```

### Caching Strategy
```
┌─────────────────────────────────────────────────────────┐
│ Cache Hierarchy                                         │
│                                                         │
│ L1: Dragonfly (metadata, 1h TTL)                       │
│     Key: gdrive:meta:{file_id}                         │
│                                                         │
│ L2: Local SQLite (index, persistent)                   │
│     Full file/folder structure                         │
│                                                         │
│ L3: Local files (large/frequent, configurable)         │
│     ~/.atlas/gdrive_cache/                             │
└─────────────────────────────────────────────────────────┘
```

---

## Layer 3: Intelligence Layer

### Auto-Categorization
```python
# daemon/gdrive/categorizer.py
CATEGORY_RULES = {
    'documents': ['.doc', '.docx', '.pdf', '.txt', '.md'],
    'spreadsheets': ['.xls', '.xlsx', '.csv'],
    'presentations': ['.ppt', '.pptx'],
    'images': ['.jpg', '.png', '.gif', '.svg'],
    'code': ['.py', '.js', '.ts', '.go', '.rs'],
    'archives': ['.zip', '.tar', '.gz', '.rar'],
    'media': ['.mp4', '.mp3', '.wav', '.mov'],
}

# Content-based categorization (for PDFs, docs)
def categorize_by_content(file_id: str) -> str:
    """Use LocalAI to categorize based on content."""
    # Extract text → LocalAI classification → Category
```

### Organization Rules
```yaml
# .atlas/gdrive_rules.yaml
rules:
  - name: "Sort by Date"
    trigger: "new_file"
    condition: "category == 'documents'"
    action: "move_to_folder(f'/Documents/{year}/{month}')"

  - name: "Archive Old"
    trigger: "scheduled_daily"
    condition: "modified_time < 6_months_ago"
    action: "move_to_folder('/Archive/{year}')"

  - name: "Project Grouping"
    trigger: "new_file"
    condition: "name contains project keywords"
    action: "move_to_folder('/Projects/{detected_project}')"
```

### Knowledge Integration
```
┌─────────────────────────────────────────────────────────┐
│ Integration with UTF Knowledge System                   │
│                                                         │
│ PDF in Drive → autonomous_ingest → UTF Claims           │
│                                                         │
│ On new PDF detected:                                    │
│   1. Download to GateofTruth/                          │
│   2. autonomous_ingest processes                        │
│   3. Claims stored in utf_knowledge.db                 │
│   4. Link back to Drive file_id                        │
│   5. Summary stored in gdrive_index.db                 │
└─────────────────────────────────────────────────────────┘
```

---

## Layer 4: MCP Server Interface

### Tools Exposed
```python
# daemon/gdrive/mcp_server.py
MCP_TOOLS = [
    Tool("gdrive.list", "List folder contents", {folder_path: str}),
    Tool("gdrive.search", "Search files", {query: str, category?: str}),
    Tool("gdrive.read", "Read file content", {file_path: str}),
    Tool("gdrive.move", "Move file", {file_path: str, dest_folder: str}),
    Tool("gdrive.organize", "Run organization rules", {folder?: str}),
    Tool("gdrive.stats", "Get usage statistics", {}),
    Tool("gdrive.sync", "Sync folder index", {folder?: str}),
    Tool("gdrive.categorize", "Auto-categorize files", {folder: str}),
]
```

### Integration with Atlas Router
```python
# atlas_spine/router.py - Add Google Drive patterns
GDRIVE_RULES = [
    (r'(?:list|show|what\'s in)\s+(?:my\s+)?(?:drive|google drive)(?:\s+(.+))?',
     'GDRIVE_LIST', lambda m: {'folder': m.group(1) or '/'}),

    (r'(?:find|search)\s+(?:in\s+)?drive\s+(?:for\s+)?(.+)',
     'GDRIVE_SEARCH', lambda m: {'query': m.group(1)}),

    (r'(?:organize|sort|clean)\s+(?:my\s+)?(?:drive|google drive)',
     'GDRIVE_ORGANIZE', lambda m: {}),
]
```

---

## Layer 5: Sync & Watch Infrastructure

### Change Detection
```python
# daemon/gdrive/watcher.py
class GDriveWatcher:
    """Watch for changes using Google Drive Changes API."""

    def __init__(self):
        self.change_token = load_change_token()

    async def poll_changes(self) -> List[Change]:
        """Poll for changes since last token."""
        changes = self.service.changes().list(
            pageToken=self.change_token,
            spaces='drive'
        ).execute()

        self.change_token = changes.get('newStartPageToken')
        return changes.get('changes', [])

    async def process_change(self, change: Change):
        """Process a single change."""
        if change['removed']:
            await self.handle_delete(change['fileId'])
        else:
            await self.handle_update(change['file'])
```

### Bidirectional Sync
```
┌─────────────────────────────────────────────────────────┐
│ Sync Architecture                                       │
│                                                         │
│ Local → Drive:                                          │
│   - GateofTruth/ processed files → Archive folder      │
│   - Handoffs → Backup/Handoffs                         │
│   - Specs → Backup/Specs                               │
│                                                         │
│ Drive → Local:                                          │
│   - New PDFs → GateofTruth/ for processing             │
│   - Shared docs → Local workspace                      │
│   - Reference materials → Reference/                   │
└─────────────────────────────────────────────────────────┘
```

---

## Layer 6: Docker Integration

### docker-compose.yaml addition
```yaml
gdrive-sync:
  build:
    context: ./daemon
    dockerfile: Dockerfile
  container_name: gdrive-sync
  command: python gdrive/watcher.py --watch --interval 300
  volumes:
    - ./daemon:/app
    - ~/.atlas/gdrive_credentials:/creds:ro
    - /c/Users/New Employee/Documents/GateofTruth:/gateoftruth
  environment:
    - GOOGLE_APPLICATION_CREDENTIALS=/creds/credentials.json
    - DRAGONFLY_URL=redis://dragonfly-cache:6379
  depends_on:
    dragonfly-cache:
      condition: service_healthy
  restart: unless-stopped
```

---

## Superstructure: Unified File Intelligence

### The Big Picture
```
┌─────────────────────────────────────────────────────────────────────┐
│                    UNIFIED FILE INTELLIGENCE                         │
│                                                                      │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                 │
│  │ Local Files │  │ Google Drive│  │   Obsidian  │                 │
│  │ (GateOfTruth│  │  (Cloud)    │  │   (Notes)   │                 │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘                 │
│         │                │                │                         │
│         └────────────────┼────────────────┘                         │
│                          ▼                                          │
│              ┌─────────────────────┐                                │
│              │   File Router       │                                │
│              │   (atlas_spine)     │                                │
│              └──────────┬──────────┘                                │
│                         │                                           │
│         ┌───────────────┼───────────────┐                          │
│         ▼               ▼               ▼                          │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐                   │
│  │ Ingest      │ │ Index       │ │ Organize    │                   │
│  │ Pipeline    │ │ (search)    │ │ Rules       │                   │
│  └──────┬──────┘ └──────┬──────┘ └──────┬──────┘                   │
│         │               │               │                          │
│         └───────────────┼───────────────┘                          │
│                         ▼                                          │
│              ┌─────────────────────┐                               │
│              │  Knowledge Graph    │                               │
│              │  (UTF Claims)       │                               │
│              └─────────────────────┘                               │
└─────────────────────────────────────────────────────────────────────┘
```

### What This Enables
1. **Single search** across local + Drive + Obsidian
2. **Automatic filing** based on content, not just name
3. **Knowledge extraction** from any source
4. **Cross-reference** files by concept, not location
5. **Proactive organization** - system suggests better structure

---

## Implementation Phases

### Phase 1: Foundation (Day 1-2)
- [ ] Set up Google Cloud project
- [ ] Create OAuth credentials
- [ ] Implement basic `GDriveClient`
- [ ] Add to `.atlas/gdrive_index.db`

### Phase 2: Core Operations (Day 3-4)
- [ ] List/read/search operations
- [ ] MCP server with basic tools
- [ ] Dragonfly caching integration

### Phase 3: Intelligence (Day 5-6)
- [ ] Auto-categorization
- [ ] Organization rules engine
- [ ] Integration with autonomous_ingest

### Phase 4: Sync & Watch (Day 7-8)
- [ ] Change detection polling
- [ ] Bidirectional sync
- [ ] Docker service

### Phase 5: Superstructure (Day 9-10)
- [ ] Unified file search
- [ ] Atlas router integration
- [ ] Cross-source knowledge linking

---

## Pre-requisites Checklist

- [ ] Google Cloud Console account
- [ ] Project created with Drive API enabled
- [ ] OAuth consent screen configured
- [ ] Service account or OAuth2 desktop credentials
- [ ] Test folder structure identified

---

## Google Drive + LocalAI Enhancement

### Storage Synergies

| Use Case | How Drive Helps | Token/Cost Impact |
|----------|-----------------|-------------------|
| **Model Library** | Store 10+ LLM models (GGUF), download on demand | Run larger models (13B, 34B) |
| **RAG Corpus** | Store 1000s of PDFs, index locally | Massive knowledge without context cost |
| **Embedding Cache** | Persist embeddings to Drive | Don't re-embed on restart |
| **Fine-tune Data** | Store training datasets | Custom models for free |
| **Cold Storage** | Archive old cache/indexes | Keep local SSD free |

### Architecture: Drive-Backed LocalAI

```
┌─────────────────────────────────────────────────────────────────────┐
│                    DRIVE-BACKED LOCALAI                             │
│                                                                      │
│  Google Drive (Cloud)                                               │
│  ├── /Models/                                                       │
│  │   ├── mistral-7b-instruct.Q5_K_M.gguf (5GB)                    │
│  │   ├── codellama-13b.Q4_K_M.gguf (8GB)                          │
│  │   ├── mixtral-8x7b.Q4_K_M.gguf (26GB)                          │
│  │   └── ...                                                        │
│  ├── /Embeddings/                                                   │
│  │   ├── utf_knowledge_embeddings.npy                              │
│  │   └── document_vectors.pkl                                       │
│  ├── /Datasets/                                                     │
│  │   ├── finetune_conversations.jsonl                              │
│  │   └── domain_knowledge.parquet                                   │
│  └── /RAG_Corpus/                                                   │
│      ├── papers/                                                    │
│      ├── books/                                                     │
│      └── documentation/                                             │
│                                                                      │
│                         ▼ (sync on demand)                          │
│                                                                      │
│  Local Cache (~/.atlas/models/)                                     │
│  └── Active model loaded in LocalAI                                │
└─────────────────────────────────────────────────────────────────────┘
```

### Model Hot-Swap Pipeline

```python
# daemon/gdrive/model_manager.py
class ModelManager:
    def __init__(self, gdrive_client, local_cache: Path):
        self.gdrive = gdrive_client
        self.cache = local_cache
        self.active_model = None

    async def ensure_model(self, model_name: str):
        """Download model from Drive if not cached."""
        local_path = self.cache / f"{model_name}.gguf"

        if not local_path.exists():
            # Download from Drive
            drive_path = f"/Models/{model_name}.gguf"
            await self.gdrive.download(drive_path, local_path)

        return local_path

    async def swap_model(self, model_name: str):
        """Hot-swap LocalAI model."""
        model_path = await self.ensure_model(model_name)

        # Update LocalAI config
        await self.update_localai_model(model_path)
        self.active_model = model_name

    def get_recommended_model(self, task_complexity: str) -> str:
        """Select model based on task."""
        return {
            'simple': 'phi-2',           # 2.7B, fast
            'medium': 'mistral-7b',       # 7B, balanced
            'complex': 'codellama-13b',   # 13B, accurate
            'reasoning': 'mixtral-8x7b',  # MoE, best quality
        }.get(task_complexity, 'mistral-7b')
```

### RAG Corpus Sync

```python
# daemon/gdrive/rag_sync.py
class RAGCorpusSync:
    """Sync Drive documents to local RAG index."""

    def __init__(self, gdrive_client):
        self.gdrive = gdrive_client
        self.corpus_folder = "/RAG_Corpus"

    async def sync_new_documents(self):
        """Download new documents and trigger ingest."""
        new_files = await self.gdrive.list_modified_since(
            self.corpus_folder,
            since=self.last_sync
        )

        for file in new_files:
            local_path = Path("GateofTruth") / file.name
            await self.gdrive.download(file.id, local_path)
            # autonomous_ingest will pick it up

    async def upload_processed(self, local_file: Path, metadata: dict):
        """Upload processed file back to Drive with metadata."""
        await self.gdrive.upload(
            local_file,
            folder=f"{self.corpus_folder}/processed",
            properties=metadata  # Claims extracted, etc.
        )
```

### Benefits

| Metric | Without Drive | With Drive |
|--------|---------------|------------|
| Available models | 1-2 (disk limit) | 10+ (swap on demand) |
| RAG corpus size | ~50GB | Unlimited |
| Embedding persistence | Lost on restart | Permanent |
| Fine-tune capability | Limited data | Full dataset access |
| Backup/recovery | Manual | Automatic |

### Quick Win: Model Library

Start with just model storage:

1. Upload models to Drive `/Models/`
2. Create `model_manager.py`
3. Add to `model_router.py` - swap models based on task
4. Huge models (34B, 70B) become accessible

---

## Pre-requisites Checklist

- [ ] Google Cloud Console account
- [ ] Project created with Drive API enabled
- [ ] OAuth consent screen configured
- [ ] Service account or OAuth2 desktop credentials
- [ ] Test folder structure identified

---

*Estimated effort: 10 days for full implementation*
*Dependencies: Existing Dragonfly, LocalAI, autonomous_ingest*
