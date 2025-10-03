# SOLVED: Lever Resume Upload Not Detected (2025-10-02 → 2025-10-03)

Status: solved in d8fba63 on 2025-10-03

Summary
- Symptom: On Lever forms, our app consistently failed to detect a successful resume upload and often never attached the file.
- Root causes (combined):
  1) Navigation/focus mismatch: the Browser-Use session sometimes navigated in another tab; our active page stayed on about:blank or on the loader. We then waited for the form in the wrong tab.
  2) Upload branch unavailability: Playwright-style APIs were not present on the wrapped page (locator/set_input_files/file chooser), and our older CDP fallback could not reliably bind to a working CDP client. Also, Lever disables the visible "Attach Resume/CV" button until location is set.
- Solutions implemented:
  - Robust navigation with verification + tab refocus (event-bus → CDP Page.navigate → page.goto) and then prefer the active page.
  - Typed CDP upload path (via session.get_or_create_cdp_session): Runtime.evaluate → DOM.setFileInputFiles(objectId).
  - Enable the widget first: fill the structured location field before attempting upload.
  - Broaden success detection (.application-upload-success and filename span) and keep hidden resumeStorageId as a strong signal.
  - Add structured logs and postmortems to make failures diagnosable (resume_upload.*, form.wait.*, apply.navigate.*).

What we tried (chronological)
1) Initial inspection: our multi-branch upload (locator/page/file chooser/LLM/iframe) + success polling; suspected success detection gaps.
2) Added logs; saw many runs timing out at the pre-form wait with url=about:blank → navigation was not sticking.
3) Implemented robust navigation pipeline and increased/parametrized pre-form wait. Also added stealth env to reduce fingerprint surprises.
4) BOM issue in queue JSON triggered loader error in Windows → fixed loader to accept utf-8-sig.
5) After navigation fixes: form rendered, but capabilities showed no Playwright methods; event-bus scan yielded scanned=0 → upload branches effectively no-op.
6) Implemented typed CDP path using Browser-Use’s CDP session. Also reordered flow to set location first (the "Attach" button is disabled until a location is chosen on some Lever tenants).
7) Broadened success detection to include .application-upload-success and filename span; added a brief settle re-check.
8) Re-tested: Snapshot showed files=1, storage_id_len>0, success_visible=true, filename populated. Application proceeded.

Evidence from the successful run
- apply.navigate.ok (href contains /apply)
- form.wait.found (form#application-form)
- resume_upload.start selector="#resume-upload-input"
- resume_upload.postmortem → { files: 1, storage_id_len: 36, success_visible: true, filename: "…Resume_2025.pdf" }

About the extra tab
- Likely caused by a new tab created during navigation or by Lever’s link behavior. We now refocus the active page after navigate (apply.page_focus.changed). A minor UX artifact is that a second tab may remain open; next refinement would be to close a stray about:blank tab if the session exposes a safe API to list/close pages.

Final implementation highlights
- Navigation: apply.navigate.start/ok/fail with verification and focus handoff.
- Upload: typed CDP Runtime.evaluate + DOM.setFileInputFiles(objectId).
- Form gating: set structured location before upload.
- Diagnostics: resume_upload.*, form.wait.*, postmortem snapshot, and optional debug widget snapshot.
- Resilience: tolerate utf-8 BOM queues; stealth env (TZ/LANG/LC_ALL); configurable pre-form wait.

Owner’s theory vs. observed
- User hypothesis: two tabs were opening; the active tab was the second one and the browser-use/CDP wasn’t wired to it. This matches what we saw earlier (about:blank waits). Refocus + verified navigate fixed this.
- My view: both the tab-focus and the lack of a reliable CDP upload path had to be solved. Once we refocused and used typed CDP (and enabled the widget via location), uploads started to succeed consistently.

Next steps (optional)
- Close stray about:blank tabs post-navigate if the session API allows.
- Add a short grace re-check before prompting for manual upload to avoid a prompt when success has just landed.
- Consider a quieter log mode for non-diagnostic runs.
