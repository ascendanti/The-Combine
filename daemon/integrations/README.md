# Integration Review System

Systematic approach to onboarding, reviewing, and integrating external repositories.

## Process

1. **Discovery** - Identify candidate repos
2. **Analysis** - Deep review with structured template
3. **Documentation** - Record findings for future reference
4. **Mapping** - Map capabilities to our architecture
5. **Integration** - Production-level adoption
6. **Validation** - Test coherence with existing system

## Review Template

Each reviewed repo gets a structured analysis document:
- `integrations/<repo-name>.json` - Machine-readable metadata
- `integrations/<repo-name>.md` - Detailed analysis

## Status Codes

- `analyzed` - Reviewed, patterns documented
- `partial` - Some patterns adopted
- `integrated` - Fully integrated
- `deferred` - Documented for future use
- `rejected` - Not suitable, reasons documented

## Index

See `integration_index.json` for the full registry.
