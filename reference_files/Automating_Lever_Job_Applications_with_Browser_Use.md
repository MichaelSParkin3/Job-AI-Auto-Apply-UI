# Automating Lever Job Applications with Browser Use: Stealth Strategies and Best Practices

**Browser Use** is an open-source Python library that empowers AI agents
to control a web browser for tasks like navigating websites and filling
out forms
autonomously[\[1\]](https://onlyoneaman.medium.com/automating-form-filling-with-ai-part-2-085a037f410e#:~:text=Understand%20Browser%20Use%3A%20Browser%20Use,driven%20automation).
By integrating large language models (LLMs) (such as Google's Gemini or
OpenAI's GPT) with Browser Use, you can automate tedious job application
processes on platforms like Lever. This guide covers how to set up
Browser Use, leverage its features (including "stealth" options), and
use LLM intelligence to automatically apply for jobs while avoiding bot
detection.

## Setting Up Browser Use for Automation

1.  **Install Browser Use and Dependencies:** Browser Use relies on
    Playwright (for browser automation) and an LLM backend. Install the
    library and Playwright's browser binaries (e.g. Chromium) via pip.
    For example, you can create a virtual environment and run:
    `pip install browser_use playwright` and then
    `playwright install chromium`[\[2\]](https://onlyoneaman.medium.com/automating-form-filling-with-ai-part-2-085a037f410e#:~:text=python%20,install%20playwright%20langchain_google_genai%20browser_use%20aiofiles).
    This will fetch the necessary browser automation drivers.
2.  **Obtain an LLM API Key:** Browser Use works with LLMs (like
    Google's PaLM 2/Gemini via the ChatGoogle interface, or OpenAI's
    ChatGPT via ChatOpenAI). Sign up for the appropriate API (e.g. a
    free Gemini API
    key[\[3\]](https://github.com/browser-use/browser-use#:~:text=uvx%20playwright%20install%20chromium%20,shell)
    or an OpenAI API key) and put it in a `.env` file, e.g.
    `GEMINI_API_KEY=<your_key>` or set environment variables as needed.
3.  **Quickstart an Agent:** Import the Browser Use Agent and an LLM
    class in your Python code. For example:

```{=html}
<!-- -->
```
    from browser_use import Agent, ChatGoogle
    llm = ChatGoogle(model="gemini-2.0-flash-exp")  # using a fast Gemini model
    agent = Agent(
        task="Find the number of stars of the browser-use GitHub repo", 
        llm=llm
    )
    agent.run_sync()

This simple agent will use the LLM to interpret the task and control the
browser accordingly. (In this case, it would navigate to the repo and
find the star count.) Ensure everything is configured (Playwright
browser installed, API keys loaded) before running your agent.

1.  **Configure Browser Settings (Optional):** You can customize the
    browser context via `BrowserProfile` to fine-tune behavior. For
    example, to see the browser actions live, run in non-headless mode
    (`BrowserProfile(headless=False)`). You might also set a specific
    user data directory or profile if you want to preserve login
    sessions, or use an incognito profile with `user_data_dir=None` for
    each
    run[\[4\]](https://docs.browser-use.com/customize/browser/all-parameters#:~:text=User%20Data%20%26%20Profiles).
    Adjusting parameters like `wait_between_actions` (default \~0.5s)
    can throttle the speed of actions to human-like
    pacing[\[5\]](https://docs.browser-use.com/customize/browser/all-parameters#:~:text=,between%20agent%20actions%20in%20seconds).
    By default, Browser Use highlights interactive elements (e.g. input
    fields) to help the AI identify
    them[\[6\]](https://docs.browser-use.com/customize/browser/all-parameters#:~:text=AI%20Integration)
    -- this is useful for form-filling tasks.

## Automating Job Search and Navigation

Before filling out applications, the agent needs to find relevant job
postings. Lever hosts job pages at `jobs.lever.co/<company>/<job>`. You
can automate the discovery of these pages using Google search or Lever's
own site:

-   **Using Google to Find Lever Postings:** Instruct the agent to
    perform a Google search for the roles you want. For example, your
    agent's task prompt could be: *"Search Google for
    site:jobs.lever.co* `<keyword>` *jobs in* `<location>`*, then open
    the first 5 results in new tabs."* Browser Use's agent can handle
    multi-step workflows, including searching and opening multiple
    pages[\[7\]](https://docs.browser-use.com/examples/templates/fast-agent#:~:text=1,summary%20for%20each%20page).
    The agent will navigate to Google, enter the query, and click the
    results. You can even have it open each result in a new tab for
    parallel processing (as demonstrated in Browser Use examples, an
    agent can open multiple pages and switch between tabs to gather
    information)[\[7\]](https://docs.browser-use.com/examples/templates/fast-agent#:~:text=1,summary%20for%20each%20page).
    When using Google, consider adding a slight delay between searches
    to avoid Google's bot detection (the default action wait helps, but
    if doing many searches, pacing is important).
-   **Navigating to the Application Form:** Once a Lever job posting is
    open, the agent will see an **"Apply for this job"** button or an
    embedded application form. Instruct the agent to click the apply
    button if needed. Lever's application forms typically appear as an
    embedded form with fields for name, email, resume, cover letter, and
    possibly custom questions. The Browser Use agent will detect form
    fields on the page (it can parse the page's interactive elements and
    labels) and prepare to fill them out. If the application opens in a
    new page or modal, the agent can detect that as well. Ensure your
    task prompt clearly states to proceed to fill out or submit the
    application after opening the job post.

## AI-Powered Form Filling on Lever

One of Browser Use's strengths is accurately filling out online forms
using data you
provide[\[8\]](https://browser-use.com/#:~:text=Say%20goodbye%20to%20manual%20data,accurately%20fills%20out%20online%20forms).
By combining an LLM with the browser control, the agent can populate
forms with contextually appropriate information. Here are tips to
effectively auto-fill Lever application forms:

-   **Provide Personal Data and Resume:** Supply the agent with the
    information it needs to fill the form. This can be done by including
    your details in the task prompt or as context. For example, you
    might include: *"Fill out the application with my information:
    Name=John Doe, Email=johndoe@example.com, Phone=123-456-7890, etc."*
    Similarly, make your resume text or relevant details available to
    the agent (you could paste a summary into the prompt or have it read
    from a file). The agent/LLM will use these details to populate
    fields like name, email, LinkedIn URL, etc., rather than inventing
    data.
-   **Attach Files (Resume/Cover Letter):** Lever forms often require
    uploading a resume (and optionally a cover letter). Browser Use
    supports file uploads, but you must **whitelist the file paths**
    that the agent can access. When creating the Agent, use the
    `available_file_paths` parameter to specify the local path of your
    resume/CV (and cover letter, if
    separate)[\[9\]](https://docs.browser-use.com/customize/tools/add#:~:text=be%20used%20to%20do%20a,Whether%20action%20contains%20sensitive%20data)[\[10\]](https://docs.browser-use.com/customize/tools/add#:~:text=%2A%20%60browser_session%3A%20BrowserSession%60%20,Whether%20action%20contains%20sensitive%20data).
    For example:
    `agent = Agent(task=my_task, llm=llm, available_file_paths=["/path/to/Resume.pdf"])`.
    This ensures the agent is allowed to attach that file when it
    encounters an upload field. The agent will then handle clicking the
    "Upload" button and selecting the specified file.
-   **Leverage LLM for Dynamic Answers:** A powerful feature of using an
    LLM is that it can generate on-the-fly answers or text. For
    instance, if the application form has a question like "Why do you
    want to work here?" or requires a cover letter, the agent can use
    the LLM to draft a response based on the job description or your
    resume. In your prompt, encourage the agent to *"answer any
    application questions in a professional tone"*. Browser Use's
    integration allows the AI to fill forms with **"dynamic, realistic
    data"** rather than static
    text[\[11\]](https://onlyoneaman.medium.com/automating-form-filling-with-ai-part-2-085a037f410e#:~:text=In%20our%20previous%20article%2C%20we,tackling%20far%20more%20complex%20tasks).
    You might even instruct it to tailor each cover letter to the job
    posting (using details from the job listing). This can save time and
    make each application unique.
-   **Review and Customize Outputs:** While the AI can fill fields
    automatically, it's wise to review what it plans to submit. You can
    run the agent in a *dry-run* mode or have it output its filled
    values. For high-stakes fields like a personal statement, you might
    have the agent pause (or use a custom `ask_human` tool) to let you
    approve or edit the LLM-generated text before
    submission[\[12\]](https://docs.browser-use.com/customize/tools/add#:~:text=tools%20%3D%20Tools)[\[13\]](https://docs.browser-use.com/customize/tools/add#:~:text=%40tools,answer).
    This human-in-the-loop approach can ensure quality and correctness.
-   **Submission and Confirmation:** Instruct the agent to click the
    final **Submit** button once all fields are filled. The agent will
    proceed to submit and can be directed to note any confirmation
    number or message. (Optionally, have it save a screenshot or
    confirmation page text to verify the application went through.)

Browser Use has demonstrated end-to-end job application in its examples
(e.g. reading a CV, finding ML engineer roles, and applying in new tabs
autonomously)[\[14\]](https://github.com/browser-use/browser-use#:~:text=Image%3A%20AI%20Did%20My%20Groceries),
so the framework is capable of handling the entire flow from search to
form fill to submission.

## Stealth Features: Avoiding Bot Detection

When automating job applications, especially at scale, it's critical to
remain "stealthy" to avoid triggering anti-bot defenses (like Cloudflare
checks or site fraud detection). **Browser Use offers stealth-oriented
features** to help with this, and you can follow best practices to
further reduce detection risk:

-   **Use Browser Use Cloud for Anti-Bot**: The simplest way to bypass
    advanced anti-bot measures (like Cloudflare IUAM challenges or
    similar) is to use the **Browser Use Cloud** service. By
    initializing your browser with `use_cloud=True`, your agent runs on
    a cloud-based browser with built-in stealth
    capabilities[\[15\]](https://github.com/browser-use/browser-use#:~:text=Simply%20go%20to%20Browser%20Use,parameter).
    This cloud service is designed to bypass Cloudflare and other bot
    protections, reducing or eliminating CAPTCHA
    interruptions[\[16\]](https://github.com/browser-use/browser-use#:~:text=Stealth%20Browser%20Infrastructure).
    (You'll need a `BROWSER_USE_API_KEY` for this service.) The cloud
    setup provides *"stealth mode"* browsing with an advanced proxy pool
    and real browser
    fingerprints[\[17\]](https://browser-use.com/#:~:text=10%20concurrent%20sessions),
    making your automation appear more like genuine human traffic.
-   **Customize Browser Fingerprints Locally**: If you run Browser Use
    locally (without the cloud), you can still take measures to mimic a
    human browser. Use the `BrowserProfile` to set a common **user agent
    string** (e.g., a recent Chrome user agent) instead of any default
    that may reveal
    automation[\[18\]](https://docs.browser-use.com/customize/browser/all-parameters#:~:text=Device%20Emulation).
    Also run in **headful mode** (`headless=False`) so the browser
    behaves like a regular one (some anti-bot scripts detect headless
    Chrome by certain flags or missing properties). Browser Use allows
    you to remove default automation flags: for example, you can set
    `ignore_default_args=['--enable-automation']` to prevent Chrome from
    adding the `"Chrome is being controlled by automated test software"`
    flag[\[19\]](https://docs.browser-use.com/customize/browser/all-parameters#:~:text=,extensions).
    This helps eliminate the `navigator.webdriver` indicator that bots
    typically have.
-   **Proxy and IP Management**: Consider routing your traffic through
    proxies or VPNs if you plan to submit many applications. Browser Use
    supports setting a proxy server in the profile
    (`proxy=ProxySettings(server="http://<IP>:<port>", ...)`)[\[20\]](https://docs.browser-use.com/customize/browser/all-parameters#:~:text=Network%20%26%20Security).
    Using residential or other proxies can distribute requests so they
    don't all come from the same IP address in a short time. This is
    particularly useful if you're applying to many jobs on the same
    platform, as it reduces the chance of being flagged for suspicious
    activity.
-   **Throttle and Randomize Actions**: Human applicants take time to
    read and fill each form. Ensure your bot inserts slight delays and
    variability in its actions. You can keep the default
    `wait_between_actions` \~0.5 seconds, or even increase it a bit for
    human-like
    pauses[\[5\]](https://docs.browser-use.com/customize/browser/all-parameters#:~:text=,between%20agent%20actions%20in%20seconds).
    Adding a small random jitter to waits (e.g., 0.5--1.5 seconds) for
    each field or page load can simulate natural timing. Avoid
    submitting dozens of applications in mere seconds -- not only could
    that trigger detection, but some forms might not load properly if
    you rush. It's better to space out applications (e.g. a few minutes
    apart or at least several seconds per application).
-   **Avoid Patterns**: If you generate cover letters or answers with
    AI, try to inject some variety or personalization so that each
    application isn't identically worded (Lever might not detect this,
    but companies might notice if they compare). Also, if a site
    presents a CAPTCHA or anti-bot challenge, don't try to brute-force
    through it; pause the agent and handle it (or use the cloud service
    which has a higher success rate of avoiding those challenges).
-   **Test in Headed Mode First**: It's a good practice to run your
    automation visibly (with a real browser window) for a few trial
    applications. Watch how the agent fills the form -- this can help
    you catch any obvious robotic behavior (like jumping fields too
    quickly or mis-clicking something) and adjust the script or prompt.
    Once confident, you can run it headless or continue headful if
    resources allow.
-   **Stealth Mode from Browser Use**: Keep in mind that **Stealth
    Mode** is an offering of Browser Use's cloud
    platform[\[17\]](https://browser-use.com/#:~:text=10%20concurrent%20sessions).
    If you need the highest level of stealth (for example, some
    companies might have aggressive bot filters on their career pages),
    using the cloud with stealth mode enabled will handle a lot of
    low-level details like proper TLS fingerprints, solving challenges,
    etc. For most basic job applications on Lever, this may not be
    necessary, but it's an option if you encounter obstacles.

By following these measures, your automated job application agent will
behave more like a human user and less like a bot, greatly reducing the
chance of detection or blocking.

## Best Practices for Reliable Job Application Automation

Finally, here are some overarching best practices to ensure your
Browser Use agent runs smoothly and effectively:

-   **Break Down the Task Clearly:** Write your agent's `task` prompt
    with clear, step-by-step intentions. For example: *"Go to
    \[Company's Lever page\], click the Apply button, and fill in the
    application form with my details. Upload my resume and submit the
    application."* A well-specified instruction helps the LLM planner
    avoid confusion. If the process has multiple steps (search for jobs,
    open each, apply), you might script these as separate sub-tasks or
    ensure the agent can open multiple tabs and handle them
    sequentially.
-   **Monitor Agent Decisions:** While Browser Use agents can operate
    autonomously, it's wise to log their actions or keep an eye on the
    console output, especially early on. In non-flash mode, the LLM will
    "think" through steps -- you can log these thoughts to debug issues.
    If the agent misinterprets a form field or a button, you may need to
    refine the prompt (e.g., "the field labeled 'Phone' should get the
    phone number") or add a custom tool to handle that element.
-   **Utilize Tools for Complex Interactions:** Browser Use allows
    custom **Tools**, which are basically functions you can define and
    allow the agent to call for specific
    tasks[\[21\]](https://docs.browser-use.com/customize/tools/add#:~:text=Simply%20add%20,function)[\[13\]](https://docs.browser-use.com/customize/tools/add#:~:text=%40tools,answer).
    If you find the agent struggling with something (for instance, a
    multi-step widget or a tricky dropdown), you can create a tool that
    uses Playwright directly to perform that action, then expose it to
    the agent. This way, the heavy lifting is done by a deterministic
    script, and the LLM just decides when to use it. Common uses might
    be a tool to solve a CAPTCHA (integrating an external solver) or a
    tool to fetch data from a local database (like answers to common
    questions).
-   **Respect Website Terms and Load:** Automating applications should
    be done responsibly. Don't overload the server with rapid-fire
    requests (the human-like pacing tips above help with this). Also,
    ensure the content you submit is truthful and reviewed -- automation
    can speed up applying, but quality still matters for job
    applications.
-   **Multi-Platform Consideration:** Today it's Lever, but companies
    use various applicant tracking systems (Greenhouse, Workday, etc.).
    Browser Use can work on any site. If expanding beyond Lever,
    modularize your approach: maybe create re-usable prompts or
    sub-agents for each platform, since forms might differ. Keep your
    personal data and resume readily accessible to the agent, and adjust
    for each form's format.
-   **Safety and Debugging:** Use features like `record_video_dir` or
    `record_har_path` in `BrowserProfile` if you need to debug what the
    agent did in the
    browser[\[22\]](https://docs.browser-use.com/customize/browser/all-parameters#:~:text=Recording%20%26%20Debugging).
    A video or HAR file can show if the form was filled correctly.
    Additionally, handle exceptions in your code -- e.g., if the agent
    throws an error or times out on a page, catch it and possibly retry
    or log the issue for later analysis.

By adhering to these guidelines, you can create an AI-driven job
application assistant that swiftly fills out Lever forms for you, while
minimizing the chances of being flagged as a bot. Browser Use's
combination of browser automation and LLM intelligence provides a
flexible framework to not only apply to jobs en masse, but to do so in a
context-aware, adaptive
manner[\[23\]](https://onlyoneaman.medium.com/automating-form-filling-with-ai-part-2-085a037f410e#:~:text=taking%20automation%20to%20a%20whole,tackling%20far%20more%20complex%20tasks).
With stealth best practices in place, your agent can operate in the
background, applying to roles with realistic accuracy and speed --
saving you hours of manual data
entry[\[8\]](https://browser-use.com/#:~:text=Say%20goodbye%20to%20manual%20data,accurately%20fills%20out%20online%20forms)
while you stay under the radar.

**Sources:**

-   Browser Use README and Documentation -- Open-source browser
    automation with LLM
    integration[\[16\]](https://github.com/browser-use/browser-use#:~:text=Stealth%20Browser%20Infrastructure)[\[8\]](https://browser-use.com/#:~:text=Say%20goodbye%20to%20manual%20data,accurately%20fills%20out%20online%20forms)[\[1\]](https://onlyoneaman.medium.com/automating-form-filling-with-ai-part-2-085a037f410e#:~:text=Understand%20Browser%20Use%3A%20Browser%20Use,driven%20automation)
-   Browser Use Cloud Docs -- Stealth browser infrastructure for
    bypassing anti-bot
    measures[\[15\]](https://github.com/browser-use/browser-use#:~:text=Simply%20go%20to%20Browser%20Use,parameter)[\[17\]](https://browser-use.com/#:~:text=10%20concurrent%20sessions)
-   Aman Kumar, *"Automating Form Filling with AI"* -- Medium article on
    using Browser Use with Gemini LLM for realistic
    form-filling[\[11\]](https://onlyoneaman.medium.com/automating-form-filling-with-ai-part-2-085a037f410e#:~:text=In%20our%20previous%20article%2C%20we,tackling%20far%20more%20complex%20tasks)[\[24\]](https://onlyoneaman.medium.com/automating-form-filling-with-ai-part-2-085a037f410e#:~:text=python%20,install%20playwright%20langchain_google_genai%20browser_use%20aiofiles)
-   Browser Use Documentation -- API parameters and Tools for
    customization (e.g. proxy, user agent, file
    uploads)[\[20\]](https://docs.browser-use.com/customize/browser/all-parameters#:~:text=Network%20%26%20Security)[\[18\]](https://docs.browser-use.com/customize/browser/all-parameters#:~:text=Device%20Emulation)[\[9\]](https://docs.browser-use.com/customize/tools/add#:~:text=be%20used%20to%20do%20a,Whether%20action%20contains%20sensitive%20data)
-   Browser Use Examples -- Demonstrations of job application automation
    and multi-step agent
    tasks[\[14\]](https://github.com/browser-use/browser-use#:~:text=Image%3A%20AI%20Did%20My%20Groceries)[\[7\]](https://docs.browser-use.com/examples/templates/fast-agent#:~:text=1,summary%20for%20each%20page)

[\[1\]](https://onlyoneaman.medium.com/automating-form-filling-with-ai-part-2-085a037f410e#:~:text=Understand%20Browser%20Use%3A%20Browser%20Use,driven%20automation)
[\[2\]](https://onlyoneaman.medium.com/automating-form-filling-with-ai-part-2-085a037f410e#:~:text=python%20,install%20playwright%20langchain_google_genai%20browser_use%20aiofiles)
[\[11\]](https://onlyoneaman.medium.com/automating-form-filling-with-ai-part-2-085a037f410e#:~:text=In%20our%20previous%20article%2C%20we,tackling%20far%20more%20complex%20tasks)
[\[23\]](https://onlyoneaman.medium.com/automating-form-filling-with-ai-part-2-085a037f410e#:~:text=taking%20automation%20to%20a%20whole,tackling%20far%20more%20complex%20tasks)
[\[24\]](https://onlyoneaman.medium.com/automating-form-filling-with-ai-part-2-085a037f410e#:~:text=python%20,install%20playwright%20langchain_google_genai%20browser_use%20aiofiles)
Automating Form Filling with AI --- Part 2 \| by Aman Kumar \| Medium

<https://onlyoneaman.medium.com/automating-form-filling-with-ai-part-2-085a037f410e>

[\[3\]](https://github.com/browser-use/browser-use#:~:text=uvx%20playwright%20install%20chromium%20,shell)
[\[14\]](https://github.com/browser-use/browser-use#:~:text=Image%3A%20AI%20Did%20My%20Groceries)
[\[15\]](https://github.com/browser-use/browser-use#:~:text=Simply%20go%20to%20Browser%20Use,parameter)
[\[16\]](https://github.com/browser-use/browser-use#:~:text=Stealth%20Browser%20Infrastructure)
GitHub - browser-use/browser-use: Make websites accessible for AI
agents. Automate tasks online with ease.

<https://github.com/browser-use/browser-use>

[\[4\]](https://docs.browser-use.com/customize/browser/all-parameters#:~:text=User%20Data%20%26%20Profiles)
[\[5\]](https://docs.browser-use.com/customize/browser/all-parameters#:~:text=,between%20agent%20actions%20in%20seconds)
[\[6\]](https://docs.browser-use.com/customize/browser/all-parameters#:~:text=AI%20Integration)
[\[18\]](https://docs.browser-use.com/customize/browser/all-parameters#:~:text=Device%20Emulation)
[\[19\]](https://docs.browser-use.com/customize/browser/all-parameters#:~:text=,extensions)
[\[20\]](https://docs.browser-use.com/customize/browser/all-parameters#:~:text=Network%20%26%20Security)
[\[22\]](https://docs.browser-use.com/customize/browser/all-parameters#:~:text=Recording%20%26%20Debugging)
All Parameters - Browser Use

<https://docs.browser-use.com/customize/browser/all-parameters>

[\[7\]](https://docs.browser-use.com/examples/templates/fast-agent#:~:text=1,summary%20for%20each%20page)
Fast Agent - Browser Use

<https://docs.browser-use.com/examples/templates/fast-agent>

[\[8\]](https://browser-use.com/#:~:text=Say%20goodbye%20to%20manual%20data,accurately%20fills%20out%20online%20forms)
[\[17\]](https://browser-use.com/#:~:text=10%20concurrent%20sessions)
Browser Use - The AI browser agent

<https://browser-use.com/>

[\[9\]](https://docs.browser-use.com/customize/tools/add#:~:text=be%20used%20to%20do%20a,Whether%20action%20contains%20sensitive%20data)
[\[10\]](https://docs.browser-use.com/customize/tools/add#:~:text=%2A%20%60browser_session%3A%20BrowserSession%60%20,Whether%20action%20contains%20sensitive%20data)
[\[12\]](https://docs.browser-use.com/customize/tools/add#:~:text=tools%20%3D%20Tools)
[\[13\]](https://docs.browser-use.com/customize/tools/add#:~:text=%40tools,answer)
[\[21\]](https://docs.browser-use.com/customize/tools/add#:~:text=Simply%20add%20,function)
Add Tools - Browser Use

<https://docs.browser-use.com/customize/tools/add>
