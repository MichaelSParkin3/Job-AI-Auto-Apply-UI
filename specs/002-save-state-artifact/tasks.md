# Tasks: Saved Form State & Audit Artifacts

1. Contract test: apply JSON includes saved_for_review with artifact paths [P]
2. Contract test: captcha_blocked includes artifact paths [P]
3. Contract test: submitted includes screenshot_after_path when auditing enabled [P]
4. Contract test: resume-job prefill+pause behavior with --json summary [P]
5. Contract test: replay-job resets status to in_progress [P]
6. Contract test: cleanup-artifacts dry-run summary and exit codes [P]
7. Data model: extend ApplicationStatus with pending_review
8. Data model: extend Artifacts with form_state_path, screenshot_before_path, screenshot_after_path
9. Orchestrator: add --review-mode, --audit-after-submit/--no-audit-after-submit flags
10. Orchestrator: add resume-job (prefill/pause, --submit) command
11. Orchestrator: add replay-job command (reset only)
12. Orchestrator: add cleanup-artifacts command with --profile/--older-than/--dry-run
13. Browser agent: implement _capture_form_state helper
14. Browser agent: implement _capture_full_page helper (full_page=True)
15. Browser agent: wire capture before submit for all outcomes
16. Browser agent: wire post-submit capture when enabled
17. Browser agent: implement _apply_saved_state (selector→name fallback)
18. Queue: add mark_pending_review and transitions validation
19. README update: new commands/flags and artifacts layout
20. Dev docs update: developer_tasks/dev_docs/app-workflow-overview.md flow changes
21. Spec 001 cross-reference: note 002 feature addition
22. Integration test: review-mode produces pending_review and artifacts
23. Integration test: resume-job prefill then submit path yields confirmation artifacts
24. Integration test: cleanup-artifacts removes only targeted files
25. Lint & format; update changelog/recent changes

Legend: [P] denotes tasks that can run in parallel.
