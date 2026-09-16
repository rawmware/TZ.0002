# Natural-language actions

## What changed

Use the existing `roman` entry point and type:

```text
Open Notepad and write hello green world
```

RAWM previews `Open Notepad and type "hello green world"?` and asks `Approve: y / Decline: n`. A `y` executes the displayed action once. An `n` cancels without opening the draft. The same approval works for file actions and model-generated plans. Advanced slash commands remain optional.

The router now recognizes `Notepad`, `note pad`, unquoted text, conversational prefixes, and the old trailing `/agent` or `/act` attempts. Quoted content stays literal. Requests missing the Notepad text get a concrete follow-up question. Its answer supplies text and still requires a separate approval.

The failure had two causes: `note pad` missed the action router entirely, and the chat policy explicitly sent users back to `/act`. The direct Notepad parser also required quoted text. Current capability information now reaches chat on every turn, including resumed sessions, and the banner explains normal conversation and y/n approval.

## Existing infrastructure

The installed `roman` launcher already points at this source tree. This fix reuses the existing local llama.cpp planner, validated tool registry, audit trail, and Windows UI Automation adapter. No new service, model download, registration, or language rewrite is needed.

No `qwen` executable was found on this session's PATH or in the inspected npm/local installation locations. Qwen Code has [built-in filesystem/shell tools](https://github.com/QwenLM/qwen-code/blob/main/docs/developers/tools/introduction.md) and [MCP integration](https://github.com/QwenLM/qwen-code/blob/main/docs/users/features/mcp.md). Those are useful for a broader agent, but do not establish a ready-to-use Notepad adapter. Reusing the adapter already in RAWM is the smaller change for this demonstration.

## Verification

Run with PowerShell 7:

```powershell
.\tests\Test-RAWMAgent.ps1
.\tests\Test-RAWMConversation.ps1
.\tests\Test-RAWMLaunchers.ps1
.\tests\Test-RAWMLive.ps1 -Model
.\tests\Test-RAWMNotepadEntry.ps1 -Approve
```

The conversation suite isolates approval/routing with a fake desktop executor. The launcher suite uses the actual registered `roman` command in all three Windows shells. The final test first declines through `roman` and checks that no scratch draft was created. It then approves through `roman`, requires the real adapter's verified result, and independently reads the visible editor through UI Automation after RAWM exits. It leaves the new Notepad draft visible. Test transcripts and observations are kept under `tests/.runs`.

### Results for this build

- Policy: 87 checks passed.
- Conversation: 88 checks passed, including exact handoff wording, no execution before approval or after decline, one-time approval, expiry, clarification, and honest failure output.
- Installed `roman`: passed in PowerShell 7, Windows PowerShell, and Command Prompt, including natural agent toggles, two declined Notepad requests, approved system information, and clean exit. Adapter compilation passed.
- Local 4B planner: exact file creation, source review, create-then-rename, and unsupported deletion rejection passed. Evidence: `tests/.runs/live-884a736df7514194b39f4db28654fdc7/results.json`.
- Local 0.8B chat: the first combined run caught a distracting system prompt. After shortening its capability guidance, the focused `-ChatOnly` check passed. Evidence: `tests/.runs/live-f05f1f73147a47b396d8eee183f4827e/results.json`.
- Decline through the real `roman` entry point: passed with no new Notepad scratch draft. Evidence: `tests/.runs/notepad-entry-20280ef2113b4ad4b80448665e80b21b/declined.txt`.
- Live approval / visible Notepad text: **not run**. The desktop escalation was declined. The adapter is compiled but its runtime compatibility remains unverified. No successful desktop demonstration is claimed.

## Current limits

Desktop support is limited to a new Notepad draft. File writes remain in RAWM's workspace and do not overwrite existing files. Other phrasing uses the local model planner and can require more detail. This is not general automation of every installed application. The existing adapter stops on target/focus changes and reports uncertainty if it cannot verify the result.
