# UTF Research Program OS Specification v1.0

## Document Purpose
Technical design specification for a UTF-native knowledge taxonomy, schema, and operator system enabling retrieval, organization, and emergent growth of research knowledge.

---

# 1. UTF Knowledge Theory

## 1.1 Core Primitives

### State
The current configuration of knowledge at time t. A State is a snapshot of all nodes (claims, concepts, models, etc.) and their relationships. States are immutable once recorded; changes produce new states.

### Event
A transformation that moves the system from State_n to State_n+1. Events are atomic, timestamped, and auditable. Examples:
- `INGEST(source_id)` - new source added
- `MERGE(node_a, node_b)` - two concepts unified
- `CONTRADICT(claim_x, claim_y)` - conflict registered

### Projection
A purpose-shaped view of the State. The same State yields different Projections depending on the Lens applied. A Projection is NOT the knowledge itself but a rendering of it for a specific use-context.

### Lens
A filter/transform that shapes how knowledge is retrieved and presented. Lenses encode:
- Use-context (explain, implement, critique, decide)
- Abstraction level (L0-L6)
- Domain scope (narrow vs cross-domain)
- Confidence threshold (show only high-confidence vs include hypotheses)

## 1.2 Why Taxonomy is Multi-Dimensional

Knowledge cannot be captured in a single tree because:

1. **Orthogonal concerns**: A claim has a domain (physics), a type (causal mechanism), an epistemic status (well-established), a scope (micro), and a use-context (implement). These are independent axes.

2. **Context-dependent grouping**: The same concept appears under "optimization" when implementing, under "calculus" when explaining, under "convex analysis" when proving.

3. **Dynamic re-categorization**: As understanding deepens, a "hack" becomes a "technique" becomes a "principle." Fixed trees cannot accommodate this.

4. **Cross-domain transfer**: Analogies require seeing the same structure across different domain branches. Trees hide this.

Therefore: Knowledge lives in a coordinate space, not a folder hierarchy. Obsidian folders are merely one projection of this space for human navigation.

## 1.3 Scientific Change Dynamics (Kuhn-Aware)

Research programs evolve through:

| Phase | Characteristics | System Behavior |
|-------|-----------------|-----------------|
| **Normal Science** | Puzzle-solving within accepted paradigm | INTEGRATE claims into existing frameworks; flag minor anomalies |
| **Anomaly Accumulation** | Results that don't fit | CONTRADICTION_CLUSTER activates; anomaly_count on Paradigm node increases |
| **Crisis** | Competing explanations emerge | Multiple Framework nodes marked `status: contested`; leverage_score spikes for resolution attempts |
| **Revolution** | Paradigm shift | Old Framework marked `status: superseded`; new Framework becomes `status: active`; mass re-linking of dependent nodes |
| **New Normal** | Consolidation | MECHANISM_PROMOTE elevates confirmed models; old anomalies become "explained phenomena" |

The system tracks `paradigm_id` on claims/models to enable filtering by research program and detecting when cross-paradigm contradictions are actually incommensurable framings.

## 1.4 Tiered Coherence

Coherence is enforced through:

1. **Vertical grounding**: Every higher-level node must trace to lower levels
   - L6 Program must link to L5 Frameworks
   - L5 Framework must link to L4 Models
   - L4 Model must link to L3 Concepts + L2 Claims
   - L2 Claim must anchor to L1 Excerpt or be marked `grounding: hypothesis`

2. **Horizontal consistency**: Nodes at the same level must not contradict without explicit `contradicted_by` edges and resolution status

3. **Temporal stability**: Nodes gain `stability_class` based on survival across new evidence integration

4. **Audit completeness**: Every node has `created_by` (operator), `created_at`, `evidence_for` links

Coherence violations are logged, not silently ignored. The system maintains a `coherence_debt` metric.

---

# 2. Ontology / Schema Specification

## 2.1 Abstraction Ladder (L0-L6)

| Level | Name | Definition | Examples |
|-------|------|------------|----------|
| L0 | Source | Original artifact (PDF, paper, book) | "Attention Is All You Need" paper |
| L1 | Excerpt | Direct quote or paraphrase with page anchor | "The dominant sequence transduction models are based on complex recurrent or convolutional neural networks" (p.1) |
| L2 | Claim | Atomic assertion extracted from source | "Self-attention reduces sequential computation to O(1)" |
| L3 | Concept | Abstract idea unifying multiple claims | "Attention mechanism", "Positional encoding" |
| L4 | Model/Mechanism/Protocol | Operational structure explaining how/why | "Scaled dot-product attention", "Multi-head attention" |
| L5 | Framework/Paradigm | Organizing theory unifying models | "Transformer architecture", "Attention-based sequence modeling" |
| L6 | Program/Plan | Actionable research direction or decision | "Replace all RNNs with attention-only models" |

### Roll-up Rules

**L1 → L2 (Excerpt to Claim)**
- Operator: ATOMIZE
- Rule: One excerpt may yield 0-N claims. Each claim must be a single testable/falsifiable assertion.
- Validation: Claim must not contain "and" joining independent assertions (split if so).

**L2 → L3 (Claim to Concept)**
- Operator: DEFINE or ABSTRACT
- Rule: When 3+ claims reference the same abstract entity, create a Concept node.
- Validation: Concept must have at least one Definition claim linked.

**L3 → L4 (Concept to Model)**
- Operator: MODELIZE
- Rule: When a Concept has operational/mechanistic claims explaining how it works, create a Model.
- Validation: Model must link to at least 2 Concepts it relates and have `how_it_works` populated.

**L4 → L5 (Model to Framework)**
- Operator: ABSTRACT
- Rule: When 3+ Models share common assumptions or can be unified under one explanatory umbrella, create a Framework.
- Validation: Framework must have explicit `core_assumptions` and link to constituent Models.

**L5 → L6 (Framework to Program)**
- Operator: PROJECT(lens=decide)
- Rule: When a Framework implies actionable research directions or decisions, create a Program.
- Validation: Program must have `objectives`, `success_criteria`, and link to motivating Framework.

## 2.2 Node Types

### Source
```yaml
type: Source
definition: Original document/artifact ingested into system
required:
  - source_id: string (hash-based)
  - title: string (extracted from content, not filename)
  - authors: list[string]
  - year: int
  - source_type: enum[Paper, Book, Report, Preprint, Blogpost, Documentation]
  - file_hash: string (SHA-256)
  - ingested_at: datetime
recommended:
  - abstract: string
  - venue: string
  - doi: string
  - url: string
  - keywords: list[string]
  - domain: string (from controlled vocab)
  - contribution_bundle_extracted: bool
allowed_links:
  - cites → Source
  - contains → Excerpt
```

### Excerpt
```yaml
type: Excerpt
definition: Direct quote or close paraphrase anchored to source location
required:
  - excerpt_id: string
  - source_id: string
  - text: string (≤500 chars)
  - location: string (page, section, paragraph)
  - extraction_method: enum[Manual, LocalAI, OCR]
recommended:
  - context_before: string (≤100 chars)
  - context_after: string (≤100 chars)
allowed_links:
  - from_source → Source
  - supports → Claim
  - defines_term → Concept
```

### Claim
```yaml
type: Claim
definition: Atomic, falsifiable assertion
required:
  - claim_id: string
  - statement: string (≤200 chars, single assertion)
  - claim_form: enum[Definition, Measurement, EmpiricalRegularity, CausalMechanism, Theorem, Algorithm, NegativeResult, Limitation, Conjecture, SurveySynthesis]
  - grounding: enum[Anchored, Hypothesis, Conjecture]
  - confidence: float[0-1]
recommended:
  - stability_class: enum[Invariant, ContextStable, ContextFragile, Contested]
  - scope: string
  - domain: string
  - evidence_grade: enum[A, B, C, D]
  - replicability_grade: enum[High, Medium, Low, Unknown]
constraints:
  - If grounding=Anchored, must have supported_by edge to Excerpt
  - If grounding=Hypothesis|Conjecture, confidence must be ≤0.6
allowed_links:
  - supported_by → Excerpt, Source
  - contradicted_by → Claim
  - depends_on_assumption → Assumption
  - instance_of → Concept
  - operationalizes → Model
```

