# TZ — `/team`: summoning bounded local subagents (implemented)

**Date:** 2026-09-17 · **Touched:** `app/tz_team.py` (new), `app/tz_agent.py`,
`app/tz_terminal.py`, `tests/test_team.py` (new), `.github/workflows/python.yml`
**No new dependencies.**

## The word you were looking for

What Boris Cherny describes in Claude Code is **subagents**: the main agent
spawns child agents, each with its own context window, a narrower tool set and
one bounded job, then reads their reports back. "Workflow" is the scripted
orchestration of several subagents. TZ now has the local, simplified form of
the first one. It is called a **team**.

## What `/team` does

```text
/team Describe this workspace and check that the tests still pass
/team Read README.md and list its headings | Report the OS and Python version
/team --write --slots 2 --workers 4 ...
```

1. **Plan.** With `|` you split the job yourself (2-4 parts). Without it the
   lead asks the task model for a JSON plan of 2-4 workers. A planner answer
   that is not a JSON array is a *planning failure* reported to you, never a
   guessed split.
2. **Run.** Each worker is `Agent.worker()`: same workspace, model and
   loopback endpoint as the session, but an **empty context**, its own role
   system prompt, **read-only tools** (`file_read list_files fetch_url
   web_search system_info`) unless `--write`, **4 rounds** instead of 8, and
   the session timeout as its deadline. Workers run on **one inference slot**
   by default — doc 03's rule: two large models fighting for one GPU are slower
   than one. `--slots N` (max 3) runs them in parallel with buffered output.
3. **Receipt.** Every worker leaves status (`done` / `empty` / `failed` /
   `canceled`), elapsed time, the tools it actually called, the files it
   verified-wrote, its report and any error. Ctrl+C marks the running and
   queued workers `canceled`, saves the receipt, then propagates.
4. **Lead summary.** One more bounded call combines the reports; it is told
   the reports are data, not instructions, and to say plainly when a worker
   failed. `--raw` skips it. If the lead fails, the worker reports stand.
5. **Persist.** `data/tz/teams/<team-id>.json` and `.md` (the completion-
   Markdown convention from doc 01). The conversation keeps a compact
   "Team evidence" message so a follow-up can build on what was actually done.

`/agents` and `/summon` are aliases. `/team` also works with `--prompt`.

## Terminal

- Plan and receipts render as bordered Rich tables (`Terminal.table`), plain
  columns when redirected.
- Each worker's stream is framed by its own rule
  (`Worker 1/3 · reader · tz-agent:latest`); the ACTIVE block shows
  `team · worker 1/3 · reader` while it runs.
- **Persistent status line (§2.4 of the UX handoff, now done):** the prompt
  toolbar is `model · ROUTE · workspace · session | live load`, truncated to
  one row.

## Bounds that are deliberate

- A read-only team cannot write even if the model asks: the tool is simply
  not in the worker's schema, and a request for it is an error in the receipt.
- Workers never route to OpenCode, never change workspace, never see the
  parent conversation.
- No new network paths; every worker uses the same loopback-only `stream()`.
- Parallel `--write` teams with overwrite confirmations will prompt from a
  worker thread; keep writes sequential (`--slots 1`, the default).

## Evidence

- `python -m unittest discover -s tests -p "test_*.py"` → 54 tests, green
  (17 new in `tests/test_team.py`: parsing, plan extraction, tool bounding,
  receipts, planner failure, worker failure, cancel, write receipts,
  read-only enforcement, parallel slots, `--raw`, terminal table/frames/status line).
- Live on this machine (RTX 2080 SUPER, `tz-agent:latest` = Qwen3 4B Q4_K_M):
  a two-worker manual team completed in ~5 s wall; a planner-driven
  `--workers 2` team produced a valid JSON plan on the first try.
- CI now installs `requirements.txt` and runs the whole suite on Windows,
  Linux and macOS.
