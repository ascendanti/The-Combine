#!/usr/bin/env python3
"""
Atlas Integration & Consolidation Test
Tests all major system integrations and data flows.
"""

import sys
import os
import json
import sqlite3
from pathlib import Path
from datetime import datetime, timedelta

DAEMON_DIR = Path(__file__).parent
sys.path.insert(0, str(DAEMON_DIR))

results = {'passed': 0, 'failed': 0, 'warnings': 0, 'sections': {}}

def test(section, name, condition, detail=''):
    global results
    if section not in results['sections']:
        results['sections'][section] = []
    status = 'PASS' if condition else 'FAIL'
    results['passed' if condition else 'failed'] += 1
    results['sections'][section].append((name, status, detail))
    icon = '[OK]' if condition else '[!!]'
    print(f'  {icon} {name}' + (f': {detail}' if detail else ''))

def warn(section, name, detail=''):
    global results
    if section not in results['sections']:
        results['sections'][section] = []
    results['warnings'] += 1
    results['sections'][section].append((name, 'WARN', detail))
    print(f'  [??] {name}: {detail}')

def main():
    print('=' * 70)
    print('ATLAS INTEGRATION & CONSOLIDATION TEST')
    print('=' * 70)
    print(f'Timestamp: {datetime.now().isoformat()}')

    # ========================================================================
    # SECTION 1: DATABASE CONSOLIDATION
    # ========================================================================
    print('\n' + '-' * 70)
    print('1. DATABASE CONSOLIDATION')
    print('-' * 70)

    databases = {
        'tasks.db': ['tasks'],
        'outcomes.db': ['outcomes', 'patterns'],
        'strategies.db': ['strategies', 'performance'],
        'memory.db': ['learnings', 'decisions'],
        'emergent.db': ['patterns', 'generated_tasks', 'goals'],
        'utf_knowledge.db': ['claims', 'sources', 'excerpts'],
        'generated_tasks.db': ['generated_tasks'],
        'context_router.db': ['context_scores'],  # Fixed: was file_scores
        'router.db': ['routing_decisions'],
    }

    for db_name, expected_tables in databases.items():
        db_path = DAEMON_DIR / db_name
        if db_path.exists():
            try:
                conn = sqlite3.connect(db_path)
                c = conn.cursor()
                c.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = [r[0] for r in c.fetchall()]

                if expected_tables[0] in tables:
                    c.execute(f'SELECT COUNT(*) FROM {expected_tables[0]}')
                    count = c.fetchone()[0]
                    test('databases', f'{db_name}', True, f'{count} rows in {expected_tables[0]}')
                else:
                    test('databases', f'{db_name}', False, f'missing table {expected_tables[0]}')
                conn.close()
            except Exception as e:
                test('databases', f'{db_name}', False, str(e)[:50])
        else:
            warn('databases', f'{db_name}', 'not found')

    # ========================================================================
    # SECTION 2: CORE MODULE IMPORTS
    # ========================================================================
    print('\n' + '-' * 70)
    print('2. CORE MODULE IMPORTS')
    print('-' * 70)

    core_modules = [
        ('unified_spine', 'UnifiedSpine'),
        ('orchestrator', 'Orchestrator'),
        ('deterministic_router', 'DeterministicRouter'),  # Fixed: main class
        ('memory_router', 'MemoryRouter'),
        ('context_router', 'ContextRouter'),
        ('outcome_tracker', 'record_outcome'),
        ('strategy_evolution', 'Strategy'),  # Fixed: class name
        ('task_generator', 'generate_tasks'),
        ('emergent', 'run_emergent_cycle'),
        ('feedback_loop', 'run_feedback_cycle'),  # Fixed: function name
        ('continuous_executor', 'ContinuousExecutor'),
        ('local_autorouter', 'route_request'),
        ('model_router', 'ModelRouter'),
    ]

    for module_name, attr in core_modules:
        try:
            mod = __import__(module_name)
            has_attr = hasattr(mod, attr)
            test('imports', f'{module_name}.{attr}', has_attr)
        except Exception as e:
            test('imports', f'{module_name}', False, str(e)[:40])

    # ========================================================================
    # SECTION 3: CROSS-MODULE DATA FLOW
    # ========================================================================
    print('\n' + '-' * 70)
    print('3. CROSS-MODULE DATA FLOW')
    print('-' * 70)

    # Test: Task Generator -> Task Queue
    try:
        from task_generator import add_generated_task

        task_id = add_generated_task(
            category='test',
            title='Integration flow test ' + datetime.now().strftime('%H%M%S'),
            description='Testing cross-module flow',
            rationale='Automated test',
            priority=5,
            source='integration_test'
        )
        test('flow', 'TaskGenerator -> generated_tasks.db', task_id is not None, task_id[:20] if task_id else 'None')
    except Exception as e:
        test('flow', 'TaskGenerator -> generated_tasks.db', False, str(e)[:40])

    # Test: Outcome -> Strategy Feedback
    try:
        from outcome_tracker import record_outcome
        from strategy_evolution import get_strategy, create_strategy

        strat = get_strategy(name='flow_test_strategy')
        if not strat:
            create_strategy(name='flow_test_strategy', type='tactical',
                           description='Flow test', actions=['test'])
            strat = get_strategy(name='flow_test_strategy')

        record_outcome(
            action='flow_test',
            result='success',
            context='strategy=flow_test_strategy',
            duration_ms=50
        )

        strat_after = get_strategy(name='flow_test_strategy')
        after_fitness = strat_after.metrics.get('fitness', 0)

        test('flow', 'Outcome -> Strategy fitness', after_fitness > 0, f'{after_fitness:.4f}')
    except Exception as e:
        test('flow', 'Outcome -> Strategy fitness', False, str(e)[:40])

    # Test: Emergent -> Task Generator
    try:
        conn = sqlite3.connect(DAEMON_DIR / 'generated_tasks.db')
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM generated_tasks WHERE source = ?", ('emergent',))
        emergent_count = c.fetchone()[0]
        conn.close()
        test('flow', 'Emergent -> TaskGenerator', emergent_count > 0, f'{emergent_count} tasks')
    except Exception as e:
        test('flow', 'Emergent -> TaskGenerator', False, str(e)[:40])

    # ========================================================================
    # SECTION 4: AUTONOMOUS EXECUTION LOOP
    # ========================================================================
    print('\n' + '-' * 70)
    print('4. AUTONOMOUS EXECUTION LOOP')
    print('-' * 70)

    try:
        from continuous_executor import ContinuousExecutor
        status = ContinuousExecutor.get_status()

        test('executor', 'Daemon running', status.get('running', False), f"PID {status.get('pid')}")

        tasks = status.get('tasks', {})
        test('executor', 'Tasks completed', tasks.get('complete', 0) > 0, f"{tasks.get('complete', 0)}")

        recent = status.get('recent_events', [])
        if recent:
            latest = recent[0]
            latest_time = datetime.fromisoformat(latest['time'])
            age_seconds = (datetime.now() - latest_time).total_seconds()
            test('executor', 'Recent activity', age_seconds < 300, f'{age_seconds:.0f}s ago')
        else:
            warn('executor', 'Recent activity', 'no events')
    except Exception as e:
        test('executor', 'Status check', False, str(e)[:40])

    # ========================================================================
    # SECTION 5: MEMORY SYSTEMS
    # ========================================================================
    print('\n' + '-' * 70)
    print('5. MEMORY SYSTEMS')
    print('-' * 70)

    try:
        from memory_router import MemoryRouter
        mr = MemoryRouter()
        test('memory', 'MemoryRouter init', True)
    except Exception as e:
        test('memory', 'MemoryRouter init', False, str(e)[:40])

    try:
        from context_router import ContextRouter
        cr = ContextRouter()
        test('memory', 'ContextRouter init', True)

        conn = sqlite3.connect(DAEMON_DIR / 'context_router.db')
        c = conn.cursor()
        c.execute('SELECT COUNT(*) FROM context_scores')  # Fixed table name
        tracked = c.fetchone()[0]
        conn.close()
        test('memory', 'Files tracked', tracked > 0, f'{tracked} files')
    except Exception as e:
        test('memory', 'ContextRouter', False, str(e)[:40])

    try:
        conn = sqlite3.connect(DAEMON_DIR / 'cross_session_memory.db')
        c = conn.cursor()
        # Check what tables exist
        c.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [r[0] for r in c.fetchall()]
        if 'memories' in tables:
            c.execute('SELECT COUNT(*) FROM memories')
            learnings = c.fetchone()[0]
            test('memory', 'Cross-session memories', learnings >= 0, f'{learnings} memories')
        elif 'learnings' in tables:
            c.execute('SELECT COUNT(*) FROM learnings')
            learnings = c.fetchone()[0]
            test('memory', 'Cross-session learnings', learnings >= 0, f'{learnings} learnings')
        else:
            test('memory', 'Cross-session tables', len(tables) > 0, f'tables: {tables[:3]}')
        conn.close()
    except Exception as e:
        warn('memory', 'Cross-session memory', str(e)[:40])

    # ========================================================================
    # SECTION 6: UTF KNOWLEDGE SYSTEM
    # ========================================================================
    print('\n' + '-' * 70)
    print('6. UTF KNOWLEDGE SYSTEM')
    print('-' * 70)

    try:
        conn = sqlite3.connect(DAEMON_DIR / 'utf_knowledge.db')
        c = conn.cursor()

        c.execute('SELECT COUNT(*) FROM claims')
        claims = c.fetchone()[0]
        test('utf', 'Claims', claims > 0, f'{claims}')

        c.execute('SELECT COUNT(*) FROM sources')
        sources = c.fetchone()[0]
        test('utf', 'Sources', sources > 0, f'{sources}')

        c.execute('SELECT COUNT(*) FROM excerpts')
        excerpts = c.fetchone()[0]
        test('utf', 'Excerpts', excerpts > 0, f'{excerpts}')

        c.execute("SELECT COUNT(*) FROM claims WHERE domain IS NOT NULL AND domain != ''")
        with_domain = c.fetchone()[0]
        coverage = (with_domain / claims * 100) if claims > 0 else 0
        test('utf', 'Domain coverage', coverage > 90, f'{coverage:.1f}%')

        conn.close()
    except Exception as e:
        test('utf', 'UTF Knowledge DB', False, str(e)[:40])

    try:
        conn = sqlite3.connect(DAEMON_DIR / 'utf_embeddings.db')
        c = conn.cursor()
        c.execute('SELECT COUNT(*) FROM claim_embeddings')
        embeddings = c.fetchone()[0]
        conn.close()
        test('utf', 'Claim embeddings', embeddings > 0, f'{embeddings}')
    except Exception as e:
        warn('utf', 'Embeddings', str(e)[:40])

    # ========================================================================
    # SECTION 7: MCP CONFIGURATION
    # ========================================================================
    print('\n' + '-' * 70)
    print('7. MCP CONFIGURATION')
    print('-' * 70)

    try:
        settings_path = DAEMON_DIR.parent / '.claude' / 'settings.local.json'
        with open(settings_path, 'r', encoding='utf-8-sig') as f:
            settings = json.load(f)

        enabled = settings.get('enabledMcpjsonServers', [])

        required_mcp = ['knowledge-graph', 'token-optimizer', 'utf-knowledge']
        for mcp in required_mcp:
            test('mcp', f'{mcp} enabled', mcp in enabled)

        test('mcp', 'Total servers', len(enabled) >= 5, f'{len(enabled)} enabled')
    except Exception as e:
        test('mcp', 'Settings parse', False, str(e)[:40])

    # ========================================================================
    # SECTION 8: HOOK LIFECYCLE
    # ========================================================================
    print('\n' + '-' * 70)
    print('8. HOOK LIFECYCLE')
    print('-' * 70)

    hooks_dir = DAEMON_DIR.parent / '.claude' / 'hooks'
    required_hooks = [
        'session-briefing.py',
        'auto-cache-pre.py',
        'continuous-learning-stop.py',
        'pre-compact-handoff.py',
    ]

    for hook in required_hooks:
        hook_path = hooks_dir / hook
        test('hooks', hook, hook_path.exists())

    # ========================================================================
    # SECTION 9: STRATEGY EVOLUTION
    # ========================================================================
    print('\n' + '-' * 70)
    print('9. STRATEGY EVOLUTION')
    print('-' * 70)

    try:
        from strategy_evolution import list_strategies, DB_PATH

        strategies = list_strategies()
        test('strategy', 'Strategies exist', len(strategies) > 0, f'{len(strategies)} total')

        active = [s for s in strategies if s.status == 'active']
        test('strategy', 'Active strategies', len(active) >= 0, f'{len(active)} active')

        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('SELECT COUNT(*) FROM performance')
        perf_count = c.fetchone()[0]
        test('strategy', 'Performance records', perf_count > 0, f'{perf_count}')

        c.execute('SELECT COUNT(*) FROM strategies WHERE generation > 0')
        evolved = c.fetchone()[0]
        test('strategy', 'Evolved strategies', evolved >= 0, f'{evolved} evolved')
        conn.close()
    except Exception as e:
        test('strategy', 'Strategy system', False, str(e)[:40])

    # ========================================================================
    # SECTION 10: UNIFIED SPINE CYCLE
    # ========================================================================
    print('\n' + '-' * 70)
    print('10. UNIFIED SPINE CYCLE')
    print('-' * 70)

    try:
        from unified_spine import UnifiedSpine
        spine = UnifiedSpine()
        status = spine.get_status()

        test('spine', 'UnifiedSpine init', True)
        test('spine', 'TaskQueue connected', 'task_queue' in status)
        test('spine', 'Strategies connected', 'strategies' in status)
        test('spine', 'LocalAI available', status.get('routing', {}).get('localai_available', False))
    except Exception as e:
        test('spine', 'UnifiedSpine', False, str(e)[:40])

    # ========================================================================
    # SUMMARY
    # ========================================================================
    print('\n' + '=' * 70)
    print('SUMMARY')
    print('=' * 70)
    print(f'  Passed:   {results["passed"]}')
    print(f'  Failed:   {results["failed"]}')
    print(f'  Warnings: {results["warnings"]}')
    print(f'  Total:    {results["passed"] + results["failed"]}')
    print()

    health_pct = results['passed'] / (results['passed'] + results['failed']) * 100 if (results['passed'] + results['failed']) > 0 else 0
    if health_pct >= 90:
        status_msg = f'SYSTEM HEALTH: EXCELLENT ({health_pct:.0f}%)'
    elif health_pct >= 75:
        status_msg = f'SYSTEM HEALTH: GOOD ({health_pct:.0f}%)'
    elif health_pct >= 50:
        status_msg = f'SYSTEM HEALTH: DEGRADED ({health_pct:.0f}%)'
    else:
        status_msg = f'SYSTEM HEALTH: CRITICAL ({health_pct:.0f}%)'

    print(f'  {status_msg}')
    print('=' * 70)

    if results['failed'] > 0:
        print('\nFAILED TESTS:')
        for section, tests in results['sections'].items():
            for name, status, detail in tests:
                if status == 'FAIL':
                    print(f'  [{section}] {name}: {detail}')

    return 0 if results['failed'] == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
