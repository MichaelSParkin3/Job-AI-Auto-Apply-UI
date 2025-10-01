<!--
Sync Impact Report
Version change: N/A → 1.0.0
Modified principles: (initial adoption) Added I–V
Added sections: Core Principles I–V; Additional Constraints — Security & Performance Standards; Development Workflow & Quality Gates; Governance
Removed sections: None
Templates:
- .specify/templates/plan-template.md — ✅ updated (version reference + path)
- .specify/templates/spec-template.md — ✅ verified aligned (no change)
- .specify/templates/tasks-template.md — ✅ verified aligned (no change)
Runtime docs: None present
Deferred TODOs:
- TODO(RATIFICATION_DATE): Original adoption date not recorded.
-->

<!--
Sync Impact Report
Version change: 1.0.0 → 1.1.0
Modified principles: None
Added sections: Coding Standards (Google-style comments + tooling gates)
Removed sections: None
Templates:
- .specify/templates/plan-template.md — ✅ updated (version reference + path)
- .specify/templates/spec-template.md — ✅ verified aligned (no change)
- .specify/templates/tasks-template.md — ✅ verified aligned (no change)
Runtime docs: None present
Deferred TODOs:
- TODO(RATIFICATION_DATE): Original adoption date not recorded.
-->

# Job-AI-Auto-Apply-UI Constitution

## Core Principles

### I. Library-First Architecture (NON-NEGOTIABLE)
MUST structure new capabilities as self-contained libraries with a clear purpose,
independent tests, and docs. Libraries expose narrow, stable contracts and avoid
cross-module reach-ins. Shared utilities MUST live in shared libraries, not copied.
Rationale: Modular boundaries enable parallel work, testing, and safe evolution.

### II. CLI/Text I/O Interface
Every library MUST expose a CLI with text protocols: stdin/args → stdout; errors →
stderr. Commands MUST support `--json` for machine consumption and human-readable
output by default. No interactive prompts without a non-interactive flag.
Rationale: Text I/O simplifies automation, observability, and testing.

### III. Test-First (TDD) (NON-NEGOTIABLE)
Write failing tests before implementation (Red → Green → Refactor). Contract tests
guard public interfaces; unit tests cover critical logic; integration tests validate
user journeys. Merges MUST demonstrate failing tests existed before code changes
or include equivalent evidence in history.
Rationale: Prevents regressions and drives better design.

### IV. Contract & Integration Testing Discipline
Public contracts (CLIs, APIs, schemas) MUST have explicit contract tests. Any
contract change REQUIRES updating tests first. Cross-boundary interactions and key
user flows MUST be covered by integration tests with realistic data.
Rationale: Ensures compatibility and end-to-end correctness.

### V. Observability, Versioning, and Simplicity
Emit structured, leveled logs; favor text outputs for reproducible debugging. All
contracts follow Semantic Versioning. Breaking changes REQUIRE a migration note and
MAJOR bump. Choose the simplest workable design (YAGNI) and remove accidental
complexity.
Rationale: Makes the system diagnosable and safely evolvable.

## Additional Constraints — Security & Performance Standards

- Secrets MUST NOT be committed. Use environment variables or secret stores.
- Dependencies MUST be pinned and scanned before release.
- User data handling MUST follow least privilege and minimal retention.
- Performance targets: interactive UI actions SHOULD complete p95 ≤ 200ms; background
  jobs SHOULD document target SLAs. Deviations MUST document rationale and monitoring.

## Coding Standards

The following coding and documentation standards are mandatory for all public
modules, classes, functions, and CLI commands.

### General Code Style
- Use an auto-formatter and linter appropriate to the language and commit their
  configuration at the repo root. CI MUST fail on style or lint violations.
- Prefer a soft line length of 100 characters.
- Naming conventions:
  - Python: `snake_case` for functions/vars, `PascalCase` for classes,
    `UPPER_SNAKE_CASE` for constants.
  - TypeScript/JavaScript: `camelCase` for functions/vars, `PascalCase` for
    classes/types, `UPPER_SNAKE_CASE` for constants; file names prefer `kebab-case`.
  - Other languages: follow their community standards with analogous mappings.
