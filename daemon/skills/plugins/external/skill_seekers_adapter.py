"""Skill Seekers adapter - Convert docs/repos/PDFs to Claude skills.

Capabilities:
- Multi-source scraping (docs, GitHub, PDFs)
- Deep AST parsing
- Conflict detection (docs vs code)
- Multi-LLM output support
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Dict, List, Optional
import logging

from .base_adapter import LocalToolAdapter

log = logging.getLogger(__name__)


class SkillSeekersAdapter(LocalToolAdapter):
    """Adapter for Skill Seekers docs-to-skills converter.

    Capabilities:
    - Analyze documentation websites
    - Parse GitHub repositories
    - Extract skill definitions from code
    - Detect documentation drift

    Usage:
        adapter = SkillSeekersAdapter()

        # Analyze documentation
        result = adapter.execute({
            "task": "analyze_docs",
            "url": "https://docs.example.com",
            "format": "claude"
        }, budget_tokens=3000)

        # Analyze repository
        result = adapter.execute({
            "task": "analyze_repo",
            "path": "/path/to/repo",
            "languages": ["python", "typescript"]
        }, budget_tokens=3000)

        # Detect conflicts
        result = adapter.execute({
            "task": "detect_conflicts",
            "docs_url": "https://docs.example.com/api",
            "repo_path": "/path/to/repo"
        }, budget_tokens=2000)
    """

    @property
    def tool_name(self) -> str:
        return "skill-seekers"

    def _invoke_local(self, input_data: Dict, budget: int) -> Dict:
        """Execute Skill Seekers task.

        Args:
            input_data: Task-specific input
            budget: Token budget

        Returns:
            Task-specific output
        """
        task = input_data.get("task", "analyze_docs")
        self._track_tokens(100)

        if task == "analyze_docs":
            return self._analyze_docs(input_data, budget)
        elif task == "analyze_repo":
            return self._analyze_repo(input_data, budget)
        elif task == "detect_conflicts":
            return self._detect_conflicts(input_data, budget)
        elif task == "generate_skill":
            return self._generate_skill(input_data, budget)
        else:
            return {"error": f"Unknown task: {task}"}

    def _analyze_docs(self, input_data: Dict, budget: int) -> Dict:
        """Analyze documentation and extract skill-relevant content."""
        url = input_data.get("url", "")
        content = input_data.get("content", "")
        format_type = input_data.get("format", "claude")

        if not url and not content:
            return {"error": "No URL or content provided"}

        self._track_tokens(100)

        # If content provided, analyze directly
        if content:
            return self._extract_skill_from_content(content, format_type)

        # Otherwise return structure for docs analysis
        # (actual scraping would be done by external tool)
        return {
            "url": url,
            "status": "pending",
            "format": format_type,
            "instructions": {
                "1": "Fetch documentation from URL",
                "2": "Extract code examples",
                "3": "Identify API patterns",
                "4": "Generate skill definition",
            },
            "supported_formats": ["claude", "gemini", "openai", "markdown"],
        }

    def _analyze_repo(self, input_data: Dict, budget: int) -> Dict:
        """Analyze repository and extract skill definitions."""
        path = input_data.get("path", "")
        languages = input_data.get("languages", ["python"])
        depth = input_data.get("depth", "shallow")

        if not path:
            return {"error": "No repository path provided"}

        repo_path = Path(path)
        if not repo_path.exists():
            return {"error": f"Path does not exist: {path}"}

        self._track_tokens(200)

        analysis = {
            "path": str(repo_path),
            "languages": languages,
            "depth": depth,
            "files_analyzed": 0,
            "skills_found": [],
            "patterns": [],
            "exports": [],
        }

        # Analyze based on languages
        for lang in languages:
            if lang == "python":
                analysis.update(self._analyze_python(repo_path, depth))
            elif lang in ["typescript", "javascript"]:
                analysis.update(self._analyze_js_ts(repo_path, depth))

        self._track_tokens(len(json.dumps(analysis)) // 4)
        return analysis

    def _analyze_python(self, repo_path: Path, depth: str) -> Dict:
        """Analyze Python repository."""
        results = {
            "python_files": 0,
            "classes": [],
            "functions": [],
            "patterns": [],
        }

        # Find Python files
        py_files = list(repo_path.glob("**/*.py"))[:50]  # Limit for budget
        results["python_files"] = len(py_files)

        for py_file in py_files[:10]:  # Analyze first 10 for shallow
            try:
                content = py_file.read_text(encoding="utf-8", errors="ignore")
                self._track_tokens(len(content) // 8)

                # Extract classes
                classes = re.findall(r'^class\s+(\w+)', content, re.MULTILINE)
                results["classes"].extend([
                    {"name": c, "file": str(py_file.relative_to(repo_path))}
                    for c in classes
                ])

                # Extract functions
                functions = re.findall(r'^def\s+(\w+)', content, re.MULTILINE)
                results["functions"].extend([
                    {"name": f, "file": str(py_file.relative_to(repo_path))}
                    for f in functions if not f.startswith("_")
                ])

                # Detect patterns
                if "async def" in content:
                    results["patterns"].append("async")
                if "@dataclass" in content:
                    results["patterns"].append("dataclass")
                if "FastAPI" in content or "@app." in content:
                    results["patterns"].append("fastapi")
                if "pytest" in content or "def test_" in content:
                    results["patterns"].append("pytest")

            except Exception as e:
                log.warning("python_analysis_error", file=str(py_file), error=str(e))

        results["patterns"] = list(set(results["patterns"]))
        return results

    def _analyze_js_ts(self, repo_path: Path, depth: str) -> Dict:
        """Analyze JavaScript/TypeScript repository."""
        results = {
            "js_ts_files": 0,
            "exports": [],
            "components": [],
            "patterns": [],
        }

        # Find JS/TS files
        js_files = list(repo_path.glob("**/*.js")) + list(repo_path.glob("**/*.ts"))
        js_files = [f for f in js_files if "node_modules" not in str(f)][:50]
        results["js_ts_files"] = len(js_files)

        for js_file in js_files[:10]:
            try:
                content = js_file.read_text(encoding="utf-8", errors="ignore")
                self._track_tokens(len(content) // 8)

                # Extract exports
                exports = re.findall(r'export\s+(?:const|function|class)\s+(\w+)', content)
                results["exports"].extend([
                    {"name": e, "file": str(js_file.relative_to(repo_path))}
                    for e in exports
                ])

                # React components
                components = re.findall(r'(?:function|const)\s+(\w+).*?(?:=>|{).*?return\s*\(?\s*<', content, re.DOTALL)
                results["components"].extend(components)

                # Detect patterns
                if "React" in content:
                    results["patterns"].append("react")
                if "express" in content.lower():
                    results["patterns"].append("express")
                if "async/await" in content or "async " in content:
                    results["patterns"].append("async")

            except Exception as e:
                log.warning("js_analysis_error", file=str(js_file), error=str(e))

        results["patterns"] = list(set(results["patterns"]))
        return results

    def _detect_conflicts(self, input_data: Dict, budget: int) -> Dict:
        """Detect conflicts between documentation and code."""
        docs_content = input_data.get("docs_content", "")
        code_content = input_data.get("code_content", "")

        if not docs_content or not code_content:
            return {"error": "Both docs_content and code_content required"}

        self._track_tokens(len(docs_content) // 4 + len(code_content) // 4)

        conflicts = []

        # Extract documented functions
        doc_functions = set(re.findall(r'`(\w+)\(`', docs_content))
        doc_functions.update(re.findall(r'def\s+(\w+)', docs_content))

        # Extract code functions
        code_functions = set(re.findall(r'def\s+(\w+)', code_content))
        code_functions.update(re.findall(r'function\s+(\w+)', code_content))

        # Find undocumented functions
        undocumented = code_functions - doc_functions
        for func in undocumented:
            if not func.startswith("_"):
                conflicts.append({
                    "type": "undocumented",
                    "name": func,
                    "severity": "warning",
                    "message": f"Function '{func}' exists in code but not in docs",
                })

        # Find documented but missing
        missing = doc_functions - code_functions
        for func in missing:
            conflicts.append({
                "type": "missing_implementation",
                "name": func,
                "severity": "error",
                "message": f"Function '{func}' documented but not found in code",
            })

        # Extract documented parameters
        param_pattern = r'`(\w+)`\s*[:\-]\s*([^`\n]+)'
        doc_params = re.findall(param_pattern, docs_content)

        output = {
            "conflicts": conflicts,
            "conflict_count": len(conflicts),
            "severity_summary": {
                "error": sum(1 for c in conflicts if c["severity"] == "error"),
                "warning": sum(1 for c in conflicts if c["severity"] == "warning"),
            },
            "documented_functions": len(doc_functions),
            "code_functions": len(code_functions),
        }

        self._track_tokens(len(json.dumps(output)) // 4)
        return output

    def _generate_skill(self, input_data: Dict, budget: int) -> Dict:
        """Generate a Claude skill definition from analysis."""
        name = input_data.get("name", "generated-skill")
        description = input_data.get("description", "")
        triggers = input_data.get("triggers", [])
        capabilities = input_data.get("capabilities", [])
        format_type = input_data.get("format", "claude")

        self._track_tokens(100)

        if format_type == "claude":
            skill = self._generate_claude_skill(name, description, triggers, capabilities)
        elif format_type == "markdown":
            skill = self._generate_markdown_skill(name, description, triggers, capabilities)
        else:
            skill = {"error": f"Unsupported format: {format_type}"}

        self._track_tokens(len(json.dumps(skill)) // 4)
        return skill

    def _generate_claude_skill(
        self, name: str, description: str, triggers: List[str], capabilities: List[str]
    ) -> Dict:
        """Generate Claude-compatible skill definition."""
        return {
            "format": "claude",
            "skill": {
                "name": name,
                "description": description,
                "triggers": triggers or [
                    f"When working with {name}",
                    f"Help me with {name}",
                ],
                "instructions": f"""You are an expert in {name}.

