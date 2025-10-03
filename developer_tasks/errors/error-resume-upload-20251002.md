# Resume Upload Is Not Detected (Lever forms)

Owner hand‑off note (updated 2025-10-03)

## TL;DR
- As of Oct 02–03, 2025, resume uploads still fail on the user’s target postings.
- Two distinct failure modes observed:
  1) CDP transport flakiness: WebSocket closes or connect refused → we never reach the upload step; our form-root wait times out.
  2) When CDP is stable, upload success still isn’t detected on some tenants (likely input remount/iframe/shadow DOM).
- We implemented multiple code hardenings (details below), but the user’s latest runs fail before upload due to CDP disconnects/timing out on form selectors.

## User symptoms and logs
- Oct 02, 2025 (evening) and Oct 03, 2025 (morning) runs (Windows):
  - Repeated lines: `WebSocket connection closed: no close frame received or sent`.
  - Then: `Expected elements did not render in time` (our 12s guard wait) → item marked failed `runtime_error`.
  - Separate run: `FATAL: Failed to setup CDP connection: [WinError 1225] The remote computer refused the network connection`.
  - A later run ends with `asyncio.exceptions.CancelledError` on `Page.navigate`, followed by manual `KeyboardInterrupt`.
- Earlier supervised sessions (before CDP issues) prompted: `Resume upload not detected. Please attach manually…` despite visible success UI.
- Typical Lever markup seen in reference samples:
  - Anchor button `.visible-resume-upload` wraps a hidden `<input id="resume-upload-input" name="resume" type="file">`.
  - Banners exist for working/success/failure/oversize and a `span.filename` placeholder for the uploaded filename.

Example HTML (abridged):
- `li.application-question.resume … <a class="visible-resume-upload"> … <input id="resume-upload-input" name="resume" type="file"> … <span class="resume-upload-success">…Success!…</span> …`

## Current code paths and where to look
- Orchestrated browser apply flow:
  - src/job_ai_auto_apply_ui/browser_agent/lever.py:335 `LeverApplyAgent.execute_in_browser`
- Resume upload helpers (added/updated):
  - src/job_ai_auto_apply_ui/browser_agent/lever.py:666 `_upload_resume(page, selector, path)`
  - src/job_ai_auto_apply_ui/browser_agent/lever.py:729 `_wait_for_resume_upload(page, selector, timeout=12.0)`
- Success detection also consulted the hidden field:
  - `input[name="resumeStorageId"]` (Lever sets this when it has ingested the file)

### What the code currently does (before Oct 02)
1) Plan building in the live DOM detects the file input selector: typically `input#resume-upload-input[name='resume']`.
2) Resume upload attempts (in order):
   - `locator.set_input_files(selector, path)` (works even when input is hidden)
   - `page.set_input_files(selector, path)`
   - `expect_file_chooser()`; click `.visible-resume-upload`, then `file_chooser.set_files(path)`
   - Retry: click `.visible-resume-upload`, then `locator.set_input_files` again
3) After each attempt, we poll up to ~12s for success signals:
   - `input.files.length > 0`
   - A non-empty `input[name='resumeStorageId']`
   - `.resume-upload-success` is visible (via computed style)
   - `span.filename` under `.application-question.resume` contains text
   - We early‑fail if `.resume-upload-failure` or `.resume-upload-oversize` is visible
4) If programmatic upload is impossible (no Playwright APIs), supervised path explicitly prompts the user to upload manually, then re‑checks the above signals. In auto mode, we return `resume_upload_unsupported`/`resume_upload_failed`.

### Hardenings implemented Oct 02–03 (in repo)
- Switch to active tab after `goto` (Lever often opens the form in a new tab). File: src/job_ai_auto_apply_ui/browser_agent/lever.py:348
- Re-plan after clicking the upload anchor: brief idle, refresh selector (fallback to `input[type="file"]`) then retry `set_input_files`. File: src/job_ai_auto_apply_ui/browser_agent/lever.py (click_anchor_then_retry block)
- Expanded iframe attempts: frame scan 5 → 20 with presence check prior to `set_input_files`. File: src/job_ai_auto_apply_ui/browser_agent/lever.py (frame_locator loop)
- LLM locator improvements: alternate prompts when the first prompt fails; still logs `css_selector` and `backend_node_id` when available. File: src/job_ai_auto_apply_ui/browser_agent/lever.py (LLM locator block)
- Stronger CDP fallback: `DOM.getFlattenedDocument(pierce=true)` and pick first/best `INPUT[type=file]` (prefer `name='resume'`) then `DOM.setFileInputFiles` via `backendNodeId`. File: src/job_ai_auto_apply_ui/browser_agent/lever.py (_cdp_set_file_input_files)
- Event-bus fallback expanded: scan window 50 → 300 with early-exit on first success; still logs `scanned`/`matched`. File: src/job_ai_auto_apply_ui/browser_agent/lever.py (_eventbus_upload_resume)
- Post-success settle check: short re-check to avoid false positives if failure/oversize banners appear late. File: src/job_ai_auto_apply_ui/browser_agent/lever.py (_wait_for_resume_upload)

### Why it can still fail (updated hypotheses)
1) Input node churn
   - Lever may replace the `<input type="file">` after attaching, resetting `files`. Our polling references the original selector, which may now point to a new empty node before the success banner flips.
2) Storage id placement
   - Some Lever themes populate the storage id outside of `input[name='resumeStorageId']` or delay it beyond our polling window.