### Concept
```yaml
type: Concept
definition: Abstract idea unifying multiple claims/excerpts
required:
  - concept_id: string
  - name: string
  - definition_1liner: string (≤25 words)
  - domain: string
recommended:
  - definition_5bullet: list[string] (≤5 items, ≤25 words each)
  - comprehension_scaffold:
      what: string
      how: string
      when_scope: string
      why_stakes: string
      how_to_use: string
      boundary_conditions: string
      failure_modes: string
  - aliases: list[string]
  - symbol: string (if mathematical)
allowed_links:
  - defined_by → Claim
  - part_of → Concept
  - specializes → Concept
  - generalizes → Concept
  - analogous_to → Concept
  - operationalized_by → Model, Protocol
```

### Model
```yaml
type: Model
definition: Operational/mechanistic structure explaining how something works
required:
  - model_id: string
  - name: string
  - model_type: enum[Mechanism, Algorithm, Architecture, Process, Simulation]
  - definition_1liner: string (≤25 words)
  - how_it_works: string (≤200 words)
recommended:
  - definition_5bullet: list[string]
  - comprehension_scaffold: (same as Concept)
  - inputs: list[string]
  - outputs: list[string]
  - assumptions: list[assumption_id]
  - limitations: list[string]
  - complexity: string (O-notation if applicable)
allowed_links:
  - explains → Concept
  - operationalizes → Concept
  - improves_on → Model, Baseline
  - depends_on_assumption → Assumption
  - tested_by → Result
  - part_of → Framework
```

### Framework
```yaml
type: Framework
definition: Organizing theory or paradigm unifying multiple models
required:
  - framework_id: string
  - name: string
  - definition_1liner: string
  - core_assumptions: list[string]
  - status: enum[Active, Contested, Superseded, Emerging]
recommended:
  - definition_5bullet: list[string]
  - scope: string
  - paradigm_id: string (if part of larger research program)
  - anomaly_count: int
  - key_predictions: list[string]
allowed_links:
  - contains → Model
  - generalizes → Framework
  - contradicted_by → Framework
  - anomaly_for ← Result
```

### Method
```yaml
type: Method
definition: General approach or technique (abstract)
required:
  - method_id: string
  - name: string
  - purpose: string
  - method_type: enum[Analytical, Empirical, Computational, Hybrid]
recommended:
  - applicability_conditions: list[string]
  - limitations: list[string]
allowed_links:
  - instance_of ← Protocol
  - applies_to → ProblemFamily
```

### Protocol
```yaml
type: Protocol
definition: Concrete, replicable procedure
required:
  - protocol_id: string
  - name: string
  - steps: list[string]
  - instance_of: method_id
recommended:
  - inputs_required: list[string]
  - outputs_produced: list[string]
  - computational_requirements: string
  - reproducibility_notes: string
allowed_links:
  - instance_of → Method
  - used_in → Result
  - depends_on_assumption → Assumption
```

### Result
```yaml
type: Result
definition: Empirical finding with quantitative outcome
required:
  - result_id: string
  - summary: string
  - metrics: dict[string, float|string]
  - replicability_grade: enum[High, Medium, Low, Unknown]
recommended:
  - dataset_id: string
  - protocol_id: string
  - baseline_comparison: list[baseline_id]
  - ablation_ids: list[string]
  - statistical_significance: string
  - effect_size: string
constraints:
  - If dataset_id or protocol_id missing, replicability_grade must be Low|Unknown
allowed_links:
  - produced_by → Protocol
  - tested_on → Dataset
  - compared_to → Baseline
  - supports → Claim
  - anomaly_for → Framework, Model
```

### Dataset
```yaml
type: Dataset
definition: Data collection used in experiments
required:
  - dataset_id: string
  - name: string
  - size: string
  - domain: string
recommended:
  - source_url: string
  - collection_method: string
  - known_biases: list[string]
  - license: string
allowed_links:
  - used_in → Result
```

### Baseline
```yaml
type: Baseline
definition: Reference point for comparison
required:
  - baseline_id: string
  - name: string
  - description: string
  - metrics: dict[string, float|string]
recommended:
  - source_id: string
  - year_established: int
  - still_competitive: bool
allowed_links:
  - compared_in → Result
  - improved_by → Result, Model
```

### Ablation
```yaml
type: Ablation
definition: Controlled removal/variation experiment
required:
  - ablation_id: string
  - what_removed: string
  - result_delta: string
  - parent_result_id: string
recommended:
  - interpretation: string
allowed_links:
  - ablation_of → Result, Model
  - reveals → Claim
```

### Limitation
```yaml
type: Limitation
definition: Known constraint or failure mode
required:
  - limitation_id: string
  - statement: string
  - applies_to: list[node_id]
  - severity: enum[Critical, Major, Minor, Noted]
recommended:
  - conditions: string (when limitation manifests)
  - workarounds: list[string]
allowed_links:
  - limits → Model, Method, Result, Claim
  - addressed_by → Model, Method
```

### Assumption
```yaml
type: Assumption
definition: Premise taken as given, violation breaks dependent claims
required:
  - assumption_id: string
  - statement: string
  - assumption_type: enum[Data, Compute, Distribution, Causal, Measurement, Social, Normative]
  - violations: string (what fails if broken)
recommended:
  - scope: string
  - testable: bool
  - tested: bool
  - confidence: float
allowed_links:
  - assumed_by → Claim, Model, Result, Protocol
```

### Argument
```yaml
type: Argument
definition: Reasoning structure connecting premises to conclusion
required:
  - argument_id: string
  - premises: list[claim_id]
  - inference_steps: list[string] (1-5 bullets)
  - conclusion: claim_id
recommended:
  - validity_notes: string (gaps, handwaves, hidden assumptions)
  - argument_type: enum[Deductive, Inductive, Abductive, Analogical]
allowed_links:
  - argues_for → Claim
  - uses_premise → Claim
```

### ProblemFamily
```yaml
type: ProblemFamily
definition: Class of related problems sharing structure
required:
  - problem_id: string
  - name: string
  - definition: string
  - instances: list[string]
recommended:
  - known_approaches: list[method_id]
  - open_questions: list[question_id]
  - hardness: string
allowed_links:
  - instance_of ← specific problem
  - solved_by → Method, Model
  - open_question → Question
```

### Paradigm (alias: ResearchProgram)
```yaml
type: Paradigm
definition: Large-scale research tradition with core commitments
required:
  - paradigm_id: string
  - name: string
  - hard_core: list[string] (non-negotiable commitments)
  - protective_belt: list[string] (adjustable auxiliary hypotheses)
  - status: enum[Dominant, Competing, Declining, Historical]
recommended:
  - exemplar_sources: list[source_id]
  - anomaly_count: int
  - successor: paradigm_id (if superseded)
allowed_links:
  - contains → Framework
  - competes_with → Paradigm
  - supersedes → Paradigm
```

### Question
```yaml
type: Question
definition: Open research question or gap
required:
  - question_id: string
  - question_text: string
  - question_type: enum[Empirical, Theoretical, Methodological, Applied]
  - priority: enum[Critical, High, Medium, Low]
recommended:
  - motivating_source: source_id
  - blocking_assumptions: list[assumption_id]
  - potential_approaches: list[string]
allowed_links:
  - motivated_by → Source, Result, Limitation
  - would_resolve → Claim (if answered)
  - addressed_by → Source, Result
```