{description}

## Capabilities
{chr(10).join(f"- {cap}" for cap in capabilities) if capabilities else "- General assistance"}

## Guidelines
1. Be precise and accurate
2. Provide working code examples
3. Explain your reasoning
4. Suggest best practices
""",
            },
        }

    def _generate_markdown_skill(
        self, name: str, description: str, triggers: List[str], capabilities: List[str]
    ) -> Dict:
        """Generate Markdown skill documentation."""
        markdown = f"""# {name}

{description}

## Triggers

{chr(10).join(f"- {t}" for t in triggers) if triggers else "- General use"}

## Capabilities

{chr(10).join(f"- {c}" for c in capabilities) if capabilities else "- General assistance"}

## Usage

```
Invoke this skill when you need help with {name}.
```
"""
        return {
            "format": "markdown",
            "content": markdown,
        }

    def _extract_skill_from_content(self, content: str, format_type: str) -> Dict:
        """Extract skill definition from documentation content."""
        self._track_tokens(len(content) // 4)

        # Extract title
        title_match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
        title = title_match.group(1) if title_match else "Extracted Skill"

        # Extract description (first paragraph)
        desc_match = re.search(r'^[A-Z][^#\n]+(?:\n[^#\n]+)*', content, re.MULTILINE)
        description = desc_match.group(0).strip() if desc_match else ""

        # Extract code examples
        code_blocks = re.findall(r'```\w*\n(.*?)```', content, re.DOTALL)

        # Extract headings as capabilities
        capabilities = re.findall(r'^##\s+(.+)$', content, re.MULTILINE)

        return self._generate_skill({
            "name": title.lower().replace(" ", "-"),
            "description": description[:200],
            "triggers": [f"Help with {title}"],
            "capabilities": capabilities[:5],
            "format": format_type,
        }, 500)
