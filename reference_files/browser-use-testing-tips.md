Here’s a practical, “do-this-first” guide for **testing browser-use apps**—from unit-ish checks through CI-grade E2E—plus tiny code patterns you can drop in.

# What to test (three layers)

* **Unit-ish (fast):** test *your* custom actions/tools and prompt logic by **stubbing the LLM** and asserting outputs. Run with no real browser, or against a static page. Use async tests. ([pytest-asyncio][1])
* **Integration (agent + browser):** run an **Agent** against controlled targets (local fixtures, static pages, or a single public doc) and assert with **lifecycle hooks** and **agent history**. ([Browser Use][2])
* **E2E (CI):** run on a **remote/CDP or cloud browser** and capture traces, video, and HAR for flake triage. Use webhooks/tracing to observe runs. ([Browser Use][3])

---

# Runner & core plumbing

* **pytest + pytest-asyncio** for async tests/fixtures (`await agent.run(...)`). Keep tests small and isolated. ([pytest-asyncio][1])
* Prefer **CDP/Cloud in CI**: `Browser(cdp_url=...)` for your provider or `use_cloud=True` (set `BROWSER_USE_API_KEY`). This avoids local Chrome quirks in pipelines. ([Browser Use][3])
* Record **artifacts** on failures: video/HAR/trace directories via browser settings. ([Browser Use][4])

---

# Assertions that work for agents

* Use **lifecycle hooks** to assert step-by-step outcomes (URL, DOM, screenshots), or to pause/resume intelligently. Hooks expose `agent.history` (urls, actions, outputs) and `browser_session` helpers. ([Browser Use][2])
* Emit **screenshots** (event bus) when a step ends to attach to reports. ([Browser Use][2])
* Gate browsing with **allowed_domains** to keep tests deterministic. ([Browser Use][5])

---

# Observability & debugging in CI

* Turn on **Laminar tracing** to get synced agent-step timelines with the **actual browser recording**—gold for flaky runs and post-mortems. ([Browser Use][6])
* Optionally subscribe to **webhooks** to assert task status transitions (`started/paused/finished`) from your CI job. ([Browser Use][7])

---

# Keep tests stable (anti-flake tips)

* Make the LLM **deterministic** in tests (temperature 0, “fast/flash” modes) and keep prompts minimal. The **Fast Agent** template shows speed/determinism knobs. ([Browser Use][8])
* Use **explicit waits and pacing** (`wait_between_actions`, `minimum_wait_page_load_time`) instead of arbitrary sleeps. ([Browser Use][4])
* For critical, brittle interactions, expose a **custom deterministic tool** (e.g., via **Playwright Integration**) and let the agent call it—best of both worlds: agentic planning + precise selector steps. ([Browser Use][9])
* Capture **video/HAR** only on failure or in nightly E2E to keep CI fast. ([Browser Use][4])
* Isolate state: per-test `user_data_dir` (temp profile) or incognito (`user_data_dir=None`). Avoid reusing sessions across tests unless you’re explicitly testing chaining. ([Browser Use][4])

---

# Minimal pytest pattern (async + hooks + artifacts)

```python
# conftest.py
import os, tempfile, pytest, asyncio
from browser_use import Browser, ChatOpenAI, Agent
from browser_use.browser.events import ScreenshotEvent

@pytest.fixture(scope="session")
def llm():
    # Deterministic model for tests
    return ChatOpenAI(model="gpt-4.1-mini", temperature=0.0)

@pytest.fixture
async def browser_tmp():
    # Isolated profile per test; turn on useful debug outputs
    tmp = tempfile.mkdtemp(prefix="bu-profile-")
    b = Browser(
        user_data_dir=tmp,
        headless=True,
        allowed_domains=["*.example.com", "docs.browser-use.com"],
        wait_between_actions=0.2,
        record_video_dir="./artifacts/video",      # video on CI
        record_har_path="./artifacts/network/test.har",
    )
    await b.start()
    try:
        yield b
    finally:
        await b.kill()

async def assert_on_step(agent: Agent):
    # Thin, fast assertions inside the step loop
    state = await agent.browser_session.get_browser_state_summary()
    assert state.url is not None
    # snapshot on each step for reporting
    ev = agent.browser_session.event_bus.dispatch(ScreenshotEvent(full_page=False))
    await ev; await ev.event_result(raise_if_any=True, raise_if_none=True)
```