### Synthesis
```yaml
type: Synthesis
definition: Novel integration of multiple nodes into new insight
required:
  - synthesis_id: string
  - summary: string
  - source_nodes: list[node_id]
  - synthesis_type: enum[Unification, Contrast, GapIdentification, Transfer, MetaAnalysis]
  - created_by: operator_name
  - created_at: datetime
recommended:
  - confidence: float
  - novelty_kind: enum[Incremental, Bridging, Foundational]
allowed_links:
  - synthesizes → any node
  - proposes → Claim, Question
```

### Decision (alias: Task)
```yaml
type: Decision
definition: Actionable choice or task derived from knowledge
required:
  - decision_id: string
  - statement: string
  - decision_type: enum[ResearchDirection, Implementation, Evaluation, Acquisition]
  - status: enum[Proposed, Active, Completed, Abandoned]
recommended:
  - rationale: string
  - supporting_evidence: list[node_id]
  - success_criteria: list[string]
  - deadline: date
allowed_links:
  - based_on → Synthesis, Claim, Result
  - blocked_by → Question, Assumption
```

### Entity
```yaml
type: Entity
definition: Named entity (person, organization, place, event)
required:
  - entity_id: string
  - name: string
  - entity_type: enum[Person, Organization, Place, Event, Artifact]
recommended:
  - aliases: list[string]
  - affiliations: list[entity_id]
  - active_period: string
allowed_links:
  - authored → Source
  - affiliated_with → Entity
  - participated_in → Entity (Event)
```

## 2.3 Edge Types

### Core Edges

| Edge | Source Types | Target Types | Semantics |
|------|--------------|--------------|-----------|
| `cites` | Source | Source | Bibliographic reference |
| `supported_by` | Claim | Excerpt, Source, Result | Evidence relationship |
| `contradicted_by` | Claim, Model, Framework | Claim, Result | Conflict (requires resolution_status) |
| `defines` | Claim, Excerpt | Concept | Definitional anchor |
| `instance_of` | specific | general | Type hierarchy |
| `part_of` | component | whole | Mereological |
| `explains` | Model, Mechanism | Concept, Phenomenon | Explanatory |
| `operationalizes` | Model, Protocol | Concept | Makes abstract concrete |
| `generalizes` | abstract | specific | Abstraction |
| `specializes` | specific | abstract | Refinement |
| `analogous_to` | any | any (same level) | Structural similarity |

### Scientific Edges

| Edge | Source Types | Target Types | Semantics |
|------|--------------|--------------|-----------|
| `improves_on` | Result, Model | Baseline, Model | Progress claim |
| `replicates` | Result | Result | Successful reproduction |
| `fails_to_replicate` | Result | Result | Failed reproduction |
| `depends_on_assumption` | Claim, Model, Result | Assumption | Dependency |
| `tested_under` | Result | Protocol, Dataset | Experimental context |
| `ablation_of` | Ablation | Result, Model | Controlled variation |
| `tradeoff_with` | Model, Method | Model, Method | Mutual exclusion |
| `anomaly_for` | Result | Framework, Model | Unexplained finding |
| `argues_for` | Argument | Claim | Reasoning support |

### Edge Constraints

1. **Claim grounding**: Every Claim with `grounding=Anchored` must have at least one `supported_by` edge to Excerpt or Source.

2. **Result completeness**: Every Result should have:
   - `tested_on` → Dataset (if missing: `replicability_grade ≤ Low`)
   - `produced_by` → Protocol (if missing: `replicability_grade ≤ Low`)

3. **Contradiction resolution**: Every `contradicted_by` edge must have:
   - `resolution_status`: enum[Unresolved, Resolved, Incommensurable]
   - `resolution_notes`: string (if resolved)

4. **Bidirectional awareness**: If A `improves_on` B, system should auto-create `improved_by` backlink.

---

# 3. Dimensional Knowledge Coordinate System (DKCS) v2

## 3.1 Base Dimensions

| Dimension | Values | Description |
|-----------|--------|-------------|
| `domain` | Controlled vocab (domains.yaml) | Subject area |
| `type` | Node type enum | What kind of knowledge unit |
| `level` | L0-L6 | Abstraction level |
| `epistemic` | Established, Supported, Contested, Speculative, Refuted | Confidence tier |
| `scope` | Universal, Domain-wide, Context-specific, Instance-specific | Generality |
| `utility` | Foundational, Instrumental, Terminal, Meta | Use category |
| `maturity` | Nascent, Developing, Mature, Declining | Lifecycle stage |
| `confidence` | 0.0-1.0 | Numeric certainty |

## 3.2 Scientific Axes (Required)

| Dimension | Values | Description |
|-----------|--------|-------------|
| `research_role` | Contribution, Replication, Survey, Critique, Tool | Paper's function |
| `novelty_kind` | Incremental, Bridging, Foundational, Refutation | Type of advance |
| `leverage_score` | 0.0-1.0 | Strategic importance for understanding |

## 3.3 Controlled Vocabulary Files

### 99_Indices/domains.yaml
```yaml
domains:
  - machine_learning
  - machine_learning/deep_learning
  - machine_learning/reinforcement_learning
  - machine_learning/nlp
  - machine_learning/computer_vision
  - mathematics
  - mathematics/linear_algebra
  - mathematics/probability
  - mathematics/optimization
  - physics
  - physics/quantum
  - physics/statistical_mechanics
  - neuroscience
  - neuroscience/computational
  - economics
  - economics/game_theory
  - philosophy
  - philosophy/epistemology
  - philosophy/philosophy_of_science
  - engineering
  - engineering/systems
  - engineering/control
  - _meta  # knowledge about knowledge
```

### 99_Indices/types.yaml
```yaml
types:
  - Source
  - Excerpt
  - Claim
  - Concept
  - Model
  - Framework
  - Method
  - Protocol
  - Result
  - Dataset
  - Baseline
  - Ablation
  - Limitation
  - Assumption
  - Argument
  - ProblemFamily
  - Paradigm
  - Question
  - Synthesis
  - Decision
  - Entity
```

### 99_Indices/epistemic.yaml
```yaml
epistemic_status:
  - Established    # Widely accepted, extensive evidence
  - Supported      # Good evidence, some replication
  - Contested      # Conflicting evidence or interpretations
  - Speculative    # Limited evidence, plausible
  - Refuted        # Contradicted by strong evidence
```

### 99_Indices/lenses.yaml
```yaml
lenses:
  - explain_teach        # Pedagogical: what, why, how
  - implement            # Operational: steps, code, protocol
  - predict_forecast     # Forward-looking: given X, expect Y
  - critique_stress_test # Adversarial: weaknesses, edge cases
  - transfer_analogize   # Cross-domain: map to new context
  - decide_act           # Action-oriented: what to do now
```

## 3.4 Coordinate String Format

For debugging and dedup, nodes can be represented as coordinate strings:

```
{type}:{level}:{domain}:{epistemic}:{scope}:{name_hash}
```

Examples:
```
Claim:L2:machine_learning/nlp:Supported:Domain-wide:a3f2c1
Model:L4:machine_learning/deep_learning:Established:Universal:7b2e9d
Concept:L3:mathematics/optimization:Established:Universal:c4d8a2
```

This enables:
- Fast dedup (same coordinates = likely duplicate)
- Similarity search (nearby coordinates = related nodes)
- Gap detection (sparse regions = under-explored areas)

---

# 4. Morphological Layer

## 4.1 Claim Form Enum

