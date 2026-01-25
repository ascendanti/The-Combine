"""
LocalOps Router - Single MCP Server for Repo Navigation & Memory Artifacts

Codex Recommendation Implementation:
- Uses ripgrep (rg) and universal-ctags for indexing
- Minimizes Claude context via .repo_artifacts/
- Deterministic workers: explorer, historian, research_documenter
- Seamless integration with existing daemon infrastructure
"""

from .server import LocalOpsServer
from .indexer import RepoIndexer
from .explorer import SymbolExplorer
from .historian import GitHistorian

__all__ = ['LocalOpsServer', 'RepoIndexer', 'SymbolExplorer', 'GitHistorian']
__version__ = '1.0.0'
