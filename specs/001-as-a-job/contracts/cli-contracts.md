# CLI Contracts

## discover
- Command: `discover --profile <name> [--window <hours>] [--cap <int>] [--json]`
- Input: profile name; time window (default 24); cap (default 10)
- Output (JSON when `--json`):
```
{
  "items": [
    {"id":"01H...","url":"...","company":"...","title":"...","discovered_at":"..."}
  ]
}
```
- Exit codes: 0 success; 2 no results; 1 other errors

Schema: `contracts/schemas/discover.schema.json`

## apply
- Command: `apply --profile <name> [--auto|--supervised] [--json]`
- Output stream (JSON lines when `--json`):
```
{"event":"start","profile":"<name>"}
{"event":"item","id":"...","status":"in_progress"}
{"event":"submitted","id":"...","confirmation_id":"..."}
{"event":"failed","id":"...","reason":{"code":"captcha_blocked","message":"..."}}
{"event":"end","summary":{"submitted":N,"failed":M}}
```
- Exit codes: 0 success; 3 partial failures; 1 fatal error

Schema (per line): `contracts/schemas/apply-event.schema.json`

## resume-job
- Command: `resume-job <id> [--json]`
- Output (JSON when `--json`):
```
{"id":"...","status":"in_progress","resumed_from_step":3}
```
- Exit codes: 0 success; 4 not found; 1 other errors

Schema: `contracts/schemas/resume-job.schema.json`