- Types are REQUIRED on all public interfaces (TypeScript types, Python type hints,
  etc.). CI MUST run a type check when available.
- Error handling: never swallow errors. Emit structured logs and return deterministic
  exit codes for CLI programs (`0` success; non-zero on failure).

### Commenting & Documentation (Google Style)
- Public interfaces MUST include doc comments that can be used to generate
  reference documentation. The Google documentation style is the normative
  reference for structure and section names.
- Section order: one-line summary; blank line; details; then `Args`/`Parameters`,
  `Returns`, `Raises`/`Throws`, `Examples`, and `Notes` as applicable.
- Module-level documentation belongs at the top of the file explaining purpose,
  key concepts, and invariants.
- Inline comments are for intent and non-obvious reasoning; avoid restating code.

Python example (Google-style docstring):

```python
def parse_resume(path: str) -> dict:
    """Parse a resume file into a structured profile.

    Args:
      path: Path to the resume file.

    Returns:
      A dictionary representing the parsed profile.

    Raises:
      FileNotFoundError: If the file does not exist.
      ValueError: If the format is unsupported.

    Examples:
      >>> parse_resume("cv.pdf")["name"]
      'Ada Lovelace'
    """
```

TypeScript/JavaScript example (JSDoc):

```ts
/**
 * Parse a resume file into a structured profile.
 *
 * @param path - Path to the resume file.
 * @returns Parsed profile.
 * @throws NotFoundError When the file does not exist.
 * @example
 * parseResume("cv.pdf").name; // "Ada Lovelace"
 */
export function parseResume(path: string): Profile { /* ... */ }
```

### Tooling Requirements (per language family)
- Python: formatter (e.g., Black), linter (e.g., Ruff/flake8), docstring checks
  aligned to Google style, and type check (e.g., mypy/pyright). Sphinx + Napoleon
  or MkDocs + mkdocstrings MAY be used to build docs from docstrings.
- TypeScript/JavaScript: Prettier + ESLint (including `eslint-plugin-jsdoc`),
  TypeScript type checks, and TypeDoc or JSDoc to generate reference docs.
- Other languages: configure the ecosystem-standard formatter, linter, type/static
  analysis, and doc tool (e.g., Javadoc, Doxygen) to consume the comment style.

### Documentation Gates
- Public symbols MUST be documented. Target 100% for public surface; minimum 90%
  doc coverage acceptable with justification in the PR.
- CI MUST build the reference documentation from comments and publish it as an
  artifact or to a `docs/` site when applicable.

## Development Workflow & Quality Gates

- Use `.specify/templates/plan-template.md` to create a feature plan. The plan MUST
  include a Constitution Check derived from this document.
- Follow TDD order in `.specify/templates/tasks-template.md`: tests → models →
  services → endpoints/UI → polish. Tests MUST fail before implementation begins.
- Contract changes MUST include updated contract tests and a version bump plan.
- PRs MUST state: Constitution Check status, affected contracts, and version impact.

## Governance

This Constitution supersedes other practice docs. All reviews MUST verify
compliance with Core Principles and Quality Gates.

Amendments: Propose via PR updating this file. Include a redline summary, a Sync
Impact Report (templates touched, sections added/removed), and migration guidance
if semantics change. Approval requires at least one maintainer and one developer
who did not author the change.

Versioning Policy: Use SemVer for the Constitution itself:
- MAJOR: Backward-incompatible governance/principle removals or redefinitions.
- MINOR: New principle/section added or materially expanded guidance.
- PATCH: Clarifications and non-semantic edits.

Compliance: Feature plans MUST include a Constitution Check. CI or reviewers MAY
reject changes that bypass mandatory tests or contract protections.

**Version**: 1.1.0 | **Ratified**: TODO(RATIFICATION_DATE) | **Last Amended**: 2025-10-01
