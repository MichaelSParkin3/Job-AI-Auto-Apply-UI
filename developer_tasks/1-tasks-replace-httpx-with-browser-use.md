# Task: Replace `httpx` with `browser-use` for Web Scraping

**Date:** 2025-10-02

## Background
The project's technical specifications mandate the use of `browser-use` for all web interactions to ensure consistent, robust, and stateful automation that can handle JavaScript-heavy sites and avoid bot detection.

- **`specs/001-as-a-job/research.md`**: Explicitly states the decision to "Use browser-use 0.7.x with CDP-first Browser sessions; headful by default."
- **`specs/001-as-a-job/plan.md`**: Details a "Browser agent for Lever" responsible for a "Headful session; resume upload; contact+links; dynamic cards; submit".

The current implementation deviates from this plan. It incorrectly uses the `httpx` library for critical web scraping tasks in both the `discover` and `apply` commands. This has led to runtime errors (like the `xml.etree.ElementTree.ParseError`) and incorrect behavior (no browser window opening during the apply step).

## Objective
Refactor the `discover` and `apply` commands to replace all `httpx` calls used for scraping web page content with `browser-use` sessions. This will align the implementation with the original design, improve reliability, and enable the system to handle dynamic web content correctly.

---

## Developer Tasks

### Part 1: Fix `apply` Command in `orchestrator.py`

The `apply` command currently fetches the application form's HTML using a background `httpx` request, which is why no browser window appears and why it fails on complex HTML.

- **File to Modify:** `src/job_ai_auto_apply_ui/orchestrator.py`

#### Tasks:
- [ ] **1.1: Remove the `httpx`-based `_default_form_fetch` function.**
  - This function is the source of the issue in the `apply` flow. It should be completely removed.

- [ ] **1.2: Modify the `iter_apply_events` function to use `browser-use`.**
  - In the loop where it processes each `item` from the queue, you must initiate a browser session to fetch the form HTML.
  - **Pattern to Follow:** The `_load_search_results_with_browser` function in `src/job_ai_auto_apply_ui/job_discovery.py` provides the correct pattern for starting a `BrowserSession`.
  - **Implementation Steps:**
    1.  Inside the `for item in pending:` loop, instantiate a `BrowserSession` using the `LeverBrowserOptions`.
    2.  Start the session: `await session.start()`.
    3.  Get the current page: `page = await session.get_current_page()`.
    4.  Navigate to the job's `apply_url`: `await page.goto(apply_url)`.
    5.  Retrieve the page's HTML content: `form_html = await page.evaluate('() => document.documentElement.outerHTML')`.
    6.  Ensure the session is properly stopped in a `finally` block: `await session.stop()`.
  - **Reference:** This change will bring the `apply` command in line with the "Application Session" and "Form Fill and Upload" flows described in `reference_files/mvp-architecture.md`.

### Part 2: Fix `discover` Command in `job_discovery.py`

The `discover` command correctly uses `browser-use` for the main Google search, but then incorrectly uses `httpx` to fetch the details from each individual job posting link.

- **File to Modify:** `src/job_ai_auto_apply_ui/job_discovery.py`

#### Tasks:
- [ ] **2.1: Remove the `httpx`-based `_default_fetch` function.**
  - This function is used as a fallback and for fetching posting details. It should be removed to enforce a browser-only workflow.

- [ ] **2.2: Modify `discover_jobs` to use the existing browser session for fetching posting details.**
  - The function already has an active `BrowserSession` from `_load_search_results_with_browser`. This session should be reused.
  - **Implementation Steps:**
    1.  The `discover_jobs` function needs access to the `session` object created in `_load_search_results_with_browser`. You will need to refactor the code to pass the active `session` into `discover_jobs` or manage the session at a higher level.
    2.  Inside the `for result in results:` loop, replace the call to `posting_html = fetch_posting(result.url)` with a browser action.
    3.  Open a new tab for the job posting: `posting_page = await session.new_page()`.
    4.  Navigate to the URL: `await posting_page.goto(result.url)`.
    5.  Get the HTML: `posting_html = await posting_page.evaluate('() => document.documentElement.outerHTML')`.
    6.  Close the tab after you are done to conserve resources: `await posting_page.close()`.
  - **Reference:** This aligns with the "multi-tab navigation" concept mentioned for `job_discovery` in `reference_files/mvp-architecture.md`.

- [ ] **2.3: Remove the `httpx` fallback logic in `discover_jobs`.**
  - The `try...except` block that calls `_load_search_results_with_browser` and then falls back to `_default_fetch` should be removed. If the browser-based discovery fails, the command should fail clearly, as this is a critical failure, not something to be worked around with a less reliable method.

### Part 3: Update and Write Tests

- [ ] **3.1: Update existing tests.**
  - Any unit or integration tests that were mocking `httpx` calls (like `_default_form_fetch`) will now fail. These tests must be updated to mock the `BrowserSession` and its methods (`start`, `goto`, `evaluate`, `stop`, etc.) instead.

- [ ] **3.2: Write a new integration test.**
  - Create a new integration test that runs the `apply` command for a single item from a fixture. This test should assert that a `BrowserSession` is created and that it navigates to the correct URL. You can use mocking to prevent the browser from actually running while still asserting that the correct calls were made.

### Part 4: Final Polish & Verification

- [ ] **4.1: Run the linter.**
  - After making all code changes, run `ruff check .` and fix any new issues.

- [ ] **4.2: Run the full test suite.**
  - Ensure all existing and new tests pass by running `pytest`.

---

## Guidance on Testing `browser-use`

Consult `reference_files/browser-use-testing-tips.md` for in-depth patterns. Key strategies include:

- **Use `pytest-asyncio`:** All browser interactions are asynchronous, so your tests must be marked with `@pytest.mark.asyncio`.
- **Mock the Browser, Not Just the Network:** Instead of mocking `httpx`, you will need to mock the `BrowserSession` object itself or the factory function that creates it (`_default_browser_factory`). Use `unittest.mock.AsyncMock` for async methods.
- **Use Fixtures for Static HTML:** For unit tests of the parsing logic (like `analyze_form`), continue to use local HTML file fixtures. The goal is not to test the browser but to test your code's reaction to the HTML.
- **Lifecycle Hooks for Integration Tests:** For higher-level tests, `browser-use` provides `on_step_start` and `on_step_end` hooks. These can be used to make assertions about the browser's state (e.g., the current URL) at each step of the agent's execution, providing a robust way to test without complex mocks.

---

## Validation Steps

After implementing the changes, verify the fixes by running the following checks:

- [ ] **Run the `apply` command:**
  - **Command:** `auto-apply apply --profile michael_scott_parkin_iii`
  - **Expected Outcome:** A browser window should open and navigate to the first job application page in the queue. The `xml.etree.ElementTree.ParseError` should no longer occur.

- [ ] **Run the `discover` command:**
  - **Command:** `auto-apply discover --profile michael_scott_parkin_iii`
  - **Expected Outcome:** Observe the browser window. After the initial Google search, the browser should open new tabs and navigate to each of the `jobs.lever.co` URLs one by one to scrape their content.

## Key References
- **Project Plan:** `specs/001-as-a-job/plan.md`
- **Architecture Overview:** `reference_files/mvp-architecture.md`
- **Browser-use Best Practices:** `reference_files/Automating_Lever_Job_Applications_with_Browser_Use.md`
- **Browser-use Session Lifecycle:** `reference_files/browser-user-0.7.X-changes.md`
- **Browser-use Testing Guide:** `reference_files/browser-use-testing-tips.md`