3) Visibility checks
   - Banners may be present but hidden behind an overlay, or displayed via virtualized subtrees. `getComputedStyle` on the banner node might report visible = false while users still see success text in another element.
4) Iframe/OOPIF boundary
   - Some Lever upload widgets mount inside cross‑origin OOPIFs. Main‑target DOM queries (and our current flattened‑DOM search) won’t see cross‑origin frames. We need Target‑domain child‑session attach to call `DOM.setFileInputFiles` inside that child target.
5) BrowserSession feature gap
   - When `BrowserSession` is not backed by Playwright or its wrapper doesn’t fully expose Playwright APIs (`locator`, `set_input_files`, `expect_file_chooser`), we fall into manual mode. If manual upload finishes after we started polling (or the page swapped nodes), we might miss the state change.
6) Theme variants
   - Not all Lever tenants use `.resume-upload-success` or `span.filename`; some show the file name in a different span, or swap text nodes without changing visibility.

## Things we tried (summary)
- Robust upload sequence (locator → page API → file chooser → anchor click+retry).
- Multi-signal success detection + “settle” loop.
- Supervised manual prompt and re-check.
- Tab switch after navigation to handle Lever’s “new tab” apply pages.
- Frame scan and LLM locator with prompt variants.
- CDP flattened‑DOM scan and event‑bus scan expansion.

What worked
- On some postings (local tests), `locator.set_input_files` + filename text appeared quickly and was detected.
- Success banners were detected reliably when their computed style reflected visibility.

What did not (consistently)
- On user’s target pages, even with visible success indications, our polling returned false—likely due to input node replacement, theme differences, or iframe scoping.

## Related configuration and profile
- Profile used: `profiles/michael_scott_parkin_iii.toml` (location and pronouns defaults updated)
- Resume path resolution: `job_ai_auto_apply_ui/profile_manager.py` `Profile.resolve_resume_path` ensures absolute path (verify the resolved path exists and < 100MB).

## Concrete next steps for a senior dev
1) Add OOPIF-aware CDP child‑target attach (highest impact)
   - Use Target.setAutoAttach(autoAttach=true, flatten=true) and/or Target.getTargets + Target.attachToTarget for type='iframe'. For each child session, `DOM.getFlattenedDocument` and call `DOM.setFileInputFiles` using `backendNodeId` of `INPUT[type=file]` (prefer `name='resume'`). Verify success inside that child session.
2) Add CDP reconnect on transport loss per item
   - On `WebSocket closed`/`CancelledError` around `Page.navigate` or our initial selector wait, tear down session, start a fresh `BrowserSession`, and retry the same item once before failing.
3) Extend initial form wait + selector set
   - Guard for up to 20s and include selectors: `form#application-form`, `#application`, `.posting-headline h2`, `[data-qa='job-description']`, and if present click `a.postings-btn.template-btn-submit[href*='/apply']` first.
4) Keep current upload fallbacks
   - Once the page is reachable and stable, our new re-plan, frame scan, LLM, flattened‑DOM and settle checks should suffice for same‑origin cases.

## Pointers in code (start lines)
- Execute flow entry: src/job_ai_auto_apply_ui/browser_agent/lever.py:335
- Upload helper: src/job_ai_auto_apply_ui/browser_agent/lever.py:666
- Success wait: src/job_ai_auto_apply_ui/browser_agent/lever.py:729
- Profile path resolution: src/job_ai_auto_apply_ui/profile_manager.py:60

## Repro steps
1) Ensure resume exists and is < 100MB: `resumes/Michael_Parkin_Senior_Front_End_Developer_Resume_2025.pdf`.
2) Run supervised: `auto-apply apply --profile michael_scott_parkin_iii --use-llm-locator --debug-resume-widget --resume-wait-timeout-seconds 25`
3) Observe the console around "Resume upload …" prompts and whether success is detected after ~1–3s.
4) If it fails, capture the form HTML around `.application-question.resume` and confirm where filename/success text actually shows.

## Known blocking errors (Oct 02–03)
- `WebSocket connection closed: no close frame received or sent` (transport dropped mid-run)
- `FATAL: Failed to setup CDP connection: [WinError 1225] The remote computer refused the network connection` (CDP endpoint unreachable)
- `asyncio.exceptions.CancelledError` during `Page.navigate` (likely the above transport loss)

## Notes about tabs
- In Browser‑Use, the first tab may show “loading agent”, and the apply form opens in a second tab. We now switch to the active page after navigation. If the CDP channel drops, this switch cannot occur and form waits will time out.

## Research ideas (web search)
- "Playwright set input files hidden input inside anchor"
- "Playwright filechooser not firing lever"
- "Chrome DevTools DOM.setFileInputFiles examples"
- "Lever application resumeStorageId theme variants"
- "Playwright file upload inside iframe"

## Decision log / changes so far
- Added multi-path Playwright upload + robust polling.
- Added manual supervised prompt + recheck.
- Broadened success detection to include filename span and computed visibility checks.
- Still reproducible on user’s target: indicates either frame scoping or tenant‑specific UI patterns not covered by our signals.

## Ask from senior dev
- Add CDP fallback and frame scoping to close the gap across BrowserSession variants and Lever tenant themes.
- Add structured debug snapshot on failure, plus an opt‑in dump of the resume widget subtree for tenant-specific analysis.
