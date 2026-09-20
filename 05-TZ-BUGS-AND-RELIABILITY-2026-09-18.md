# TZ Bugs and Reliability — 2026-09-18

Source: Roman's test session on 2026-09-18 (three runs of `roman`, two in PowerShell, one in cmd). He rated the first run "totally unsuccessful". Each bug below is quoted from the transcript, traced to the code, and given a fix. Priority order is the order listed.

Roman's headline complaint: *"sometimes it says it can't access the browser and sometimes it says it does"* — same model, same kind of request, different outcome. That is **B1**. Fix B1 and B2 and most of his frustration goes away.

---

## B1 — "Open the browser and look up X" is left to the model's mood

**Observed (PowerShell run 1, `tz-agent:latest`):**
```
Me > open it in the browser for me
AI  > I'm unable to open a browser for you as I don't have direct access to your device's browser...
Me > open the web browser and type in what time is it in new mexico?
AI  > I'm unable to open your web browser or type commands into it directly.
Me > open the webbrowser
AI  > I'm unable to open your web browser directly.
```
**Observed (cmd run, same model, minutes later):**
```
Me > hello can u opent the browser and look up lil waynes most recent track
[tool] open_target {"opened": "https://www.google.com/search?q=lil+wayne+most+recent+track"}
```
Same again in PowerShell run 3 ("opent the web rbwoser so i can see it" → `open_target` worked).

**Root cause:** `Agent.direct()` in `app/tz_agent.py` (around line 463) is the deterministic, no-model path. Its only browser rule is:
```python
m = re.fullmatch(r'(?:open|launch)\s+(https?://\S+)', s, re.I)
```
It only fires on a literal URL. Any natural phrasing ("open the browser and look up…", "open it in the browser", "open the webbrowser") falls through to the 4B model, which has `open_target` in its tool list but sometimes decides it "can't access the browser". Qwen3 4B at Q4 is nondeterministic at the default temperature; the shell (PowerShell vs cmd) has nothing to do with it — both run `python tz.py`.

**Fix:**
1. Add deterministic intents to `direct()` **before** the URL rule:
   - `open (the|my|a)? (web ?)?browser (and|to)? (look up|search( for)?|type( in)?|google|find) <query>` → `open_target` with `https://www.google.com/search?q=<urlencoded query>`.
   - `(look up|search|google) <query> (in|on) (the )?(web ?)?browser` → same.
   - `open (it|that|this) in (the )?browser` / `open the (web ?)?browser so i can see (it)?` when there is a previous `web_search` or `fetch_url` in `self.messages` → open the last search query on Google (or the last fetched URL).
   - Bare `open (the )?(web ?)?browser` → open `https://www.google.com`. Better than refusing.
