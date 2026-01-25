"""
LocalOps MCP Server - Single unified server for repo navigation

MCP Tools:
- repo.status      - Get index status
- repo.refresh     - Refresh all indexes
- explorer.structure - Get directory tree
- explorer.find_symbol - Find symbol definitions
- explorer.outline - Get file outline
- explorer.references - Find symbol references
- historian.commits - Get recent commits
- historian.file_history - Get file history
- historian.stats - Get repo statistics
- search.code - Search with ripgrep (cached)
"""

import json
import asyncio
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional

# MCP SDK imports (if available)
try:
    from mcp.server import Server
    from mcp.server.models import InitializationOptions
    from mcp.server.stdio import stdio_server
    from mcp.types import Tool, TextContent
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False

from .indexer import RepoIndexer
from .explorer import SymbolExplorer
from .historian import GitHistorian


class LocalOpsServer:
    """Unified MCP server for repository operations."""

    def __init__(self, repo_path: Optional[Path] = None):
        self.repo_path = Path(repo_path) if repo_path else Path.cwd()
        self.indexer = RepoIndexer(self.repo_path)
        self.explorer = SymbolExplorer(self.repo_path, self.indexer)
        self.historian = GitHistorian(self.repo_path)
        self.artifacts_path = self.repo_path / '.repo_artifacts'
        self.artifacts_path.mkdir(exist_ok=True)

    # === Core MCP Tools ===

    def repo_status(self) -> Dict:
        """Get current index status."""
        return self.indexer.get_status()

    def repo_refresh(self) -> Dict:
        """Refresh all indexes."""
        return self.indexer.refresh()

    def explorer_structure(self, max_depth: int = 3) -> Dict:
        """Get directory structure."""
        structure = self.explorer.get_structure(max_depth)
        self._save_artifact('structure.json', structure)
        return structure

    def explorer_find_symbol(self, name: str, kind: Optional[str] = None) -> Dict:
        """Find symbol by name."""
        results = self.explorer.find_symbol(name, kind)
        return {'symbol': name, 'kind': kind, 'results': results, 'count': len(results)}

    def explorer_outline(self, file_path: str) -> Dict:
        """Get outline of a file."""
        outline = self.explorer.get_file_outline(file_path)
        return {'file': file_path, 'outline': outline}

    def explorer_references(self, symbol: str, file_glob: str = '*') -> Dict:
        """Find all references to a symbol."""
        refs = self.explorer.find_references(symbol, file_glob)
        return {'symbol': symbol, 'references': refs, 'count': len(refs)}

    def historian_commits(self, limit: int = 20) -> Dict:
        """Get recent commits."""
        commits = self.historian.get_recent_commits(limit)
        return {'commits': commits, 'count': len(commits)}

    def historian_file_history(self, file_path: str, limit: int = 10) -> Dict:
        """Get history of a file."""
        history = self.historian.get_file_history(file_path, limit)
        return {'file': file_path, 'history': history}

    def historian_stats(self) -> Dict:
        """Get repository statistics."""
        stats = self.historian.get_stats()
        self._save_artifact('repo_stats.json', stats)
        return stats

    def search_code(self, pattern: str, file_glob: str = '*') -> Dict:
        """Search code with caching."""
        results = self.indexer.search(pattern, file_glob)
        return {'pattern': pattern, 'glob': file_glob, 'results': results, 'count': len(results)}

    # === Artifact Management ===

    def _save_artifact(self, name: str, data: Any):
        """Save artifact to .repo_artifacts/"""
        path = self.artifacts_path / name
        if isinstance(data, dict):
            path.write_text(json.dumps(data, indent=2, default=str))
        else:
            path.write_text(str(data))

    def generate_context(self, entry_point: Optional[str] = None) -> str:
        """Generate LLM-ready context artifact."""
        context = []
        context.append(f"# Repository Context\n")
        context.append(f"Generated: {datetime.now().isoformat()}\n")
        context.append(f"Path: {self.repo_path}\n\n")

        # Stats
        stats = self.historian.get_stats()
        context.append("## Statistics\n")
        context.append(f"- Branch: {stats.get('current_branch', 'unknown')}\n")
        context.append(f"- Commits: {stats.get('total_commits', 0)}\n")
        context.append(f"- Files: {stats.get('total_files', 0)}\n\n")

        # Recent activity
        commits = self.historian.get_recent_commits(5)
        context.append("## Recent Commits\n")
        for c in commits:
            context.append(f"- {c['hash']} {c['message'][:60]}\n")

        # Index status
        status = self.indexer.get_status()
        context.append(f"\n## Index Status\n")
        context.append(f"- Files indexed: {status.get('files_indexed', 0)}\n")
        context.append(f"- Symbols: {status.get('symbols_indexed', 0)}\n")

        content = ''.join(context)
        self._save_artifact('context.md', content)
        return content

    # === Tool Registration ===

    def get_tools(self) -> list:
        """Get list of available MCP tools."""
        return [
            {'name': 'repo.status', 'description': 'Get index status', 'params': {}},
            {'name': 'repo.refresh', 'description': 'Refresh all indexes', 'params': {}},
            {'name': 'explorer.structure', 'description': 'Get directory tree', 'params': {'max_depth': 'int (default 3)'}},
            {'name': 'explorer.find_symbol', 'description': 'Find symbol definitions', 'params': {'name': 'string', 'kind': 'optional string'}},
            {'name': 'explorer.outline', 'description': 'Get file outline', 'params': {'file_path': 'string'}},
            {'name': 'explorer.references', 'description': 'Find symbol references', 'params': {'symbol': 'string', 'file_glob': 'optional string'}},
            {'name': 'historian.commits', 'description': 'Get recent commits', 'params': {'limit': 'int (default 20)'}},
            {'name': 'historian.file_history', 'description': 'Get file history', 'params': {'file_path': 'string', 'limit': 'int'}},
            {'name': 'historian.stats', 'description': 'Get repo statistics', 'params': {}},
            {'name': 'search.code', 'description': 'Search code (cached)', 'params': {'pattern': 'string', 'file_glob': 'optional string'}},
        ]

    def call_tool(self, name: str, params: Dict) -> Dict:
        """Route tool call to appropriate method."""
        handlers = {
            'repo.status': lambda p: self.repo_status(),
            'repo.refresh': lambda p: self.repo_refresh(),
            'explorer.structure': lambda p: self.explorer_structure(p.get('max_depth', 3)),
            'explorer.find_symbol': lambda p: self.explorer_find_symbol(p['name'], p.get('kind')),
            'explorer.outline': lambda p: self.explorer_outline(p['file_path']),
            'explorer.references': lambda p: self.explorer_references(p['symbol'], p.get('file_glob', '*')),
            'historian.commits': lambda p: self.historian_commits(p.get('limit', 20)),
            'historian.file_history': lambda p: self.historian_file_history(p['file_path'], p.get('limit', 10)),
            'historian.stats': lambda p: self.historian_stats(),
            'search.code': lambda p: self.search_code(p['pattern'], p.get('file_glob', '*')),
        }

        if name not in handlers:
            return {'error': f'Unknown tool: {name}', 'available': list(handlers.keys())}

        try:
            return handlers[name](params)
        except Exception as e:
            return {'error': str(e), 'tool': name}