| Form | Definition | Integration Behavior |
|------|------------|---------------------|
| `Definition` | Specifies meaning of term | Anchor for Concept nodes; compositional |
| `Measurement` | Quantitative observation | Links to Result; requires units/protocol |
| `EmpiricalRegularity` | "X tends to correlate with Y" | Statistical; needs replication |
| `CausalMechanism` | "X causes Y because Z" | Requires Model; high value if supported |
| `Theorem` | Proven logical statement | Compositional; check axioms |
| `Algorithm` | Step-by-step procedure | Procedural; links to Protocol |
| `NegativeResult` | "X does not work/hold" | Bounds search space; often undervalued |
| `Limitation` | Constraint on applicability | Conditional; modifies other claims |
| `Conjecture` | Unproven hypothesis | Low confidence; high leverage if true |
| `SurveySynthesis` | Summary of multiple sources | Meta-level; check source coverage |

## 4.2 Stability Class

| Class | Definition | System Behavior |
|-------|------------|-----------------|
| `Invariant` | Holds across all known contexts | High confidence; use freely |
| `ContextStable` | Holds within specified scope | Check scope match before applying |
| `ContextFragile` | Sensitive to conditions | Always include caveats |
| `Contested` | Active disagreement | Show competing views |

## 4.3 Integration Mode

| Mode | Definition | When to Use |
|------|------------|-------------|
| `Compositional` | Claims combine additively | Definitions, theorems |
| `Comparative` | Claims contrast alternatives | Methods, models |
| `Conditional` | Claims apply under conditions | Limitations, empirical regularities |
| `Procedural` | Claims sequence into process | Algorithms, protocols |

## 4.4 How Morphology Affects Retrieval

When answering a query:

1. **Identify required morphology**: "How do I implement X?" needs Procedural/Algorithm claims; "Why does X work?" needs CausalMechanism claims.

2. **Filter by stability**: If use_context is Decide/Act, prefer Invariant and ContextStable; if Critique, include ContextFragile and Contested.

3. **Match integration mode**: For implementation queries, chain Procedural claims; for explanation, layer Compositional definitions then CausalMechanism.

---

# 5. Use-Context as First-Class Dimension

## 5.1 Use-Context Enum

| Context | Definition | Projection Emphasis |
|---------|------------|---------------------|
| `Explain_Teach` | Build understanding | Definitions, examples, analogies, scaffold |
| `Implement` | Execute in practice | Protocols, code, concrete steps, gotchas |
| `Predict_Forecast` | Anticipate outcomes | Empirical regularities, models, confidence bounds |
| `Critique_Stress_Test` | Find weaknesses | Limitations, assumptions, anomalies, edge cases |
| `Transfer_Analogize` | Apply to new domain | Structural similarities, abstracted patterns |
| `Decide_Act` | Choose action | Trade-offs, risks, success criteria, recommendations |

## 5.2 Projection Differences by Use-Context

| Context | Included Node Types | Confidence Filter | Emphasis |
|---------|--------------------| ------------------|----------|
| Explain_Teach | Concept, Definition Claims, Model (simplified) | ≥0.6 | Clarity over precision |
| Implement | Protocol, Algorithm Claims, Result (benchmarks) | ≥0.7 | Completeness over elegance |
| Predict_Forecast | Model, EmpiricalRegularity Claims, Dataset | ≥0.5 (show uncertainty) | Calibration over confidence |
| Critique_Stress_Test | Limitation, Assumption, Contested Claims, Anomaly | All (include low) | Coverage over comfort |
| Transfer_Analogize | Concept (abstract), analogous_to edges, Framework | ≥0.6 | Structure over detail |
| Decide_Act | Synthesis, Decision, Trade-off edges, leverage_score | ≥0.7 | Actionability over completeness |

## 5.3 Projection Answer Requirements

Every projection must include:

```yaml
projection_response:
  answer: string
  use_context: enum
  linked_nodes:
    - node_id: string
      relevance: float
      contribution: string (how this node contributed)
  confidence: float
  evidence_grade: enum[A, B, C, D]
  replicability_grade: enum[High, Medium, Low, Unknown]
  missing_pieces:
    - description: string
      would_raise_confidence_by: float
      how_to_obtain: string
  caveats:
    - string
```

---

# 6. UTF Operator Library

## 6.1 Macro Operators

### INGEST
```yaml
operator: INGEST
definition: Add new Source to system
inputs:
  - file_path: string
  - source_type: enum
outputs:
  - source_node: Source
  - excerpt_nodes: list[Excerpt]
event_log:
  - timestamp
  - file_hash
  - extraction_method
  - excerpt_count
  - error_count
failure_modes:
  - PDF unreadable → tag source `extraction_quality: failed`
  - Language unsupported → tag `language: unsupported`
  - Duplicate hash → link to existing, do not create
```

### IMBIBE
```yaml
operator: IMBIBE
definition: Deep extraction of contribution bundle from Source
inputs:
  - source_id: string
outputs:
  - claims: list[Claim]
  - methods: list[Method|Protocol]
  - results: list[Result]
  - baselines: list[Baseline]
  - ablations: list[Ablation]
  - assumptions: list[Assumption]
  - limitations: list[Limitation]
  - questions: list[Question] (future work)
event_log:
  - timestamp
  - source_id
  - element_counts (by type)
  - missing_elements (what couldn't be extracted)
  - confidence_distribution
failure_modes:
  - Method not explicit → create Limitation "method underspecified"
  - No baselines → mark Result `baseline_comparison: none`
  - Missing metrics → mark Result `metrics: incomplete`
```

### INTEGRATE
```yaml
operator: INTEGRATE
definition: Connect new nodes to existing graph
inputs:
  - new_nodes: list[Node]
  - existing_graph: Graph
outputs:
  - edges_created: list[Edge]
  - conflicts_detected: list[Contradiction]
  - concepts_updated: list[Concept]
event_log:
  - timestamp
  - new_node_ids
  - edge_count
  - conflict_count
  - merge_suggestions
failure_modes:
  - Orphan node (no connections) → tag `integration_status: orphan`
  - Concept collision (same name, different meaning) → create disambiguation
  - Circular dependency → tag and log
```

## 6.2 Micro Operators

### ANCHOR
```yaml
operator: ANCHOR
definition: Attach Claim to supporting Excerpt
inputs:
  - claim_id
  - excerpt_id
outputs:
  - supported_by edge
event_log: [claim_id, excerpt_id, timestamp]
failure_modes:
  - Excerpt doesn't support claim → reject with reason
```

### ATOMIZE
```yaml
operator: ATOMIZE
definition: Split compound statement into atomic Claims
inputs:
  - text: string
  - source_location: string
outputs:
  - claims: list[Claim]
event_log: [input_text, output_count, split_points]
failure_modes:
  - Cannot split (already atomic) → return single claim
  - Ambiguous split → create multiple interpretations, tag `atomization: ambiguous`
```

### DEFINE
```yaml
operator: DEFINE
definition: Create or update Concept definition
inputs:
  - concept_name: string
  - definition_claims: list[Claim]
outputs:
  - concept_node: Concept
  - defines edges
event_log: [concept_id, definition_source, prior_definition_if_any]
failure_modes:
  - Conflicting definitions → create Contested status, link both
```

### MODELIZE
```yaml
operator: MODELIZE
definition: Elevate related Claims/Concepts to Model
inputs:
  - concept_ids: list[string]
  - mechanistic_claims: list[Claim]
outputs:
  - model_node: Model
event_log: [model_id, source_concepts, claim_count]
failure_modes:
  - Insufficient mechanistic detail → create Model with `completeness: partial`
```

### ABSTRACT
```yaml
operator: ABSTRACT
definition: Generalize from instances to higher-level node
inputs:
  - instance_nodes: list[Node]
  - abstraction_level: int (target L)
outputs:
  - abstract_node: Node (at target level)
  - generalizes edges
event_log: [input_ids, output_id, abstraction_type]
failure_modes:
  - Instances too heterogeneous → tag `abstraction_quality: forced`
```

