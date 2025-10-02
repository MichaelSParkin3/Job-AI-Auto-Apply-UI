# Resume Upload Is Not Detected (Lever forms)

Owner hand‑off note (2025-10-02)

## TL;DR
- User can see the Lever UI showing an attached resume (filename/check icon or "Analyzing… → Success!").
- Our automation often logs: "Resume upload not detected" and proceeds as if nothing attached.
- Root tensions:
  - Some runs lack a native Playwright `Page.set_input_files`, so plain JS cannot set `input.files` (blocked by the browser).
  - Lever frequently re-creates or resets the file `<input>` after reading the file, so `input.files.length` may return 0 even when upload succeeded.
  - Success/failure banners are theme‑specific and sometimes controlled purely by CSS, so simple visibility checks can miss them.
  - Occasionally the apply page is guarded by hCaptcha; we bail out early for those forms.

## User symptoms and logs
- Supervised session; first job hit hCaptcha and failed fast (`captcha_blocked`).
- Next job(s) showed our prompt "Resume upload not detected. Please attach manually…" even though the user reports seeing the success UI.
- Provided HTML indicates the typical Lever markup:
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

### What the code currently does
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

## Why detection can still fail (hypotheses)
1) Input node churn
   - Lever may replace the `<input type="file">` after attaching, resetting `files`. Our polling references the original selector, which may now point to a new empty node before the success banner flips.
2) Storage id placement
   - Some Lever themes populate the storage id outside of `input[name='resumeStorageId']` or delay it beyond our polling window.
3) Visibility checks
   - Banners may be present but hidden behind an overlay, or displayed via virtualized subtrees. `getComputedStyle` on the banner node might report visible = false while users still see success text in another element.
4) Iframe boundary
   - Some implementations render the application form within an iframe. If we’re not using the frame’s context to select elements, our selectors succeed but the signals don’t represent the visual state the user sees.
5) BrowserSession feature gap
   - When `BrowserSession` is not backed by Playwright or its wrapper doesn’t fully expose Playwright APIs (`locator`, `set_input_files`, `expect_file_chooser`), we fall into manual mode. If manual upload finishes after we started polling (or the page swapped nodes), we might miss the state change.
6) Theme variants
   - Not all Lever tenants use `.resume-upload-success` or `span.filename`; some show the file name in a different span, or swap text nodes without changing visibility.

## Things we tried
- Switched from single `page.set_input_files` to a robust sequence (locator → page → filechooser → click+retry).
- Added post‑upload polling for multiple success indicators (files[], resumeStorageId, success banner, filename text) and early failure banners.
- Improved supervised fallback with an explicit prompt and re‑check after user action.

What worked
- On some postings (local tests), `locator.set_input_files` + filename text appeared quickly and was detected.
- Success banners were detected reliably when their computed style reflected visibility.

What did not (consistently)
- On user’s target pages, even with visible success indications, our polling returned false—likely due to input node replacement, theme differences, or iframe scoping.

## Related configuration and profile
- Profile used: `profiles/michael_scott_parkin_iii.toml` (location and pronouns defaults updated)
- Resume path resolution: `job_ai_auto_apply_ui/profile_manager.py` `Profile.resolve_resume_path` ensures absolute path (verify the resolved path exists and < 100MB).

## Concrete next steps for a senior dev
1) Verify Playwright surface
   - Ensure `BrowserSession` page object is a real Playwright `Page` with `locator`, `set_input_files`, and `expect_file_chooser` available.
   - If not, extend `BrowserSession` to expose a raw CDP channel.
2) Add CDP fallback (recommended)
   - Use `DOM.getDocument` → `DOM.querySelector` to get nodeId for the file input → `DOM.setFileInputFiles` with the absolute resume path.
   - Repeat this after clicking `.visible-resume-upload` because some tenants create the input lazily.
3) Re-scope to the correct frame
   - Detect if the form lives in an `<iframe>`; if so, use Playwright’s `frameLocator('iframe[…]')` (or equivalent) to run selectors/uploads within that frame.
4) Strengthen success detection
   - After each attempt, re-query the resume container root and re-derive selectors (guard against node swaps).
   - Add more signals: look for a non-empty text node near `.default-label` replacement, or a data attribute Lever sets (e.g., `data-resume-uploaded`).
   - Log a structured snapshot on failure: `{ files_len, has_storage_id, success_visible, filename_text, banner_texts }`.
5) Timing and retries
   - Increase poll timeout to 20–25s on slow themes.
   - Add a short retry loop that re-attempts upload if signals remain negative but the user stays on page.
6) Manual diagnostic mode (temporary)
   - Behind an env flag, dump `document.querySelector('.application-question.resume').outerHTML` to logs when detection fails.

## Pointers in code (start lines)
- Execute flow entry: src/job_ai_auto_apply_ui/browser_agent/lever.py:335
- Upload helper: src/job_ai_auto_apply_ui/browser_agent/lever.py:666
- Success wait: src/job_ai_auto_apply_ui/browser_agent/lever.py:729
- Profile path resolution: src/job_ai_auto_apply_ui/profile_manager.py:60

## Repro steps
1) Ensure resume exists and is < 100MB: `resumes/Michael_Parkin_Senior_Front_End_Developer_Resume_2025.pdf`.
2) Run supervised: `auto-apply apply --profile michael_scott_parkin_iii`
3) Observe the console around "Resume upload …" prompts and whether success is detected after ~1–3s.
4) If it fails, capture the form HTML around `.application-question.resume` and confirm where filename/success text actually shows.

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
