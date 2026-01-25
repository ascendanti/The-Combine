"""
Atlas Router - Rule-based Routing (LLM fallback)

Routes requests to operators:
1. Rule-based matching (no LLM, instant)
2. LocalAI classification (cheap, fast)
3. Claude escalation (expensive, accurate)

Goal: 80%+ requests handled without expensive LLM.
"""

import re
import json
from pathlib import Path
from typing import Dict, Tuple, Optional
from .map import AtlasMap
from .operators import Operators
from .events import EventStore

class AtlasRouter:
    """Deterministic router for Atlas operations."""

    def __init__(self, repo_path: Optional[Path] = None, localai_url: str = 'http://localhost:8080/v1'):
        self.repo_path = Path(repo_path) if repo_path else Path.cwd()
        self.localai_url = localai_url
        self.atlas_map = AtlasMap(self.repo_path)
        self.operators = Operators(self.repo_path, self.atlas_map, localai_url)
        self.events = EventStore(self.repo_path)

        # Rule patterns: (regex, operator, param_extractor)
        self.rules = self._build_rules()

    def _build_rules(self) -> list:
        """Build routing rules."""
        return [
            # LOOKUP patterns
            (r'(?:find|search|where|look for|locate)\s+(?:the\s+)?(.+)', 'LOOKUP', lambda m: {'query': m.group(1)}),
            (r'(?:which|what)\s+(?:files?|modules?)\s+(?:have|contain|handle)\s+(.+)', 'LOOKUP', lambda m: {'query': m.group(1)}),
            (r'show\s+(?:me\s+)?(?:files?|code)\s+(?:for|about|related to)\s+(.+)', 'LOOKUP', lambda m: {'query': m.group(1)}),

            # OPEN patterns
            (r'(?:open|read|show|view|cat)\s+(?:the\s+)?(?:file\s+)?["\']?([^\s"\']+)["\']?', 'OPEN', lambda m: {'file': m.group(1)}),
            (r'(?:what|show)\s+(?:is\s+)?in\s+["\']?([^\s"\']+)["\']?', 'OPEN', lambda m: {'file': m.group(1)}),

            # DIAGNOSE patterns
            (r'(?:i\s+)?(?:got|have|see|getting)\s+(?:an?\s+)?error[:\s]+(.+)', 'DIAGNOSE', lambda m: {'error': m.group(1)}),
            (r'(?:why|what)\s+(?:is|does|causes?)\s+(?:this\s+)?error[:\s]+(.+)', 'DIAGNOSE', lambda m: {'error': m.group(1)}),
            (r'(?:fix|debug|solve|help with)\s+(?:this\s+)?error[:\s]+(.+)', 'DIAGNOSE', lambda m: {'error': m.group(1)}),
            (r'(.+?)\s+(?:is\s+)?not\s+(?:working|recognized|found)', 'DIAGNOSE', lambda m: {'error': m.group(0)}),

            # TEST patterns
            (r'(?:run|execute|test)\s+(?:the\s+)?(?:command\s+)?["\']?(.+?)["\']?$', 'TEST', lambda m: {'command': m.group(1)}),
            (r'(?:check|verify|validate)\s+(?:if\s+)?(.+?)\s+(?:works|is working)', 'TEST', lambda m: {'command': m.group(1)}),

            # General capability queries -> LOOKUP
            (r'(?:list|show)\s+(?:all\s+)?(?:capabilities|features|modules)', 'LOOKUP', lambda m: {'query': 'daemon'}),
            (r'(?:what|which)\s+(?:can|does)\s+(?:the\s+)?(?:system|atlas)\s+(?:do|have)', 'LOOKUP', lambda m: {'query': 'capability'}),
        ]

    def route(self, request: str) -> Tuple[str, Dict, str]:
        """
        Route a request to an operator.

        Returns: (operator, params, routing_method)
        """
        request_lower = request.lower().strip()

        # Try rule-based routing first
        for pattern, operator, extractor in self.rules:
            match = re.search(pattern, request_lower, re.IGNORECASE)
            if match:
                params = extractor(match)
                return (operator, params, 'rule')

        # Fallback: Use LocalAI for classification
        return self._localai_route(request)

    def _localai_route(self, request: str) -> Tuple[str, Dict, str]:
        """Use LocalAI for routing (cheap fallback)."""
        try:
            import urllib.request

            prompt = f"""Classify this request into one operator. Reply with ONLY valid JSON.

Operators:
- LOOKUP: Find files, code, symbols (query: search term)
- OPEN: Read file contents (file: path)
- DIAGNOSE: Debug errors (error: error text)
- TEST: Run commands (command: shell command)
- THINK: Complex reasoning needed

Request: "{request}"

JSON: {{"operator": "OPERATOR_NAME", "params": {{...}}}}"""

            payload = json.dumps({
                'model': 'mistral',
                'messages': [{'role': 'user', 'content': prompt}],
                'temperature': 0,
                'max_tokens': 150
            }).encode()

            req = urllib.request.Request(
                f'{self.localai_url}/chat/completions',
                data=payload,
                headers={'Content-Type': 'application/json'}
            )

            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read())
                content = data.get('choices', [{}])[0].get('message', {}).get('content', '')

                # Parse JSON from response
                json_match = re.search(r'\{[^}]+\}', content)
                if json_match:
                    result = json.loads(json_match.group())
                    return (result.get('operator', 'THINK'), result.get('params', {}), 'localai')

        except Exception as e:
            pass

        # Ultimate fallback: THINK
        return ('THINK', {'question': request}, 'fallback')

    def execute(self, request: str) -> Dict:
        """Route and execute a request."""
        operator, params, method = self.route(request)

        # Execute operator
        result = self.operators.execute(operator, params)

        # Determine next suggestion
        next_suggestion = self._suggest_next(operator, result)

        # Log event
        event_id = self.events.log(
            command_text=request,
            route={'operator': operator, 'method': method},
            operator=operator,
            inputs=params,
            outputs=result,
            status='error' if 'error' in result else 'success',
            error=result.get('error'),
            next_suggestion=next_suggestion
        )

        return {
            'event_id': event_id,
            'operator': operator,
            'routing_method': method,
            'result': result,
            'next_suggestion': next_suggestion
        }

    def _suggest_next(self, operator: str, result: Dict) -> Optional[str]:
        """Suggest next action based on result."""
        if 'error' in result:
            return 'DIAGNOSE: Check playbooks or run THINK for help'

        if operator == 'LOOKUP':
            results = result.get('results', [])
            if results:
                first_file = results[0].get('path', '')
                return f'OPEN: atlas route "open {first_file}"'
            return 'LOOKUP: Try different search terms'

        if operator == 'DIAGNOSE':
            matches = result.get('matches', [])
            if matches and matches[0].get('commands'):
                cmd = matches[0]['commands'][0]
                return f'TEST: atlas route "run {cmd}"'
            return 'THINK: No playbook match, try THINK operator'

        if operator == 'OPEN':
            return 'PATCH: Make edits or LOOKUP for related files'

        if operator == 'THINK':
            response = result.get('response', {})
            next_action = response.get('next_action', 'DONE')
            if next_action != 'DONE':
                return f'{next_action}: {json.dumps(response.get("next_params", {}))}'

        return None

    def loop(self, initial_request: str, max_iterations: int = 5) -> list:
        """Run routing loop until DONE or max iterations."""
        history = []
        current_request = initial_request

        for i in range(max_iterations):
            result = self.execute(current_request)
            history.append(result)

            # Check stop conditions
            if result.get('operator') == 'THINK':
                response = result.get('result', {}).get('response', {})
                if response.get('next_action') == 'DONE':
                    break

            # No next suggestion
            if not result.get('next_suggestion'):
                break

            # Safety: THINK suggests more THINK
            if result.get('operator') == 'THINK' and 'THINK' in str(result.get('next_suggestion', '')):
                break

            # Continue with next suggestion (for loop mode)
            # In practice, we'd parse the suggestion into a new request
            # For now, just return history

        return history


def main():
    """CLI entry point."""
    import argparse
    parser = argparse.ArgumentParser(description='Atlas Router')
    parser.add_argument('request', nargs='*', help='Request to route')
    parser.add_argument('--repo', type=str, help='Repository path')
    parser.add_argument('--loop', action='store_true', help='Run in loop mode')
    parser.add_argument('--debug', action='store_true', help='Show routing details')

    args = parser.parse_args()

    if not args.request:
        parser.print_help()
        return

    request = ' '.join(args.request)
    router = AtlasRouter(Path(args.repo) if args.repo else None)

    if args.loop:
        history = router.loop(request)
        for i, h in enumerate(history):
            print(f"\n--- Step {i+1}: {h['operator']} ---")
            print(json.dumps(h['result'], indent=2)[:500])
    else:
        result = router.execute(request)
        if args.debug:
            print(f"Routing: {result['operator']} via {result['routing_method']}")
        print(json.dumps(result['result'], indent=2))
        if result.get('next_suggestion'):
            print(f"\nNext: {result['next_suggestion']}")


if __name__ == '__main__':
    main()
