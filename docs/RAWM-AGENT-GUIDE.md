# RAWM can inspect files and take local actions

Start RAWM as usual:

```text
roman
```

The agent is enabled in this package's settings. An already-open RAWM session needs to be exited and reopened to load the new code.

## Ask it to check a file

```text
Check "C:\path\script.py" for bugs
Explain "C:\path\settings.json"
Summarize "C:\path\notes.md"
```

Use a real path and quote it, especially if it contains spaces. You can also use:

```text
/inspect "C:\path\script.py" Why is this returning the wrong total?
```

RAWM reads the selected local file and asks its local model to explain or review it. The review can cite line numbers and suggest corrections. It does not execute the file or change it. Selecting a file does not authorize writes to its folder. Relative inspection paths start in the RAWM application folder.

Text and source-code formats are supported, including Python, PowerShell, JavaScript, TypeScript, C#, SQL, JSON, CSV, and Markdown. PDF, Office documents, images, whole-project review, and voice input are future capabilities. Files must be at most 64 KB and fit the model's configured context; larger files need a smaller excerpt. Hidden credential files, linked paths, network shares, and detected credential-like contents are blocked.

## Ask it to work with files

```text
List workspace files
Create file "notes.txt" containing "Hello Roman"
Read workspace file "notes.txt"
Rename "notes.txt" to "ideas.txt"
```

The write workspace is the `workspace` folder inside RAWM. File tools cannot write to your Desktop, Documents, application code, or another folder outside that workspace. Nested folders are created with new files. Supported file-tool formats are `.txt`, `.md`, `.csv`, `.json`, and `.log`. Reads and renames are limited to 32 KB; new content is limited to 4,000 characters. Existing files are never overwritten.

For a more flexible request or a sequence:

```text
Create a file named first.txt containing exactly alpha, then rename first.txt to second.txt.
```

RAWM asks the configured local planning model for a structured plan. It displays the concrete steps and exact text. To execute the displayed action, enter:

```text
y
```

Enter `n` to cancel. Every proposed action waits for approval, including direct Notepad, file creation, and read-only tool requests. Plans expire after five minutes, cannot be approved twice, and disappear when you leave the session or change chats. Slash commands are optional.

Execution stops on the first failure. Completed steps remain in place; RAWM reports that explicitly. It does not retry uncertain actions. File results never become instructions for further tools.

## Desktop actions

```text
Open Notepad and write hello green world
```

Notepad is the first desktop adapter, one tool behind the general controller. The adapter opens a uniquely named blank scratch file, verifies the Notepad process, window, editor, and focus, inserts literal text into that editor, then reads it back. It never sends global keyboard shortcuts or uses the clipboard. The entered text is not explicitly saved by RAWM; Notepad may independently preserve unsaved tabs using its own settings. Empty scratch files remain under `data/agent/drafts`.

The spelling `note pad` and unquoted text are accepted. RAWM shows the exact proposed text and waits for `y` or `n`. If the text is missing, it asks what to type and then requests approval.

**Desktop validation is pending:** the current launcher and cancellation checks pass, but the live approval test was declined at the desktop permission prompt. Text entry through this adapter is not yet verified on this machine. Unsupported Notepad versions, dialogs, or changed focus should cause a visible stop. See [current verification](RAWM-NATURAL-LANGUAGE-FIX.md).

## Controls and privacy

| Command | Purpose |
| --- | --- |
| `y` / `n` | Approve / decline the displayed action |
| `turn agent off` / `turn agent on` | Disable / enable local actions |
| `/agent` or `/agent tools` | Status, examples, and enabled tools |
| `/agent off` | Chat only for this session |
| `/agent on` | Enable local actions and inspection |
| `/act <request>` | Request a local action plan |
| `/inspect "path" <question>` | Read and analyze one selected file |
| `/approve <id>` | Execute the exact displayed plan |
| `/cancel` | Discard a pending plan |
| `/agent audit` | Show recent action outcomes |
| `/stop` | Cancel a pending plan and stop the owned model server |

Escape cancels an in-flight planning request or stops the Notepad helper / further steps. Ctrl+C exits an active operation; inspect any partially completed work before retrying. Model loading and streaming file reviews use the existing application cancellation behavior.

Ordinary chat is still available. `/paste` remains reference/chat input and never triggers tools automatically. Raw agent requests and file-read results are excluded from chat prompts and exports. File inspection saves your question and the model's review, which may quote excerpts; it does not attach the raw source to saved history. RAWM's built-in tools and local chat remain loopback-only and require no API key or internet connection. Optional worker delegation can use installed Pi Code or Qwen Code through local Ollama, or Codex CLI when that CLI has its own credentials; run `/workers` to inspect availability.

The local audit log is `data/agent/audit.jsonl`. It records timestamps, plan IDs, tools, target paths, and outcomes. Typed/file text is represented by a character count, not stored in the audit. Credential detection is a limited heuristic; do not intentionally provide secrets. This is an application policy boundary, not an OS security sandbox against other software modifying files concurrently.

## Model and tool settings

`config/settings.json` keeps the existing `fast` and `code` model slots. Change their local model filenames to use compatible replacements. `agent.plannerModel` chooses which slot handles planning and file review. `agent.enabled` sets the startup mode; removing a tool from `agent.tools` disables it. Missing agent configuration defaults to chat only.

The initial registry contains `notepad.write`, `workspace.list`, `file.read`, `file.create`, `file.rename`, and `system.info`. Explicit file inspection is a separate read-only flow governed by `file.read` permission. Shell commands generated by models, deletion, overwriting, installing software, sending messages, arbitrary application control, and network tools are unsupported and cannot be enabled merely by a model or an approval response.