### CONCRETIZE
```yaml
operator: CONCRETIZE
definition: Generate specific instance from abstract node
inputs:
  - abstract_node: Node
  - context: string
outputs:
  - concrete_node: Node
  - specializes edge
event_log: [abstract_id, concrete_id, context]
failure_modes:
  - Context incompatible → reject with reason
```

### MERGE
```yaml
operator: MERGE
definition: Unify duplicate/equivalent nodes
inputs:
  - node_a: Node
  - node_b: Node
outputs:
  - merged_node: Node
  - redirect_edges: list[Edge] (rewired)
event_log: [merged_ids, new_id, edge_rewire_count]
failure_modes:
  - Not actually equivalent → reject, create analogous_to instead
```

### SPLIT
```yaml
operator: SPLIT
definition: Divide overloaded node into distinct nodes
inputs:
  - node: Node
  - split_criteria: string
outputs:
  - split_nodes: list[Node]
event_log: [original_id, new_ids, split_reason]
failure_modes:
  - No clear split point → tag `needs_review: split_ambiguous`
```

### CONTRAST
```yaml
operator: CONTRAST
definition: Create explicit comparison between nodes
inputs:
  - node_a: Node
  - node_b: Node
  - dimensions: list[string]
outputs:
  - comparison_edges: list[Edge]
  - synthesis_node: Synthesis (optional)
event_log: [compared_ids, dimensions, differences_found]
failure_modes:
  - Incomparable (different types/levels) → reject or note limitation
```

### PROJECT(lens)
```yaml
operator: PROJECT
definition: Generate use-context-specific view
inputs:
  - query: string
  - lens: enum[Explain, Implement, Predict, Critique, Transfer, Decide]
  - scope: optional[node_ids or domain]
outputs:
  - projection_response: ProjectionResponse
event_log: [query, lens, nodes_retrieved, confidence]
failure_modes:
  - Insufficient coverage → list missing_pieces
```

### AUDIT(trace)
```yaml
operator: AUDIT
definition: Generate provenance trace for any node
inputs:
  - node_id: string
outputs:
  - creation_event: Event
  - dependency_chain: list[Node]
  - modification_history: list[Event]
event_log: [audited_node, trace_depth]
failure_modes:
  - Broken provenance → flag `audit_status: incomplete`
```

### DISTILL(node)
```yaml
operator: DISTILL
definition: Update compression triplet based on current evidence
inputs:
  - node_id: string
outputs:
  - updated_1liner: string
  - updated_5bullet: list[string]
  - delta_log: string (what changed and why)
event_log: [node_id, prior_version, new_version, trigger]
failure_modes:
  - No new information → no-op, log "no change"
```

## 6.3 Self-Improvement Loop Operators (INTEGRATE++)

### FRONTIER_SCAN
```yaml
operator: FRONTIER_SCAN
definition: Identify knowledge gaps and high-leverage unknowns
inputs:
  - domain_filter: optional[string]
  - depth: int (how many hops from known)
outputs:
  - frontier_questions: list[Question]
  - sparse_regions: list[coordinate_range]
  - recommended_sources: list[string] (titles/keywords to seek)
event_log: [scan_scope, gap_count, priority_ranking]
```

### CONTRADICTION_CLUSTER
```yaml
operator: CONTRADICTION_CLUSTER
definition: Group related contradictions for resolution
inputs:
  - none (scans all contradicted_by edges)
outputs:
  - clusters: list[ContradictionCluster]
    - claims_involved: list[Claim]
    - potential_resolution: string
    - blocking_assumptions: list[Assumption]
event_log: [cluster_count, largest_cluster_size]
```

### TRANSFER_SUGGEST
```yaml
operator: TRANSFER_SUGGEST
definition: Propose cross-domain analogies
inputs:
  - source_domain: string
  - target_domain: string
outputs:
  - transfer_candidates: list[TransferSuggestion]
    - source_node: Node
    - target_mapping: string
    - confidence: float
    - caveats: list[string]
event_log: [domains, candidate_count, accepted_count]
```

### MECHANISM_PROMOTE
```yaml
operator: MECHANISM_PROMOTE
definition: Elevate well-supported Claims to Model status
inputs:
  - threshold_evidence: int (min supporting Results)
  - threshold_stability: enum[ContextStable, Invariant]
outputs:
  - promoted_models: list[Model]
event_log: [scanned_claims, promoted_count, rejection_reasons]
```

### PROTOCOL_HARDEN
```yaml
operator: PROTOCOL_HARDEN
definition: Strengthen Protocol based on accumulated experience
inputs:
  - protocol_id: string
  - result_ids: list[string] (Results using this Protocol)
outputs:
  - updated_protocol: Protocol
  - added_caveats: list[string]
  - refined_steps: list[string]
event_log: [protocol_id, result_count, modifications]
```

### LEVERAGE_PRIORITIZE
```yaml
operator: LEVERAGE_PRIORITIZE
definition: Rank nodes/questions by strategic importance
inputs:
  - candidates: list[Node|Question]
  - objective: string (e.g., "understand transformers", "implement RAG")
outputs:
  - ranked_list: list[(node_id, leverage_score, rationale)]
event_log: [objective, candidate_count, top_5]
```

---

# 7. Contribution Bundle Extraction Spec

For each scientific Source, extract the following structured decomposition:

## 7.1 Required Elements

### Claims
```yaml
claims:
  - claim_id: auto-generated
    statement: string (atomic, ≤200 chars)
    claim_form: enum
    excerpt_anchor: excerpt_id
    confidence: float
    novelty: bool (is this new to this paper?)
```
Rule: Minimum 3 claims per Source. If fewer extractable, mark Source `claim_density: low`.

### Methods/Protocols
```yaml
methods:
  - method_id: auto-generated
    name: string
    description: string
    steps: list[string] (if Protocol-level detail available)
    completeness: enum[Full, Partial, Referenced]
```
Rule: If no method described, create Limitation node "methodology not specified" and reduce replicability.

### Results
```yaml
results:
  - result_id: auto-generated
    summary: string
    metrics:
      metric_name: value (with units)
    dataset_id: string (or "unspecified")
    protocol_id: string (or "unspecified")
    statistical_significance: string (or "not reported")
```
Rule: If metrics missing, mark `metrics: qualitative_only`.

### Baselines
```yaml
baselines:
  - baseline_id: auto-generated
    name: string
    source: string (citation or "author-implemented")
    metrics: dict
```
Rule: If no baselines, mark Source `baseline_comparison: none`.

### Ablations
```yaml
ablations:
  - ablation_id: auto-generated
    what_removed: string
    delta: string (effect on metrics)
    interpretation: string
```
Rule: Ablations are optional but valuable. If present, extract all.

### Assumptions
```yaml
assumptions:
  - assumption_id: auto-generated
    statement: string
    assumption_type: enum
    explicit: bool (stated by authors vs inferred)
    violations: string
```
Rule: Extract at least 2 assumptions per Source (often implicit).

### Limitations
```yaml
limitations:
  - limitation_id: auto-generated
    statement: string
    severity: enum
    acknowledged_by_authors: bool
```
Rule: If authors claim no limitations, mark Source `limitation_acknowledgment: absent` (red flag).

### Future Work / Questions
```yaml
questions:
  - question_id: auto-generated
    question_text: string
    question_type: enum
    mentioned_in_source: bool
```
Rule: Extract "future work" section items as Question nodes.

## 7.2 Absence Representation

When an element cannot be extracted:

```yaml
missing_element:
  element_type: enum
  reason: enum[NotPresent, Unclear, BehindPaywall, LanguageBarrier]
  confidence_penalty: float (how much to reduce overall source reliability)
```

