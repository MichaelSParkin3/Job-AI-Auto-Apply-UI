# Research: Lever Auto‑Apply Assistant

Date: 2025-10-01  
Spec: G:\Github_Repos\Job-AI-Auto-Apply-UI\Job-AI-Auto-Apply-UI\specs\001-as-a-job\spec.md

## Decisions
- Use browser-use 0.7.x with CDP-first Browser sessions; headful by default.
- Default pacing: dwell 0.8s ±0.4s jitter; max parallel tabs 3; retries with backoff ×2.
- Allowed domains gate: google.* (search only), jobs.lever.co/*, company subpaths.
- Artifacts: screenshots + DOM snapshots always on failure; optional video/HAR when diagnostics is enabled.
- Discovery cap default 10; time window default 24h; supervised default (pause at final submit).

## Rationale
- CDP-first reduces flakiness and enables real/remote browser support.
- Human-like pacing avoids bot detection and server overload; limits keep sessions predictable.
- Domain gating improves safety and determinism in tests and during live runs.
- Minimal artifacts by default keep storage small; optional heavier traces aid debugging when needed.
- Default encryption off lowers setup friction; opt-in covers sensitive data.

## Alternatives Considered
- Playwright-first API → adds complexity and diverges from 0.7.x best practices; kept as optional tools.
- Cloud browsers by default → not required for MVP; local-first kept; cloud remains an advanced option.
- Always-on video/HAR → high storage/IO overhead; reserved for diagnostics.

## Open Items (tracked for planning)
- Proxy configuration matrix and validation.
- JSON schema for field mappings & confirmation capture (versioned in repo).

## Sources
- reference_files/patterns-google-lever.md — consolidated selectors and URL patterns for Google discovery and Lever pages
- reference_files/mvp-architecture.md — high-level flow and component responsibilities
- reference_files/browser-user-0.7.X-changes.md — hooks, event bus, CDP-first behavior
- reference_files/browser-use-testing-tips.md — testing layers, artifacts, CI advice
- reference_files/Automating_Lever_Job_Applications_with_Browser_Use.md — practical setup/stealth guidance
