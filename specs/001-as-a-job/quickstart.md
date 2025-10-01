# Quickstart: Lever Auto‑Apply Assistant

1. Create or select a profile with resume path and keywords.
2. Run discovery:
   - Human: `discover --profile my-profile`
   - JSON: `discover --profile my-profile --json > queue.json`
3. Start applying (supervised by default):
   - Human: `apply --profile my-profile`
   - Auto-submit: `apply --profile my-profile --auto`
4. Handle CAPTCHAs:
   - When blocked, note the job id and run `resume-job <id>` after manual solve.
5. Review logs and artifacts under `data/`.

Acceptance validation
- Discovery produces up to 10 new items within the last 24h.
- Supervised mode pauses on final submit; one-click approval proceeds.
- Submitted items record confirmation text or ID and final URL.
- Blocked items store DOM snapshot and screenshot; resume restores state to the step before CAPTCHA.