Example penalties:
- No method: -0.3 replicability
- No baselines: -0.2 confidence on improvement claims
- No limitations acknowledged: -0.1 overall (author bias concern)

---

# 8. Internalization Enhancements

## 8.1 Assumption Ledger

First-class treatment of assumptions as nodes:

```yaml
Assumption:
  assumption_id: string
  statement: string
  assumption_type:
    - Data           # "Training data is IID"
    - Compute        # "Sufficient GPU memory available"
    - Distribution   # "Test distribution matches training"
    - Causal         # "X causes Y, not reverse"
    - Measurement    # "Metrics capture true performance"
    - Social         # "Users behave rationally"
    - Normative      # "Fairness means equal outcomes"
  violations: string (what breaks if assumption false)
  scope: string (where assumption applies)
  testable: bool
  tested: bool
  test_result: optional[string]
```

Edge: `depends_on_assumption` links Claim, Model, Result, Protocol → Assumption

Query support: "What breaks if [assumption] is violated?" → trace all dependent nodes.

## 8.2 7-Slot Comprehension Scaffold

Required for every Concept and Model at L3+:

```yaml
comprehension_scaffold:
  what: string        # Definition (1-2 sentences)
  how: string         # Mechanism/process
  when_scope: string  # Conditions where applicable
  why_stakes: string  # Why it matters
  how_to_use: string  # Practical application
  boundary_conditions: string  # Where it breaks down
  failure_modes: string        # Common mistakes/misuses
```

Completeness tracking: `scaffold_completeness: 0-7` (count of filled slots)

## 8.3 Glossary + Symbol Table Extraction

Per Source, extract:

```yaml
glossary:
  terms:
    - term: string
      definition: string (≤50 words)
      linked_concept: optional[concept_id]
      first_occurrence: string (page/section)

symbol_table:
  symbols:
    - symbol: string (e.g., "\\theta")
      meaning: string
      units: optional[string]
      scope: string (section or "global")

abbreviation_map:
  abbreviations:
    - abbrev: string
      expansion: string
      first_defined: string (page/section)
```

## 8.4 Argument Map Schema

Explicit representation of reasoning:

```yaml
Argument:
  argument_id: string
  argument_type: enum[Deductive, Inductive, Abductive, Analogical]
  premises:
    - claim_id: string
      role: string (e.g., "major premise", "evidence")
  inference_steps:
    - step_number: int
      statement: string (≤50 words)
      inference_type: optional[string] (e.g., "modus ponens")
  conclusion: claim_id
  validity_notes: string (gaps, hidden assumptions, handwaves)
  strength: enum[Strong, Moderate, Weak, Fallacious]
```

Edge: `argues_for` (Argument → Claim)

## 8.5 Evidence Grade + Replicability Grade

### Evidence Grade (for Claims)

| Grade | Criteria |
|-------|----------|
| A | Multiple independent replications; meta-analysis available; large effect sizes |
| B | At least one replication; consistent with theory; reasonable sample size |
| C | Single study; plausible but unreplicated; small sample or effect |
| D | Anecdotal; theoretical only; contradicted by other evidence |

### Replicability Grade (for Results)

| Grade | Criteria |
|-------|----------|
| High | Code available; data available; method fully specified; successfully replicated |
| Medium | Method specified; data/code partially available; not yet replicated |
| Low | Method underspecified; no data/code; or failed replication attempts |
| Unknown | Insufficient information to assess |

Heuristics for local model:
- Code link present → +1 replicability
- "Data available upon request" → Medium
- No method section → Low
- "We replicate [X]" → check if successful

## 8.6 Delta Notes

For each Source, capture what's new:

```yaml
delta_notes:
  delta_vs_prior:
    - "First to apply X to domain Y"
    - "Achieves Z% improvement over baseline B on dataset D"
    - "Proposes novel loss function L"
    - "Identifies limitation L in prior work P"
  baseline_gap_closed: string (which gap this work addresses)
  remaining_gaps: list[string]
```

Edge: `improves_on` (Result/Model → Baseline/Model with `improvement: string`)

## 8.7 Compression Triplet

Three representations maintained for each Concept/Model/Framework:

```yaml
compression_triplet:
  1liner: string (≤25 words)
  5bullet:
    - bullet_1 (≤25 words)
    - bullet_2
    - bullet_3
    - bullet_4
    - bullet_5
  full_scaffold: comprehension_scaffold (7 slots)
```

DISTILL operator updates these when:
- New evidence arrives (supporting or contradicting)
- Scope changes (generalized or specialized)
- New use-context requires different emphasis

Log deltas: `distill_history: list[(timestamp, trigger, old_1liner, new_1liner)]`

---

# 9. Obsidian Vault Architecture

## 9.1 Folder Layout

```
vault/
├── 00_Sources/
│   ├── 2024/
│   │   ├── attention-is-all-you-need.md
│   │   └── ...
│   └── by-domain/
│       └── (symlinks or MOCs)
├── 01_Excerpts/
│   └── (rarely browsed directly)
├── 02_Claims/
│   ├── by-form/
│   │   ├── definitions.md (MOC)
│   │   ├── mechanisms.md (MOC)
│   │   └── ...
│   └── by-domain/
├── 03_Concepts/
│   ├── attention-mechanism.md
│   └── ...
├── 04_Models/
│   ├── transformer.md
│   └── ...
├── 05_Frameworks/
│   ├── attention-based-sequence-modeling.md
│   └── ...
├── 06_Syntheses/
│   └── ...
├── 07_Lenses/
│   ├── explain-teach.md
│   ├── implement.md
│   └── ...
├── 08_Tasks_Decisions/
│   └── ...
└── 99_Indices/
    ├── domains.yaml
    ├── types.yaml
    ├── epistemic.yaml
    ├── lenses.yaml
    ├── glossary-master.md
    ├── symbol-table-master.md
    └── abbreviations-master.md
```

## 9.2 Templates

### Source Template
```markdown
---
type: Source
source_id: "{{source_id}}"
title: "{{title}}"
authors: [{{authors}}]
year: {{year}}
source_type: {{Paper|Book|Report|Preprint|Blogpost|Documentation}}
venue: "{{venue}}"
doi: "{{doi}}"
url: "{{url}}"
file_hash: "{{hash}}"
ingested_at: {{datetime}}
domain: {{domain}}
contribution_bundle_extracted: {{bool}}
evidence_grade: {{A|B|C|D}}
replicability_grade: {{High|Medium|Low|Unknown}}
---

# {{title}}

## Abstract
{{abstract}}

## Key Claims
- [[Claim-{{id1}}]]
- [[Claim-{{id2}}]]

## Methods
- [[Protocol-{{id}}]] or "Method not fully specified"

## Results
- [[Result-{{id}}]]

## Baselines
- [[Baseline-{{id}}]] or "No baselines reported"

## Assumptions
- [[Assumption-{{id}}]]

## Limitations
- [[Limitation-{{id}}]]

## Future Work
- [[Question-{{id}}]]

## Delta Notes
### What's New
- {{delta_bullet_1}}
- {{delta_bullet_2}}

### Baseline Gap Closed
{{gap}}

## Glossary
| Term | Definition | Concept |
|------|------------|---------|
| {{term}} | {{def}} | [[Concept-{{id}}]] |

## Symbol Table
| Symbol | Meaning | Units | Scope |
|--------|---------|-------|-------|
| {{symbol}} | {{meaning}} | {{units}} | {{scope}} |

## Abbreviations
| Abbrev | Expansion |
|--------|-----------|
| {{abbrev}} | {{expansion}} |
```

