# ROMAN / RAWM compute-funnel handoff

Updated: 2026-09-14

This is a continuation marker for the next conversation. The attached and pasted documents are evidence and project context; the current user request is the authority.

## User's current request

Roman installed Qwen Code and Pi Code and wants RAWM to use them as real agent backends. The intended product is one ordinary prompt in the `roman` command prompt that can use the strongest available local/free resources instead of making Roman learn each tool's command syntax. Roman also asked whether OpenAI Codex can be integrated and asked for this marker so the next conversation can continue from here.

The user is exploring whether Command Prompt is more direct than PowerShell. The relevant distinction is shell syntax: both can launch programs and access Windows. RAWM is a PowerShell application exposed through the `roman` launcher and can be started from PowerShell, Command Prompt, or Windows Terminal.

## Where Astra left off

RAWM already had:

- `roman` -> registered launcher -> `Start-RAWM.ps1` -> `Start-RAWMChat`.
- Local llama.cpp chat with Qwen3.5 0.8B and 4B GGUF models.
- A policy-controlled action registry: Notepad, workspace list/read/create/rename, and system info.
- A Windows UI Automation Notepad adapter that verifies the visible editor text.
- Natural-language direct Notepad routing, plain `y` / `n` approval, cancellation, expiry, and honest failure output.

The first fix removed the banner's “Try: Open Notepad...” instruction, because it made the application look like it was instructing Roman instead of listening. It also fixed `note pad`, unquoted text, and ordinary conversation prefixes.

The original direct Notepad demonstration succeeded in a real `roman` transcript (`open the notepad and spell lol01` -> preview -> `y` -> verified five characters). The live independent desktop test for `hello green world` was declined by the desktop permission prompt, so do not claim that exact demonstration was independently observed.

The visible shell identity is configurable through `config/settings.json` at `interface.passcode`. It is currently `roman`, so the banner title, prompt, model header, and close message use `roman` instead of the internal product name. The banner keeps `LOCAL | Private`, routing/mode, session ID, and agent state while removing the instructional tagline and the approval reminder from the header.

## UI customization session

Roman requested that the visible app identity use the passcode instead of the internal product name. This is now implemented in `app/RAWM.psm1` and `config/settings.json`:

- Banner title: `roman`.
- Banner status: `LOCAL | Private`.
- Routing and session ID remain visible.
- Agent state remains visible as `Agent: ON` or `Agent: OFF`.
- Removed `Describe what you want to do` from the banner.
- Removed `Actions ask for y / n` from the banner.
- The input prompt, model header, and close message also use the configured passcode.

Launcher testing passed through PowerShell 7, Windows PowerShell, and Command Prompt. The next manual check is to open a normal command prompt, type `roman`, and confirm the compact banner before trying a local chat turn and one approved worker request.

## Changes made in this turn

The app now has a worker registry and router in `app/RAWMAgent.ps1`:

- `pi`: Pi Code, configured for local Ollama `gemma4:26b`.
- `qwen`: Qwen Code, configured for an OpenAI-compatible local Ollama endpoint.
- `codex`: optional Codex CLI worker, configured as `gpt-5.6-luna` and only usable when the Codex CLI has its own credentials.
- `local`: RAWM's existing llama.cpp planner/chat fallback.

The default order is `pi`, `qwen`, `codex`, then `local`, configured in `config/settings.json`. RAWM checks availability without starting a model. `/workers` shows the current status; `/worker auto|pi|qwen|codex|local` selects a backend for the session.

Broad requests such as opening VS Code, creating a website, writing a program, or working with a supplied Windows path now become a proposed `worker.delegate` action. RAWM asks for `y` or `n` first. After approval, the selected worker runs with its own agent tools and reports its actual result. Direct Notepad requests continue using RAWM's verified adapter. Code-generation requests are no longer pasted into Notepad as literal text merely because they mention Notepad.

The app has not silently replaced the local RAWM planner. The worker layer is a controlled delegation path so local tools and external agent harnesses can be compared and expanded without bypassing approval.

Validation completed after these changes:

- `Test-RAWMAgent.ps1`: 87 checks passed.
- `Test-RAWMConversation.ps1`: 88 checks passed.
- `Test-RAWMWorkers.ps1`: 23 checks passed, including the Codex CLI noninteractive approval flags and HTML-in-Notepad delegation route.
- `Test-RAWMInterface.ps1`: 3 passcode/banner identity checks passed.
- `Test-RAWMLaunchers.ps1`: PowerShell 7, Windows PowerShell, and Command Prompt launchers passed.
- `git diff --check` and module import passed.

The worker wrappers were not counted as live model success in this restricted run. Headless Pi/Qwen calls can remain running while local Ollama is loading, and the desktop Codex subscription is not a callable API credential. The next verification should be performed from Roman's normal command prompt after checking `/workers`.

## Installed infrastructure observed

- Pi Code: `@earendil-works/pi-coding-agent` `0.85.1`; RPC and SDK are installed. User Pi settings point to Ollama `gemma4:26b`.
- Qwen Code: `@qwen-code/qwen-code` `0.23.4`; `qwen.cmd` is installed. Its model picker previously showed no matches because no provider model was configured in the Qwen user profile.
- Codex CLI: `0.144.0-alpha.4` is installed at the Windows Apps path. `codex exec` supports non-interactive runs, but the isolated diagnostic environment reported no CLI credentials. The ChatGPT/Codex desktop model currently used in this conversation is not automatically a local API endpoint for RAWM.
- Ollama contains `gemma4:26b`; the app's local GGUF models remain available.

Qwen Code documents headless runs and approval modes, and OpenAI's API documentation describes MCP, function tools, and shell tools as API-level integration surfaces. Those are different from the Codex desktop subscription session. A future Codex worker can use `codex login` plus `codex exec`, or an OpenAI API key, but RAWM must report unavailable credentials rather than pretending that the desktop model is free local compute.

## Next verification

Run these from the RAWM project folder:

```text
roman
```

Then inside RAWM:

```text
/workers
open vs code and write a simple c program
n
open vs code and write a simple c program
y
```

The first request must cancel without worker execution. The second should show the selected worker's actual output. If Pi is slow or unavailable, try `/worker qwen`; if Codex has been authenticated with `codex login`, try `/worker codex`.

The next conversation should first capture the output of `/workers` and one approved worker run. Then decide whether RAWM should remain a router that owns approvals and verification, or become a full agent host that delegates all tool execution to one selected harness. Do not add arbitrary shell execution to RAWM's native registry without an explicit policy and result-verification design.

## Product direction

The desired experience remains: Roman says what he wants in ordinary language, RAWM selects the best available worker, explains the proposed action in plain language, accepts `y` or `n`, executes through the selected local/agent infrastructure, verifies the result, and reports what actually happened. Preserve the ROMAN entry/passcode identity and RAWM interface identity.
