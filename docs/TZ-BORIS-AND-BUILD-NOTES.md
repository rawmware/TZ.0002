# What changed and why

## Research: Boris Cherny

Reviewed September 16, 2026: [Boris's profile](https://github.com/bcherny) identifies his work on Claude Code at Anthropic. His pinned public repositories include [json-schema-to-typescript](https://github.com/bcherny/json-schema-to-typescript), [Undux](https://github.com/bcherny/undux), [typed-rx-emitter](https://github.com/bcherny/typed-rx-emitter), Flow migration tools, and TypeScript exercises. His personal profile is not the implementation of Claude Code.

The relevant design lessons are our interpretation, not attributed quotes: explicit contracts from schema tooling, simple state from Undux, and observable events from typed emitters. TZ uses validated tool arguments, explicit tool results, local event records, and visible completion/error status. No dependency on these unrelated TypeScript libraries was added. We did not copy Claude Code internals or claim to reproduce it.

## Concrete failure fixes

- The supplied transcript sent ordinary file/web work to Gemma 1B as chat. Direct tools now intercept supported requests, including the original path-first `AGENTS.md read this for me then.` form. The model does not decide whether reading the requested file is permissible.
- PDFs use actual extracted text; scanned PDFs still need OCR. The supplied `1706.03762v7.pdf` identifies itself as *Attention Is All You Need* by Vaswani and coauthors. This paper explains Transformer architecture; it is not an agent orchestration implementation.
- Public web requests perform actual HTTP requests. Codex/GitHub project discovery uses GitHub's repository search; general search uses Bing RSS. Search snippets are labeled as discovery evidence and may be imperfect. Fetch source pages before treating snippets as established facts.
- The previous 23 GB coding model is a poor default for this desktop's 8 GB GPU. The new default is a ~2.5 GB Qwen3 4B instruction model. The original Qwen3 thinking variant remained verbose despite `think:false` and a template experiment; the non-thinking Instruct variant passed the direct-response test. Existing large models were preserved.
- The legacy completion code inherited HttpClient's 100-second timeout despite a 180-second application deadline. It now lets the application timer own cancellation. The new runtime enforces a bounded deadline, shows progress, preserves printed partial output and reports incomplete streams as failures.
- Both desktop shortcuts pointed at the same launcher. The old installer originally made `Roman TZ`; later work added `TZ`. The Python installer keeps one `TZ` shortcut and archives the old one locally.
- `/passcode NAME` now creates an actual per-user launch command, not just a display label. The canonical `tz` fallback and old aliases remain valid.

## OpenCode integration

OpenCode 1.18.31 was installed with `npm i -g opencode-ai`. TZ runs its executable directly and streams JSON events. Its [documented local Ollama provider](https://opencode.ai/docs/providers/#ollama) uses the same `tz-agent:latest` model. No cloud model is silently selected. `/opencode` opens the full terminal UI; `/opencode TASK` runs inside TZ. Natural coding tasks use that adapter when present. Model tool calls also remain available through the lightweight native runtime.

The adapter distinguishes completed tool events, failed tool events, process errors and completed steps; a process exit alone does not prove completion. Headless shell approvals can be declined by OpenCode; use its interactive UI when approval is needed. This is a functional local agent, not a guarantee that a 4B model can solve every programming task.

## Preservation and scope

The PowerShell implementation and its desktop adapters remain as legacy code. The new default is the portable Python runtime. Local/private historical notes and machine settings are not newly published. Laptop instructions are in `TZ-LAPTOP-SETUP.md`.