### Claim Template
```markdown
---
type: Claim
claim_id: "{{claim_id}}"
statement: "{{statement}}"
claim_form: {{Definition|Measurement|EmpiricalRegularity|CausalMechanism|Theorem|Algorithm|NegativeResult|Limitation|Conjecture|SurveySynthesis}}
grounding: {{Anchored|Hypothesis|Conjecture}}
confidence: {{0.0-1.0}}
stability_class: {{Invariant|ContextStable|ContextFragile|Contested}}
evidence_grade: {{A|B|C|D}}
domain: {{domain}}
scope: {{Universal|DomainWide|ContextSpecific|InstanceSpecific}}
---

# {{statement_short}}

## Statement
{{full_statement}}

## Evidence
- Anchored in: [[Excerpt-{{id}}]]
- Supported by: [[Result-{{id}}]]

## Depends On
- [[Assumption-{{id}}]]

## Related
- Instance of: [[Concept-{{id}}]]
- Contradicted by: [[Claim-{{id}}]] (if any)

## Stability Notes
{{why this stability class}}
```

### Concept Template
```markdown
---
type: Concept
concept_id: "{{concept_id}}"
name: "{{name}}"
domain: {{domain}}
level: L3
epistemic: {{Established|Supported|Contested|Speculative}}
scaffold_completeness: {{0-7}}
aliases: [{{aliases}}]
symbol: "{{symbol if mathematical}}"
---

# {{name}}

## Compression Triplet

### 1-Liner (≤25 words)
{{1liner}}

### 5-Bullet (≤120 words total)
1. {{bullet_1}}
2. {{bullet_2}}
3. {{bullet_3}}
4. {{bullet_4}}
5. {{bullet_5}}

## Comprehension Scaffold

### 1. What
{{what}}

### 2. How
{{how}}

### 3. When (Scope)
{{when_scope}}

### 4. Why (Stakes)
{{why_stakes}}

### 5. How to Use
{{how_to_use}}

### 6. Boundary Conditions
{{boundary_conditions}}

### 7. Failure Modes
{{failure_modes}}

## Defined By
- [[Claim-{{id}}]]

## Part Of
- [[Concept-{{parent_id}}]]

## Operationalized By
- [[Model-{{id}}]]
- [[Protocol-{{id}}]]

## Analogous To
- [[Concept-{{analog_id}}]] — {{why analogous}}
```

### Model Template
```markdown
---
type: Model
model_id: "{{model_id}}"
name: "{{name}}"
model_type: {{Mechanism|Algorithm|Architecture|Process|Simulation}}
domain: {{domain}}
level: L4
epistemic: {{status}}
inputs: [{{inputs}}]
outputs: [{{outputs}}]
complexity: "{{O-notation}}"
scaffold_completeness: {{0-7}}
---

# {{name}}

## Compression Triplet

### 1-Liner
{{1liner}}

### 5-Bullet
1. {{bullet_1}}
2. {{bullet_2}}
3. {{bullet_3}}
4. {{bullet_4}}
5. {{bullet_5}}

## How It Works
{{how_it_works}}

## Comprehension Scaffold
(same 7 slots as Concept)

## Explains
- [[Concept-{{id}}]]

## Depends On
- [[Assumption-{{id}}]]

## Tested By
- [[Result-{{id}}]]

## Improves On
- [[Baseline-{{id}}]] — {{how}}

## Limitations
- [[Limitation-{{id}}]]

## Part Of
- [[Framework-{{id}}]]
```

### Protocol Template
```markdown
---
type: Protocol
protocol_id: "{{protocol_id}}"
name: "{{name}}"
instance_of: "{{method_id}}"
domain: {{domain}}
level: L4
reproducibility_notes: "{{notes}}"
---

# {{name}}

## Purpose
{{purpose}}

## Inputs Required
- {{input_1}}
- {{input_2}}

## Steps
1. {{step_1}}
2. {{step_2}}
3. {{step_3}}
...

## Outputs Produced
- {{output_1}}

## Computational Requirements
{{requirements}}

## Assumptions
- [[Assumption-{{id}}]]

## Used In
- [[Result-{{id}}]]
```

### Result Template
```markdown
---
type: Result
result_id: "{{result_id}}"
source_id: "{{source_id}}"
replicability_grade: {{High|Medium|Low|Unknown}}
---

# {{summary_short}}

## Summary
{{summary}}

## Metrics
| Metric | Value | Baseline | Delta |
|--------|-------|----------|-------|
| {{metric}} | {{value}} | {{baseline_value}} | {{delta}} |

## Experimental Setup
- Dataset: [[Dataset-{{id}}]]
- Protocol: [[Protocol-{{id}}]]

## Baselines Compared
- [[Baseline-{{id}}]]

## Ablations
- [[Ablation-{{id}}]]

## Statistical Significance
{{significance}}

## Supports
- [[Claim-{{id}}]]

## Anomaly For
- [[Framework-{{id}}]] (if applicable)
```

### Framework Template
```markdown
---
type: Framework
framework_id: "{{framework_id}}"
name: "{{name}}"
domain: {{domain}}
level: L5
status: {{Active|Contested|Superseded|Emerging}}
paradigm_id: "{{paradigm_id}}"
anomaly_count: {{int}}
---

# {{name}}

## 1-Liner
{{1liner}}

## Core Assumptions
1. {{assumption_1}}
2. {{assumption_2}}
3. {{assumption_3}}

## Key Predictions
- {{prediction_1}}
- {{prediction_2}}

## Contains
- [[Model-{{id1}}]]
- [[Model-{{id2}}]]

## Generalizes
- [[Framework-{{child_id}}]]

## Anomalies
- [[Result-{{id}}]] — {{why anomalous}}

## Competing Frameworks
- [[Framework-{{competitor_id}}]]
```

### Assumption Template
```markdown
---
type: Assumption
assumption_id: "{{assumption_id}}"
assumption_type: {{Data|Compute|Distribution|Causal|Measurement|Social|Normative}}
testable: {{bool}}
tested: {{bool}}
---

# {{statement_short}}

## Statement
{{statement}}

## Type
{{assumption_type}}

## Violations
What breaks if this assumption is false:
{{violations}}

## Scope
{{scope}}

## Tested?
{{tested_status_and_result}}

## Assumed By
- [[Claim-{{id}}]]
- [[Model-{{id}}]]
- [[Result-{{id}}]]
```

### Argument Template
```markdown
---
type: Argument
argument_id: "{{argument_id}}"
argument_type: {{Deductive|Inductive|Abductive|Analogical}}
strength: {{Strong|Moderate|Weak|Fallacious}}
---

# Argument: {{conclusion_short}}

## Premises
1. [[Claim-{{premise1_id}}]] — {{role}}
2. [[Claim-{{premise2_id}}]] — {{role}}

## Inference Steps
1. {{step_1}}
2. {{step_2}}
3. {{step_3}}

## Conclusion
[[Claim-{{conclusion_id}}]]

## Validity Notes
{{gaps, handwaves, hidden assumptions}}

## Strength Assessment
{{why this strength rating}}
```

### Synthesis Template
```markdown
---
type: Synthesis
synthesis_id: "{{synthesis_id}}"
synthesis_type: {{Unification|Contrast|GapIdentification|Transfer|MetaAnalysis}}
created_by: {{operator}}
created_at: {{datetime}}
confidence: {{0.0-1.0}}
novelty_kind: {{Incremental|Bridging|Foundational}}
---

# {{summary_short}}

## Summary
{{summary}}

## Source Nodes
- [[Node-{{id1}}]] — {{contribution}}
- [[Node-{{id2}}]] — {{contribution}}

## Novel Insight
{{what this synthesis reveals that wasn't in individual sources}}

## Proposes
- [[Claim-{{new_claim_id}}]]
- [[Question-{{new_question_id}}]]

## Confidence Notes
{{why this confidence level}}

## Missing Pieces
- {{what would raise confidence}}
```