```python
# test_docs.py
import pytest
from browser_use import Agent

@pytest.mark.asyncio
async def test_docs_home(llm, browser_tmp):
    agent = Agent(
        task="Open https://docs.browser-use.com and report the page title.",
        llm=llm,
        browser_session=browser_tmp,
    )
    result = await agent.run(max_steps=3)  # pass hooks via on_step_start/End if needed
    assert "Browser Use" in result.final_result().strip()
```

* Hooks: `on_step_start`/`on_step_end` let you assert state and take screenshots per step. ([Browser Use][2])
* Artifacts: `record_video_dir` and `record_har_path` provide evidence for failures. ([Browser Use][4])

---

# Scaling up in CI

* Run a **matrix**: local Chrome (CDP) vs **cloud browsers** using `use_cloud=True` (no local setup). ([Browser Use][3])
* Parallelize cautiously (separate profiles per worker). If you need many agents at once, see the **Parallel Agents** template. ([Browser Use][10])
* Wire **Laminar** at process start so every run is traced automatically. ([Browser Use][6])
* For app-style QA, peek at the official **qa-use** project and the “Vibetest-Use” example (currently being updated for 0.7.x) as inspiration for an agentic QA harness. ([GitHub][11])

---

# Extra knobs worth knowing

* **allowed_domains / prohibited_domains**: constrain navigation for safety & determinism. ([Browser Use][5])
* **deterministic_rendering**: exists but marked ⚠️ not recommended—use only for debugging specific rendering-flake scenarios. ([Browser Use][4])
* **Real Browser**: connect to your Chrome profile when you *need* persistent auth flows (e.g., SSO) for E2E; close Chrome first. ([Browser Use][12])

---

## TL;DR recommended stack

* **pytest + pytest-asyncio** (async fixtures & tests) ([pytest-asyncio][1])
* **Browser(cdp_url=...)** locally; **`use_cloud=True`** in CI; **artifacts enabled** (video/HAR) ([Browser Use][3])
* **Lifecycle hooks** for assertions + **event bus** screenshots; **Laminar** for synced recordings & traces ([Browser Use][2])
* **Deterministic LLM** settings for tests; **Playwright-backed custom tools** for brittle steps ([Browser Use][8])

If you want, I can generate a small **`tests/` scaffold** (conftest, fixtures, CI YAML, and a couple of sample specs) tailored to your repo.

[1]: https://pytest-asyncio.readthedocs.io/?utm_source=chatgpt.com "Welcome to pytest-asyncio! — pytest-asyncio 1.2.0 ..."
[2]: https://docs.browser-use.com/customize/hooks "Lifecycle Hooks - Browser Use"
[3]: https://docs.browser-use.com/customize/browser/remote?utm_source=chatgpt.com "Remote Browser"
[4]: https://docs.browser-use.com/customize/browser/all-parameters "All Parameters - Browser Use"
[5]: https://docs.browser-use.com/customize/browser/all-parameters?utm_source=chatgpt.com "All Parameters"
[6]: https://docs.browser-use.com/development/observability "Observability - Browser Use"
[7]: https://docs.browser-use.com/cloud/v1/webhooks "Webhooks - Browser Use"
[8]: https://docs.browser-use.com/examples/templates/fast-agent?utm_source=chatgpt.com "Fast Agent"
[9]: https://docs.browser-use.com/examples/templates/playwright-integration?utm_source=chatgpt.com "Playwright Integration"
[10]: https://docs.browser-use.com/examples/templates/parallel-browser?utm_source=chatgpt.com "Parallel Agents"
[11]: https://github.com/browser-use/qa-use?utm_source=chatgpt.com "browser-use/qa-use"
[12]: https://docs.browser-use.com/customize/browser/real-browser?utm_source=chatgpt.com "Real Browser"
