# Browser Use LLM Prompting — Comprehensive Notes (Last updated: 2025-10-02)

This app uses `browser-use` (CDP-first). This document aggregates the LLM-related prompting features across the library with deep links for day-to-day use and future design decisions.

— Contents
- Overview: Agent vs Page vs Tools
- Element Finding by Prompt (LLM)
- Page Content Extraction + Structured Output
- Agent Prompt Controls (system prompts, thinking, vision, output schemas)
- Built-in Tools (LLM-invoked) relevant to forms
- Custom Tools and CDP Access
- Prompting Tips & Patterns
- Examples
- References

## Overview: Agent vs Page vs Tools
- `Agent`: the high-level orchestrator that interprets your natural-language instructions, plans a sequence of actions, calls `Page` methods, and invokes tools. You can configure its LLM, system prompt, thinking/vision, output schema, limits, etc. See All Parameters. 
  - Docs: https://docs.browser-use.com/all-parameters
- `Page`: low-level browser surface; includes LLM-aware helpers like finding elements by prompt and extracting structured content.
  - Docs: https://docs.browser-use.com/python/references/page
- `Tools`: discrete capabilities the Agent can call via function-calling (e.g., `upload_file_to_element`, `click`, `fill`, etc.). You can add your own tools that receive a `cdp_client` and `browser_session`.
  - Docs: https://docs.browser-use.com/python/references/tools, https://docs.browser-use.com/customize/additional-tools

## Element Finding by Prompt (LLM)
Use these when CSS/XPath varies across tenants or when the DOM churns.
- `Page.get_element_by_prompt(prompt: str, …)` → best-match element or `None`.
- `Page.must_get_element_by_prompt(prompt: str, …)` → raises if not found.
- Returned `Element` typically exposes: `css_selector`, `xpath`, `backend_node_id`, `text`, `tag`.
- Docs: https://docs.browser-use.com/python/references/page, https://docs.browser-use.com/all-parameters#page

Example prompts
- "the resume upload input element (the <input type=\"file\"> used to attach a resume) inside the application form; not the submit button"
- "the visible button used to open the resume file chooser"

Notes
- Works well when combined with a CDP fallback (via `backend_node_id`) or when you feed the discovered `css_selector` back into Playwright/Browser Use for robust retries.

## Page Content Extraction + Structured Output
LLM-backed page parsing and structured extraction:
- `Page.extract_content()` returns the page’s textual/semantic content via an extraction LLM; you can override the model with `page_extraction_llm`.
- `Page.structured_output(model: type[T], llm=…)` lets you define a Pydantic/typed schema for LLM to return strongly-typed data (e.g., parsing application summaries or confirmation screens).
- Parameters (Agent level): `page_extraction_llm`, `include_attributes` (to enrich what the LLM sees), `sensitive_data` mask.
- Docs: https://docs.browser-use.com/all-parameters#page_extraction_llm, https://docs.browser-use.com/all-parameters#include_attributes, https://docs.browser-use.com/python/references/page

## Agent Prompt Controls (System, Thinking, Vision, Output Schemas)
- LLM selection & temperature: `llm`, `temperature`.
- System prompt customization: extend/override the Agent’s system prompt to steer style, safety, and tooling behavior.
- Thinking toggles: `use_thinking` (enable chain-of-thought style internal reasoning for planning), `flash_mode` (fast path, minimal thinking), `max_actions_per_step`, `max_actions_per_run`.
- Vision: `use_vision` to allow the LLM to reason over screenshots; `vision_detail_level` to tune fidelity/cost.
- Output schema: `output_model_schema` lets you specify a structured schema for the Agent’s final response—useful for contract tests.
- Conversation control & persistence: `save_conversation_path`, `final_response_after_failure`, `stop_on`, `calculate_cost`, `generate_gif` (for run visualizations), `available_file_paths` (tool sandboxing).
- Docs: https://docs.browser-use.com/all-parameters

Common settings we may use
- `use_thinking=false, flash_mode=true` for fast deterministic steps when we already know the DOM pattern.
- `use_vision=true` if the page has canvas-based widgets or visual-only success banners.
- `output_model_schema=<PydanticModel>` when we need typed output for downstream code.

## Built-in Tools (LLM-Invoked) Relevant to Forms
- `upload_file_to_element` — provide an element and local file path; handles file input upload.
- Navigation and interaction tools: `click`, `input_text`, `press_key`, `scroll`, and more; these are invoked by the Agent via function-calling when it decides actions based on your prompt.
- Docs: https://docs.browser-use.com/python/references/tools

