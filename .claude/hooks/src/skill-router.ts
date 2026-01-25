/**
 * Skill Router Module
 *
 * Provides skill routing, prerequisite resolution, co-activation,
 * and topological sorting for the skill system.
 *
 * Part of the self-improving skill system (Phases 3-6).
 */

import type {
  SkillRulesConfig,
  SkillLookupResult,
} from './shared/skill-router-types.js';

export { CircularDependencyError } from './shared/skill-router-types.js';

/**
 * Detect if there's a circular dependency starting from a skill.
 * Returns the cycle path if found, null otherwise.
 */
export function detectCircularDependency(
  skillName: string,
  rules: SkillRulesConfig
): string[] | null {
  const visiting = new Set<string>();
  const visited = new Set<string>();

  function dfs(name: string, path: string[]): string[] | null {
    if (visiting.has(name)) {
      return [...path, name];
    }
    if (visited.has(name)) return null;

    visiting.add(name);
    const skill = rules.skills[name];
    if (skill?.prerequisites?.require) {
      for (const prereq of skill.prerequisites.require) {
        const cycle = dfs(prereq, [...path, name]);
        if (cycle) return cycle;
      }
    }
    visiting.delete(name);
    visited.add(name);
    return null;
  }

  return dfs(skillName, []);
}

/**
 * Topologically sort skills based on their prerequisites.
 * Throws CircularDependencyError if a cycle is detected.
 * @param skillNameOrNames - A single skill name or array of skill names
 */
export function topologicalSort(
  skillNameOrNames: string | string[],
  rules: SkillRulesConfig
): string[] {
  const skillNames = Array.isArray(skillNameOrNames) ? skillNameOrNames : [skillNameOrNames];
  const visited = new Set<string>();
  const visiting = new Set<string>();
  const result: string[] = [];

  function visit(name: string, path: string[] = []): void {
    if (visiting.has(name)) {
      throw new Error(`Circular dependency detected: ${[...path, name].join(' -> ')}`);
    }
    if (visited.has(name)) return;

    visiting.add(name);
    const skill = rules.skills[name];
    if (skill?.prerequisites?.require) {
      for (const prereq of skill.prerequisites.require) {
        visit(prereq, [...path, name]);
      }
    }
    visiting.delete(name);
    visited.add(name);
    result.push(name);
  }

  for (const name of skillNames) {
    visit(name);
  }

  return result;
}

/**
 * Resolve prerequisites for a skill.
 * Returns suggested and required prerequisites with topological load order.
 */
export function resolvePrerequisites(
  skillName: string,
  rules: SkillRulesConfig
): { suggest: string[]; require: string[]; loadOrder: string[] } {
  const skill = rules.skills[skillName];
  if (!skill) {
    return { suggest: [], require: [], loadOrder: [skillName] };
  }

  const suggest = skill.prerequisites?.suggest ?? [];
  const require = skill.prerequisites?.require ?? [];

  // Collect all required prerequisites transitively
  const allRequired = new Set<string>();
  const queue = [...require];

  while (queue.length > 0) {
    const name = queue.shift()!;
    if (allRequired.has(name)) continue;
    allRequired.add(name);

    const dep = rules.skills[name];
    if (dep?.prerequisites?.require) {
      queue.push(...dep.prerequisites.require);
    }
  }

  // Build load order: required prereqs first, then the skill itself
  const toSort = [...allRequired, skillName];
  const loadOrder = topologicalSort(toSort, rules);

  return { suggest, require: [...allRequired], loadOrder };
}

/**
 * Resolve co-activation for a skill.
 * Returns peers that should be activated together.
 */
export function resolveCoActivation(
  skillName: string,
  rules: SkillRulesConfig
): { peers: string[]; mode: 'all' | 'any' } {
  const skill = rules.skills[skillName];
  if (!skill || !skill.coActivate) {
    return { peers: [], mode: 'any' };
  }

  return {
    peers: skill.coActivate,
    mode: skill.coActivateMode ?? 'any',
  };
}

/**
 * Get the loading mode for a skill.
 */
export function getLoadingMode(
  skillName: string,
  rules: SkillRulesConfig
): 'lazy' | 'eager' | 'eager-prerequisites' {
  const skill = rules.skills[skillName];
  return skill?.loading ?? 'lazy';
}

interface BaseMatch {
  skillName: string;
  source?: 'keyword' | 'intent' | 'memory' | 'jit';
  priorityValue?: number;
  confidence?: number;
}

/**
 * Build an enhanced lookup result with all resolution data.
 * Accepts either (skillName, rules) or (baseMatch, rules).
 */
export function buildEnhancedLookupResult(
  skillNameOrMatch: string | BaseMatch,
  rules: SkillRulesConfig,
  baseResult?: Partial<SkillLookupResult>
): SkillLookupResult {
  const skillName = typeof skillNameOrMatch === 'string'
    ? skillNameOrMatch
    : skillNameOrMatch.skillName;

  const base = typeof skillNameOrMatch === 'string'
    ? (baseResult ?? {})
    : skillNameOrMatch;

  const prerequisites = resolvePrerequisites(skillName, rules);
  const coActivation = resolveCoActivation(skillName, rules);
  const loading = getLoadingMode(skillName, rules);

  return {
    found: true,
    skillName,
    confidence: base.confidence ?? 1.0,
    source: base.source ?? 'keyword',
    prerequisites,
    coActivation,
    loading,
  };
}