2. Add one sentence to `SYSTEM` (line 35): *"open_target opens the user's real default browser on this machine; when the user asks to open, show, or look something up in the browser, call open_target with a search URL instead of saying you cannot."* This covers phrasings the regexes miss.
3. Tests in `tests/test_tz.py`: parametrize the phrasings above (including Roman's typos: "opent", "webbrowser", "rbwoser" — at least the first two) and assert `direct()` returns `('open_target', {...google URL...})` without calling Ollama.

**Roman's own insight, worth honoring:** modern browsers already have AI in the address bar. For "look up X" requests, opening a Google search in the real browser gives him more than the 4B model summarizing snippets. So make "open the browser" the *easy* path, not the fallback.

---

## B2 — `web_search` (Bing RSS) returns junk

**Observed (three separate queries):**
| Query | Top results |
|---|---|
| `current time in Albuquerque NM` | current.com (a bank), Baidu dictionary entry for "current", Wikipedia "Electric current" |
| `best recipe for chicken soup` | bestbuy.com, Merriam-Webster "best", Cambridge "best" |
| `James Gandolfini biography` | alistamento.eb.mil.br (Brazilian military enlistment), eight times |

**Root cause:** `execute()` → `web_search` (line ~318) hits `https://www.bing.com/search?format=rss&q=...`. The results look like Bing is matching only the first token, or returning cached junk for the RSS endpoint. Either way, the provider is unreliable now.

**Fix:**
1. Verify from the shell first so the next Claude does not guess:
   ```bash
   curl -s -A "Mozilla/5.0" "https://www.bing.com/search?format=rss&q=James+Gandolfini+biography" | head -c 3000
   ```
2. Replace or supplement the provider. Candidates, stdlib only:
   - DuckDuckGo HTML endpoint `https://html.duckduckgo.com/html/?q=<query>` (parse `<a class="result__a">` and `<a class="result__snippet">` with `PageText`-style HTMLParser). Needs a browser-like `User-Agent`, which `get_url()` may already send — check.
   - Keep Bing RSS as a second provider and try providers in order, returning the first set of results that actually contains a query term.
3. **Relevance guard:** after fetching, count results whose title+snippet contain at least one non-stopword query term (len ≥ 4). If zero, raise `ValueError('Search returned no relevant results for: <query>. Use /open to search in the browser.')` instead of handing the model garbage. This directly prevents B3.
4. Tests: mock `get_url` and assert (a) DDG HTML parses into `{title,url,snippet}`; (b) the relevance guard rejects the "Current bank" result set for the Albuquerque query.

---

## B3 — Model hallucinates when search results are irrelevant

**Observed:** after the Gandolfini junk results, `tz-agent:latest` produced a confident biography with **wrong facts**: born 1940 (real: 1961), died January 2009 (real: June 2013), starred in *The Godfather Part II* (1979) and *The Man Who Knew Too Much* (1956) — none of it true. `SYSTEM` says "Do not claim live facts from memory", but a 4B model ignores that when it has nothing else.

**Fix:** B2's relevance guard is the main fix (the model gets a tool error, and the error text tells it to use `/open`). Additionally, add to `SYSTEM`: *"If a search or fetch result does not answer the question, say so and offer open_target; never fill the gap from memory."* Test: a converse round where the tool returns the guard error should not produce a tool-free answer longer than ~80 words — hard to unit test against a live model; make it a manual check in `TZ-QUICK-TEST-GUIDE.md`.

---

## B4 — "What time is it in X" needs no web at all

**Observed:** "look up the time in Albuquerque NM" → `fetch_url` → `HTTP Error 403: Forbidden` (time sites block bots) → then the junk search. Two tool calls, 30 seconds, no answer.

**Fix:** Python 3.9+ has `zoneinfo` (Windows needs the `tzdata` package — check `python -c "import zoneinfo; zoneinfo.ZoneInfo('Asia/Tokyo')"`; if it fails, add `tzdata` to `requirements.txt`, it is pure-Python and tiny).
1. Add a `local_time` tool: `{'zone': STR}` → returns ISO time, UTC offset, and the zone name. Include a small alias table for the phrases Roman actually uses: `japan → Asia/Tokyo`, `new mexico|albuquerque → America/Denver`, `portsmouth nh|new hampshire|boston|new york|nyc → America/New_York`, `london → Europe/London`, `california|la|los angeles → America/Los_Angeles`, etc. Unknown place → error telling the model to use open_target.
2. `direct()` intent: `what time is it in <place>` / `time in <place>` / `look up the time in <place>` → `local_time`. Deterministic, sub-second, no model.
3. Tests: alias table lookups and a fixed-`now` formatting test.

This also becomes the first preset in the UI's "Search" icon (doc 06), since Roman named "time in Japan" as one of his repeated questions.

---

## B5 — Big models exceed the 90 s timeout and AUTO can pick them

**Observed:**
- `/use qwen3.6:latest` (36B MoE) → 90 s timeout, no output.
- `/use gemma4:26b` → canceled at 50 s.
- `/auto` then "open the web browser and look up where the statue of liberty came from" → `[route] AUTO → gemma4:26b · task / context` — AUTO kept the pinned 26B model as the task model, so the "reset" did not reset.

**Root cause:** `/use` (main loop, line ~683) sets both `agent.model` and `agent.task_model`; `/auto` only flips `agent.routing`. And `route()` never checks whether a model fits in VRAM. On 8 GB, anything over ~5 GB of weights spills to CPU and the first prompt evaluation takes minutes.

**Fix:**
1. `/auto` must restore `agent.task_model` to the configured default (`tz-agent:latest`) and print it.
2. In `/use`, query `/api/show` (or `/api/tags` `size` field) and compare to GPU VRAM from `terminal.hardware` (psutil/nvidia-smi are already read for the specs box). If `size > 0.85 * vram`, warn: `qwen3.6:latest is 22 GB; this GPU has 8 GB. It will run mostly on CPU and may exceed the 90 s timeout. Continue? (y/N)`.
3. Fuzzy `/use`: `/use qwen 3.6` and `/use qwen3.6` should resolve to `qwen3.6:latest` when exactly one installed model matches after stripping spaces/case and prefix-matching. Same for `/models qwen` → filter list instead of "Unknown command".
4. Consider raising the first-token wait when the model is not resident (`[waiting] … loading or evaluating prompt` already knows this state): e.g. `--timeout` applies to generation, plus a separate load grace period. Optional.
5. Tests: `/use` fuzzy resolution against a fake `/api/tags` list; `/auto` resets `task_model`.

---

## B6 — Cold-start latency and stray "Canceled" line

**Observed:**
- `hello?` → gemma3:1b, `[waiting] 10s`, 4 output tokens in 10.8 s. The fast model was not loaded.
- In PowerShell run 2, `Canceled. Partial output is unverified.` printed **after** a complete answer with no Ctrl+C.

**Fix:**
1. Optional warm-up: after `terminal.specs()` in `main()`, fire a background `POST /api/generate` with `keep_alive` for the fast model and `tz-agent:latest` (empty prompt, `"keep_alive": "30m"`). Ollama v0.34 supports this. Don't block the prompt on it.
2. Find where `KeyboardInterrupt` is raised/caught in `tz_terminal.py` `activity()` / `read()`; a prompt_toolkit cancel or the activity spinner's thread shutdown is likely surfacing as `KeyboardInterrupt` after the turn ends. Reproduce by running a turn with `/verbose` and check the events log `data/tz/events.jsonl`.

---

## B7 — Label mismatch (cosmetic)

Header shows `TZ | LOCAL AGENT`, status bar shows `tz-agent:latest · AUTO · TIZI`, but Roman launches with `roman` and `config/settings.json` says `interface.passcode: "roman"` while `config/tz.local.json` says `"passcode": "TZ"`. `Agent.label` reads `tz.local.json`. Decide one source of truth (`tz.local.json`, since `/passcode` writes it) and drop or ignore the legacy key. Low priority; matters for the UI title bar later.

---

## Not a bug: PowerShell vs cmd

Roman concluded "it's working way better in command prompt than PowerShell". The transcript does not support that: PowerShell run 3 worked exactly like the cmd run. Both invoke the same `tz.py`. The variance is B1 (model nondeterminism). After B1 the behavior is identical in both shells by construction; tell Roman that plainly and show him `rom.ps1` (three lines, just calls `TZ.cmd`).

One real difference to keep in mind: Windows Terminal/PowerShell renders the Rich box-drawing characters and the status line differently than legacy conhost cmd. If he prefers cmd's look, that is a font/terminal setting, not the app.

---

## Manual test script after fixes (add to `TZ-QUICK-TEST-GUIDE.md`)

Run `roman` and type, in order:
1. `open the browser and look up the time in japan` → browser opens Google search; no model round-trip (`[direct]` or equivalent line).
2. `what time is it in japan` → instant local answer with zone name.
3. `look up who james gandolfini was` → either relevant search results, or a clear "no relevant results, use /open" error — **never** an invented biography.
4. `/use qwen 3.6` → resolves to `qwen3.6:latest` and warns about VRAM.
5. `/auto` → prints that the task model is back to `tz-agent:latest`.
6. `hello?` → under 3 s once warm.