## Custom Tools and CDP Access
- You can register custom tools that receive the active `cdp_client` and `browser_session`—perfect for targeted actions the generic LLM planner might struggle with, such as `DOM.setFileInputFiles` or frame attachment.
- Quick starts: adding tools to an Actor/Agent and exposing them with friendly names for prompts like “upload my resume via CDP if the regular upload fails.”
- Docs: https://docs.browser-use.com/customize/additional-tools, https://docs.browser-use.com/customize/actor/start#add-custom-tools

## Prompting Tips & Patterns
- Be specific about role and constraints: “Find the resume upload input (<input type='file'>) inside the application form, not the submit button.”
- Prefer outcome + guardrails: “If you cannot find the input by label, search for an adjacent anchor that triggers a file chooser; return its selector.”
- Provide context keys and labels: include visible labels, aria-labels, and container names (e.g., `.application-question.resume`).
- Pair LLM element discovery with deterministic actions: once an element is found, prefer deterministic upload via set_input_files or CDP.
- Use structured outputs: when asking the LLM to extract page state (e.g., Lever success banners, filename text), define a schema via `structured_output` and validate it.

## Examples

### 1) Targeted element finding + CDP upload (no Agent)
```python
from browser_use.llm.openai import ChatOpenAI

async def attach_resume_with_llm(page, resume_path: str):
    llm = ChatOpenAI(model="gpt-4.1-mini")  # pick your provider/model
    # Ask for the precise file input element inside the application form
    element = await page.must_get_element_by_prompt(
        "the resume upload input element (the <input type=\\"file\\"> used to attach a resume) inside the application form; not the submit button",
        llm=llm,
    )
    css = getattr(element, "css_selector", None)
    if css:
        # Try deterministic upload first if your wrapper exposes it
        try:
            await page.locator(css).set_input_files(resume_path)
            return True
        except Exception:
            pass
    # Fallback: use CDP programmatically
    await _cdp_set_file_input_files(page, css or "input[type='file']", resume_path)
    return True
```
Notes: `must_get_element_by_prompt` is LLM-backed. If your session lacks Playwright APIs, use the CDP fallback directly (see CDP helper in our lever agent).

### 2) Agent + Tools: upload via built-in tool
```python
from browser_use import Agent
from browser_use.llm.openai import ChatOpenAI

async def apply_with_agent(browser_session, resume_path: str):
    llm = ChatOpenAI(model="gpt-4.1-mini")
    agent = Agent(
        task=(
            "Find the resume upload input and attach the provided file. "
            "Prefer the built-in upload tool; only click visible anchors if needed."
        ),
        llm=llm,
        browser_session=browser_session,
    )
    # The Agent will internally use element-finding and may call tools like upload_file_to_element
    await agent.run()
```
Docs: https://docs.browser-use.com/python/references/tools

### 3) Custom tool using CDP (robust fallback)
```python
from pydantic import BaseModel
from browser_use import Tools, ActionResult

class UploadParams(BaseModel):
    selector: str
    path: str

tools = Tools()

@tools.action("Upload file via CDP to a selector", param_model=UploadParams)
async def upload_via_cdp(params: UploadParams, browser_session):
    # Resolve CDP client and call DOM.setFileInputFiles
    client = getattr(browser_session, "cdp_client", None) or getattr(browser_session, "cdp", None)
    if not client:
        return ActionResult(error="No CDP client available")
    send = getattr(client, "send", None) or getattr(client, "execute", None)
    if not callable(send):
        return ActionResult(error="CDP send method not available")
    await send("DOM.enable", {})
    doc = await send("DOM.getDocument", {"depth": -1, "pierce": True})
    root = (doc.get("root") or {}).get("nodeId")
    if not root:
        return ActionResult(error="No DOM root")
    q = await send("DOM.querySelector", {"nodeId": root, "selector": params.selector})
    node_id = q.get("nodeId") if isinstance(q, dict) else None
    if not node_id:
        return ActionResult(error="Selector not found")
    await send("DOM.setFileInputFiles", {"files": [params.path], "nodeId": node_id})
    return ActionResult(extracted_content=f"Uploaded {params.path} to {params.selector}")
```
Docs: https://docs.browser-use.com/customize/additional-tools

### 4) Structured page extraction after upload
```python
from pydantic import BaseModel

class UploadState(BaseModel):
    success: bool
    filename_text: str | None

async def read_upload_state(page, llm):
    return await page.structured_output(
        UploadState,
        prompt=(
            "Return whether the Lever UI indicates a successful resume upload, and the visible filename."
        ),
        llm=llm,
    )
```
Docs: https://docs.browser-use.com/python/references/page