# === MCP Server Entry Point ===

async def run_mcp_server(repo_path: Optional[str] = None):
    """Run as MCP server."""
    if not MCP_AVAILABLE:
        print("MCP SDK not installed. Run: pip install mcp")
        return

    server = Server("localops-router")
    ops = LocalOpsServer(Path(repo_path) if repo_path else Path.cwd())

    @server.list_tools()
    async def list_tools():
        return [
            Tool(
                name="repo_status",
                description="Get index status",
                inputSchema={"type": "object", "properties": {}}
            ),
            Tool(
                name="repo_refresh",
                description="Refresh all indexes",
                inputSchema={"type": "object", "properties": {}}
            ),
            Tool(
                name="explorer_find_symbol",
                description="Find symbol definitions",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "description": "Symbol name"},
                        "kind": {"type": "string", "description": "Symbol kind (function, class, etc)"}
                    },
                    "required": ["name"]
                }
            ),
            Tool(
                name="search_code",
                description="Search code with ripgrep (cached)",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "pattern": {"type": "string", "description": "Search pattern"},
                        "file_glob": {"type": "string", "description": "File glob filter"}
                    },
                    "required": ["pattern"]
                }
            ),
            Tool(
                name="historian_commits",
                description="Get recent commits",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "limit": {"type": "integer", "description": "Number of commits"}
                    }
                }
            ),
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict):
        # Map underscore to dot notation
        tool_name = name.replace('_', '.', 1)
        result = ops.call_tool(tool_name, arguments)
        return [TextContent(type="text", text=json.dumps(result, indent=2))]

    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, InitializationOptions())


def main():
    """CLI entry point."""
    import argparse
    parser = argparse.ArgumentParser(description='LocalOps Router')
    parser.add_argument('--repo', type=str, help='Repository path')
    parser.add_argument('--serve', action='store_true', help='Run as MCP server')
    parser.add_argument('--status', action='store_true', help='Show status')
    parser.add_argument('--refresh', action='store_true', help='Refresh indexes')
    parser.add_argument('--context', action='store_true', help='Generate context')

    args = parser.parse_args()

    if args.serve:
        asyncio.run(run_mcp_server(args.repo))
    else:
        ops = LocalOpsServer(Path(args.repo) if args.repo else Path.cwd())

        if args.status:
            print(json.dumps(ops.repo_status(), indent=2))
        elif args.refresh:
            print(json.dumps(ops.repo_refresh(), indent=2))
        elif args.context:
            print(ops.generate_context())
        else:
            parser.print_help()


if __name__ == '__main__':
    main()