---

# 10. Implementation Notes

## 10.1 Minimal Viable Subset (MVP)

### MVP Node Types (start with these)
1. Source
2. Excerpt
3. Claim
4. Concept
5. Assumption
6. Limitation

### MVP Edges (start with these)
1. `supported_by` (Claim → Excerpt)
2. `defines` (Claim → Concept)
3. `depends_on_assumption` (Claim → Assumption)
4. `limits` (Limitation → Claim)
5. `cites` (Source → Source)

### MVP Fields (absolute minimum per node)
- Source: source_id, title, authors, year, file_hash
- Excerpt: excerpt_id, source_id, text, location
- Claim: claim_id, statement, claim_form, grounding, confidence
- Concept: concept_id, name, definition_1liner
- Assumption: assumption_id, statement, assumption_type, violations
- Limitation: limitation_id, statement, severity

## 10.2 Extraction Order for Local Models

Optimized for Mistral 7B capabilities:

**Pass 1: Structural (high reliability)**
1. Title extraction (from content, not filename)
2. Author extraction
3. Abstract extraction
4. Section headings
5. Reference list

**Pass 2: Excerpt extraction (medium reliability)**
1. Definitions (look for "X is defined as", "we define X")
2. Claims with metrics ("achieves X%", "outperforms by Y")
3. Limitation statements ("however", "limitation", "does not")
4. Future work ("future work", "remains to be")

**Pass 3: Semantic (lower reliability, needs validation)**
1. Claim atomization
2. Assumption inference
3. Relationship extraction
4. Concept unification

**Pass 4: Synthesis (defer to periodic batch)**
1. Cross-source concept merging
2. Contradiction detection
3. Framework construction

## 10.3 Quality Gates

### Gate 1: Source Acceptance
A Source becomes "knowledge" (not just a PDF) when:
- [ ] Title extracted (not filename)
- [ ] At least 1 author identified
- [ ] At least 3 excerpts extracted
- [ ] At least 2 claims derived
- [ ] At least 1 assumption identified

Failing gate: Mark `quality_status: pending_review`

### Gate 2: Claim Validity
A Claim is valid when:
- [ ] Single atomic assertion (no "and" joining independent claims)
- [ ] Has grounding (Anchored with excerpt, or explicitly Hypothesis)
- [ ] claim_form assigned
- [ ] confidence assigned

Failing gate: Mark `validity_status: needs_atomization` or `needs_grounding`

### Gate 3: Concept Maturity
A Concept is mature when:
- [ ] At least 1 Definition claim linked
- [ ] definition_1liner populated
- [ ] At least 2 slots of comprehension_scaffold filled

Failing gate: `maturity_status: stub`

## 10.4 Lightweight Heuristics

### leverage_score (0.0-1.0)
```python
def leverage_score(node):
    base = 0.3
    if node.type in ['Framework', 'Paradigm']: base += 0.3
    if node.incoming_edge_count > 5: base += 0.2
    if node.epistemic == 'Contested': base += 0.1  # resolution value
    if node.domain == current_focus_domain: base += 0.1
    return min(base, 1.0)
```

### confidence (0.0-1.0)
```python
def confidence(claim):
    base = 0.5
    if claim.grounding == 'Anchored': base += 0.2
    if claim.evidence_grade == 'A': base += 0.2
    elif claim.evidence_grade == 'B': base += 0.1
    if claim.stability_class == 'Invariant': base += 0.1
    if claim.contradicted_by: base -= 0.2
    return max(0.0, min(base, 1.0))
```

### novelty_kind
```python
def novelty_kind(source):
    if "first" in source.abstract.lower(): return 'Foundational'
    if source.improves_on_count > 0: return 'Incremental'
    if source.cross_domain_refs > 2: return 'Bridging'
    return 'Incremental'
```

### anomaly_for detection
```python
def is_anomaly(result, framework):
    if result contradicts framework.key_predictions: return True
    if result.metrics significantly_differ_from framework.expected_range: return True
    if result explicitly_claims "surprising" or "unexpected": return True
    return False
```

### evidence_grade heuristics
```python
def evidence_grade(claim):
    replications = count_replication_edges(claim)
    if replications >= 3 and meta_analysis_exists(claim): return 'A'
    if replications >= 1: return 'B'
    if supporting_results >= 1: return 'C'
    return 'D'
```

### replicability_grade heuristics
```python
def replicability_grade(result):
    score = 0
    if result.code_available: score += 2
    if result.data_available: score += 2
    if result.protocol.completeness == 'Full': score += 1
    if result.replicated_by: score += 2

    if score >= 5: return 'High'
    if score >= 3: return 'Medium'
    if score >= 1: return 'Low'
    return 'Unknown'
```

## 10.5 Taxonomy Drift Prevention

### Controlled Vocabulary Governance

1. **Canonical files**: All enum values live in `99_Indices/*.yaml`

2. **Validation on write**: Before creating/updating node, validate all enum fields against canonical files

3. **Synonym resolution**: Maintain `99_Indices/synonyms.yaml` mapping variants to canonical:
   ```yaml
   synonyms:
     "deep learning": "machine_learning/deep_learning"
     "DL": "machine_learning/deep_learning"
     "neural networks": "machine_learning/deep_learning"
   ```

4. **Periodic audit**: Monthly AUDIT operator scans for:
   - Nodes with enum values not in canonical files (drift detected)
   - Concepts with same name but different IDs (potential merge)
   - High-count domains that should be split

5. **Change protocol**: To add new enum value:
   - Add to canonical file with definition
   - Run migration to re-classify existing nodes
   - Log change in `99_Indices/changelog.md`

### Uniform Measure Enforcement

1. **Template compliance**: All nodes must use templates (no free-form)

2. **Required field validation**: Nodes missing required fields get `compliance_status: incomplete`

3. **Length limits**: Enforce character limits (1-liner ≤ 25 words, etc.)

4. **Relationship minimums**: Orphan detection (nodes with no edges after 7 days)

---

# MVP Checklist

## Minimum to Start Emergent Reasoning

### Node Types (6)
- [ ] Source (with title, authors, year, file_hash)
- [ ] Excerpt (with source_id, text, location)
- [ ] Claim (with statement, claim_form, grounding, confidence)
- [ ] Concept (with name, definition_1liner)
- [ ] Assumption (with statement, assumption_type, violations)
- [ ] Limitation (with statement, severity)

### Edge Types (5)
- [ ] supported_by (Claim → Excerpt)
- [ ] defines (Claim → Concept)
- [ ] depends_on_assumption (Claim → Assumption)
- [ ] limits (Limitation → Claim, Model)
- [ ] cites (Source → Source)

### Fields per Node (minimum)
- [ ] All nodes: id, type, created_at, created_by
- [ ] Source: title, authors, year
- [ ] Claim: statement, claim_form, confidence
- [ ] Concept: name, definition_1liner

### Operators (4 to start)
- [ ] INGEST (Source + Excerpts)
- [ ] ATOMIZE (Excerpt → Claims)
- [ ] DEFINE (Claims → Concept)
- [ ] AUDIT (trace any node)

### Quality Gates (2)
- [ ] Source acceptance (title + 3 excerpts + 2 claims)
- [ ] Claim validity (atomic + grounded)

### Controlled Vocab (2 files)
- [ ] domains.yaml
- [ ] types.yaml

### Obsidian Structure (4 folders)
- [ ] 00_Sources/
- [ ] 02_Claims/
- [ ] 03_Concepts/
- [ ] 99_Indices/

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-01-23 | Initial specification |

---

*This specification is designed for implementation with LocalAI (Mistral 7B) for extraction and Obsidian for human navigation. All schemas optimize for structured, repeatable extraction targets.*