### 5) Community example (adapt cautiously)
The following pattern circulates online showing an Agent with `Tools` actions that read a CV, save jobs, and upload a CV by indexing DOM elements.

Key takeaways we can reuse:
- Use `Tools.action` to expose high-level operations (save, read, upload) that the Agent can call via function-calling.
- If the page lacks stable selectors, allow the LLM to explore by index or by prompt, but prefer prompt-based targeting when available.
- For uploads, combine an index/prompt discovery step with a deterministic upload (`upload_file_to_element` tool or CDP fallback) rather than directly mutating `input.files` in JS.

Modernized sketch for 0.7.x-style APIs:
```python
import asyncio, csv
from pathlib import Path
from pydantic import BaseModel
from browser_use import Agent, Tools, ActionResult
from browser_use.llm.openai import ChatOpenAI

CV = Path.cwd() / "dummy_cv.pdf"
CV.write_text("Hi I am a machine learning engineer…", encoding="utf-8")

tools = Tools()

class Job(BaseModel):
    title: str; link: str; company: str; fit_score: float
    location: str | None = None; salary: str | None = None

@tools.action("Save jobs to CSV", param_model=Job)
def save_jobs(job: Job):
    with open("jobs.csv", "a", newline="") as f:
        csv.writer(f).writerow([job.title, job.company, job.link, job.salary, job.location])
    return "Saved"

@tools.action("Read my CV for context")
def read_cv():
    txt = CV.read_text(encoding="utf-8")
    return ActionResult(extracted_content=txt, include_in_memory=True)

@tools.action("Upload CV by prompt (fallback to index)")
async def upload_cv(browser_session, index: int | None = None):
    path = str(CV)
    # Prefer LLM element finding
    page = await browser_session.new_page()
    try:
        from browser_use.llm.openai import ChatOpenAI
        llm = ChatOpenAI(model="gpt-4.1-mini")
        el = await page.must_get_element_by_prompt(
            "the resume upload input element (<input type='file'>) inside the application form",
            llm=llm,
        )
        sel = getattr(el, "css_selector", None)
        if sel:
            try:
                await page.locator(sel).set_input_files(path)
                return "Uploaded via selector"
            except Exception:
                pass
        # CDP fallback
        from your_project.helpers import cdp_set_file_input_files
        await cdp_set_file_input_files(page, sel or "input[type='file']", path)
        return "Uploaded via CDP"
    except Exception:
        # Last resort: by index if your session exposes it
        if index is None:
            return ActionResult(error="No prompt match and no index provided")
        dom_element = await browser_session.get_element_by_index(index)
        if dom_element is None:
            return ActionResult(error=f"No element at index {index}")
        if not browser_session.is_file_input(dom_element):
            return ActionResult(error=f"Element at index {index} is not a file input")
        # Prefer the library's upload tool/event if available
        from browser_use.browser.events import UploadFileEvent
        event = browser_session.event_bus.dispatch(UploadFileEvent(node=dom_element, file_path=path))
        await event; await event.event_result(raise_if_any=True, raise_if_none=False)
        return "Uploaded via event bus"

async def main(browser_session):
    llm = ChatOpenAI(model="gpt-4.1-mini")
    agent = Agent(
        task=("Read my CV with read_cv, search for ML internships, save results, and be ready to upload the CV."),
        llm=llm,
        tools=tools,
        browser_session=browser_session,
    )
    await agent.run()
```
Use back-compat aliases noted in All Parameters (e.g., `controller` alias for `tools`, `browser`/`browser_session` aliases) if your version differs. Docs: https://docs.browser-use.com/all-parameters

## References
- Agent parameters (LLM, thinking, vision, output models, extraction LLM, limits):
  - https://docs.browser-use.com/all-parameters
- Page reference (LLM element finding, extraction helpers):
  - https://docs.browser-use.com/python/references/page
- Tools reference (upload, navigation, inputs):
  - https://docs.browser-use.com/python/references/tools
- Custom tools & CDP access:
  - https://docs.browser-use.com/customize/additional-tools
  - https://docs.browser-use.com/customize/actor/start#add-custom-tools

---

Historical note
- This file supersedes the shorter one-pager that originally lived under `specs/001-as-a-job/browser-use-llm-notes.md`. It aggregates additional Agent/Prompt features (thinking/vision/output schemas) we rely on as of browser-use 0.7.x.
