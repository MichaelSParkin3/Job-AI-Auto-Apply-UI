Here’s a fast, practical snapshot of what changed with **browser-use 0.7.9** (vs pre-0.7) and how to migrate.

# Biggest shifts in 0.7.x (incl. 0.7.9)

* **Event-driven core for agents.** You now get lifecycle **hooks** (`on_step_start`/`on_step_end`) and an internal **event bus** on the `browser_session` (e.g., dispatch a `ScreenshotEvent`), plus runtime controls like `pause()`, `resume()`, and `add_new_task()`. This makes orchestration reactive and composable. ([Browser Use][1])
* **Explicit session lifecycle.** `Browser` (alias of `BrowserSession`) is a first-class object you start/stop and reuse; you can manage tabs, inspect state, and keep the session alive to **chain tasks** (preserving cookies/storage). ([Browser Use][2])
* **CDP-first engine (Playwright optional).** 0.7 moved off a Playwright-centric core toward **pure CDP**, with optional Playwright **integration via CDP** when you need deterministic steps. This cuts flakiness and simplifies remote/real-browser support. ([SafetyCLI][3])
* **Remote/real browser + cloud.** Connect to a **cloud browser** (`use_cloud=True`) or any **CDP URL**; you can also attach to a **real Chrome profile** to reuse logins. ([Browser Use][4])
* **Observability & webhooks.** Built-in **webhooks** emit task status events (init/started/paused/stopped/finished), and **Laminar** tracing aligns the browser timeline with agent steps—handy for debugging and ops. ([Browser Use][5])
* **Model integrations cleaned up.** Use `ChatOpenAI`, `ChatAnthropic`, `ChatAzureOpenAI`, etc., and run agents **async** (`await agent.run(...)`). ([Browser Use][6])
* **Config surface updated.** `BrowserProfile` remains for backward compatibility but `Browser(...)` now takes the knobs directly; `Browser` == `BrowserSession`. ([Browser Use][7])

# Quick migration tips

1. **Update imports & async:**

   ```py
   from browser_use import Agent, Browser, ChatOpenAI
   agent = Agent(task="...", browser=Browser(), llm=ChatOpenAI(model="gpt-4.1-mini"))
   history = await agent.run(max_steps=..., on_step_start=..., on_step_end=...)
   ```

   (Switch any old sync calls to `await`.) ([Browser Use][8])

2. **Adopt event-driven hooks:** Move old “poll & check” logic into `on_step_start`/`on_step_end`. Use the **event bus** for side-effects (screenshots, custom signals). ([Browser Use][1])

3. **Preserve sessions:** For multi-step flows or chat UIs, keep the browser alive and **chain tasks** with `agent.add_new_task(...)` (or set keep-alive via profile). Cookies and local storage persist. ([Browser Use][9])

4. **CDP over Playwright (or mix deliberately):** Prefer `Browser(...)` with CDP. If you relied on Playwright APIs, use the **Playwright Integration** template to share the same Chrome and expose deterministic actions as **custom tools**. ([Browser Use][10])

5. **Real/remote browsers:**

   * Need your logged-in Chrome? Use **Real Browser** (`executable_path`, `user_data_dir`, `profile_directory`).
   * Running distributed? Use **Cloud** (`use_cloud=True`) or a provider’s **`cdp_url`**. ([Browser Use][11])

6. **Wire up ops:** Subscribe to **webhooks** for task status, and enable **Laminar** tracing for step-by-step time-aligned recordings. ([Browser Use][5])

7. **LLM swap-in:** Replace any legacy model wrappers with the new `Chat*` classes (OpenAI/Anthropic/Azure), set your env keys, and keep prompts minimal—0.7’s planner handles more. ([Browser Use][6])

8. **Know the aliases/back-compat:** `BrowserProfile` still works as a container for params if you’re migrating incrementally, but new code should pass settings to `Browser(...)`. ([Browser Use][7])

If you want, I can turn this into a short checklist for your repo and sketch a minimal 0.7.9 starter showing hooks + chained tasks + a remote CDP connection.

[1]: https://docs.browser-use.com/customize/hooks?utm_source=chatgpt.com "Lifecycle Hooks"
[2]: https://docs.browser-use.com/customize/actor/all-parameters?utm_source=chatgpt.com "All Parameters"
[3]: https://data.safetycli.com/packages/pypi/browser-use/changelog?utm_source=chatgpt.com "browser-use Changelog"
[4]: https://docs.browser-use.com/customize/browser/remote?utm_source=chatgpt.com "Remote Browser"
[5]: https://docs.browser-use.com/cloud/v1/webhooks?utm_source=chatgpt.com "Webhooks"
[6]: https://docs.browser-use.com/customize/supported-models?utm_source=chatgpt.com "Supported Models"
[7]: https://docs.browser-use.com/customize/browser/all-parameters?utm_source=chatgpt.com "All Parameters"
[8]: https://docs.browser-use.com/customize/browser/basics?utm_source=chatgpt.com "Basics"
[9]: https://docs.browser-use.com/examples/templates/follow-up-tasks?utm_source=chatgpt.com "Follow up tasks"
[10]: https://docs.browser-use.com/examples/templates/playwright-integration?utm_source=chatgpt.com "Playwright Integration"
[11]: https://docs.browser-use.com/customize/browser/real-browser?utm_source=chatgpt.com "Real Browser"
