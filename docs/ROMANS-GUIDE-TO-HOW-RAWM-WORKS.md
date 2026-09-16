# Roman's guide to how RAWM works

**From an idea in plain English to a local AI app you enjoy using.**

Written for Roman, with Astra's help, on September 13, 2026.

This guide describes the local Windows version repaired in our September 12–13 conversation. It is based on the actual application files and the repair results from that conversation. Creating this guide did not change the application or the E-drive version.

Roman, you do not need to understand every symbol on the first read. Start with what each piece is responsible for. When those responsibilities make sense, the code becomes much easier to read.

The examples here are explanations, not a setup checklist you need to run. Your app is already working.

## Contents

1. [What you built, and what your role was](#1-what-you-built-and-what-your-role-was)
2. [The whole app in one picture](#2-the-whole-app-in-one-picture)
3. [The basic vocabulary](#3-the-basic-vocabulary)
4. [Your files and folders](#4-your-files-and-folders)
5. [What happens when you type roman](#5-what-happens-when-you-type-roman)
6. [Profiles, and why two profiles were normal](#6-profiles-and-why-two-profiles-were-normal)
7. [What broke and how we repaired it](#7-what-broke-and-how-we-repaired-it)
8. [Execution policies in ordinary language](#8-execution-policies-in-ordinary-language)
9. [Reading PowerShell without knowing every word](#9-reading-powershell-without-knowing-every-word)
10. [Routing, models, and the local AI engine](#10-routing-models-and-the-local-ai-engine)
11. [A message travels through the app](#11-a-message-travels-through-the-app)
12. [Settings, behavior instructions, and saved chats](#12-settings-behavior-instructions-and-saved-chats)
13. [How the word wrapping works](#13-how-the-word-wrapping-works)
14. [The function map](#14-the-function-map)
15. [Your everyday command guide](#15-your-everyday-command-guide)
16. [How we knew the repair worked](#16-how-we-knew-the-repair-worked)
17. [How to approach your next project](#17-how-to-approach-your-next-project)
18. [What you can say when you share this](#18-what-you-can-say-when-you-share-this)
19. [A handoff note for a future conversation](#19-a-handoff-note-for-a-future-conversation)

## 1. What you built and what your role was

You built a personal terminal application called **RAWM**. You open PowerShell, type `roman`, and talk to a language model running on your own computer. The app provides model routing, streamed replies, saved conversations, copy/export commands, usage information, and text wrapping.

You were the person deciding what the product should feel like. You wanted a short entry command, useful answers, different modes, and an experience you would actually enjoy using. When something failed, you supplied evidence and clarified the priority: get the local computer working, preserve the other features, and leave the E-drive version alone.

Those are concrete product decisions. A programmer still needs someone to decide what should happen, which tradeoffs are acceptable, and what counts as finished.

```text
+----------------------------------------------------------+
| ROMAN: product creator and human orchestrator             |
| Chooses the experience, priorities, limits, and next step |
+----------------------------+-----------------------------+
                             |
                             v
+----------------------------------------------------------+
| AI coding assistant                                      |
| Turns requirements into code, investigates, and tests     |
+----------------------------+-----------------------------+
                             |
                             v
+----------------------------------------------------------+
| Existing building blocks                                 |
| PowerShell + llama.cpp + Qwen model files                 |
+----------------------------+-----------------------------+
                             |
                             v
+----------------------------------------------------------+
| RAWM: the application you shaped and use                  |
+----------------------------------------------------------+
```

There is also a second kind of orchestration *inside* RAWM. Its code decides which model to use, starts the engine, sends a request, displays the reply, and saves the conversation. Your orchestration directs the project; the application's orchestration coordinates its software components.

An accurate way to describe your work is:

> I designed and built a local AI chat application with AI coding assistance. I directed the features, tested the experience, and worked through the setup problems. It uses PowerShell for the application and existing Qwen models through llama.cpp for local answers.

That gives you credit for the product and credits the people who built the underlying tools. You did not need to train a new language model or write an inference engine to build an application around them.

## 2. The whole app in one picture

```text
                         YOUR COMPUTER
+----------------------------------------------------------+
|                                                          |
|  You type: roman                                         |
|        |                                                 |
|        v                                                 |
|  PowerShell finds your launcher                           |
|        |                                                 |
|        v                                                 |
|  Start-RAWM.ps1                                          |
|  Selects PowerShell 7 when needed                         |
|        |                                                 |
|        v                                                 |
|  app/RAWM.psm1                                           |
|  +--------------------+  +----------------------------+  |
|  | Read settings      |  | Read behavior instructions |  |
|  +--------------------+  +----------------------------+  |
|        |                                                 |
|        v                                                 |
|  Read your message -> choose FAST or CODE                 |
|        |                                                 |
|        v                                                 |
|  llama-server.exe + the selected .gguf model               |
|        |                                                 |
|        v                                                 |
|  Stream answer -> wrap text -> show usage                 |
|        |                                                 |
|        v                                                 |
|  Save conversation -> wait for your next message          |
|                                                          |
+----------------------------------------------------------+
```

The downloadable models and runtime need internet access during installation. The chat code in this version then sends inference requests to `127.0.0.1`, which points back to this computer. It does not send these chat requests to a paid cloud model.

There are two separate AI experiences in this story: the coding assistant you used to build RAWM, and the local models you talk to *inside* RAWM. Choosing Astra or Luna while developing the app does not install those assistants inside RAWM. Your installed model choices are described later in this guide.

## 3. The basic vocabulary

| Word | Friendly meaning | Your RAWM example |
|---|---|---|
| Program / application | Instructions and supporting pieces that perform a job. | RAWM provides the chat experience. |
| Terminal / console window | The text-based place where you see output and enter commands. | The window in your screenshot. |
| Shell | A program that interprets commands. | PowerShell. |
| Programming language | Rules for expressing instructions precisely. | PowerShell is the main language used in RAWM. |
| Script | A text file of instructions that another program runs. | `Start-RAWM.ps1`. |
| Function | A named, reusable piece of code with a particular job. | `Get-RAWMModelMode` chooses a model mode. |
| Variable | A name attached to a value the program is using. | `$Mode` might contain `'fast'`. |
| Parameter | An input a function or script accepts. | `-Mode code` tells the launcher which mode to use. |
| Module | A reusable collection of related code. | `app/RAWM.psm1`. |
| Runtime | Software needed to execute a particular kind of work. | PowerShell runs scripts; llama.cpp runs model inference. |
| Dependency | Another component your app needs. | The PowerShell executable, engine DLLs, and model files. |
| Process | A running instance of a program. | A running `llama-server.exe`. |
| Configuration | Values that control how existing code behaves. | Model paths and response limits in `settings.json`. |
| State | What the app currently remembers while running. | Current mode, conversation, and last answer. |
| Persistence | Saving information so it survives closing the app. | Conversation JSON files. |
| API | An agreed way for programs to exchange requests and results. | RAWM asks the local server for a chat response. |
| Debugging | Following evidence to explain and repair a failure. | Finding duplicated code inside the profile. |

PowerShell is both a shell you can use interactively and a programming language for scripts. That is why you can type commands directly into it and also use it to build a complete text application.

## 4. Your files and folders

Your working local application folder is:

```text
C:\Users\ROMAN\Documents\ChatGPT\Rawm's local LLM
```

Inside that folder, the responsibilities are arranged like this. The model names are shortened in this picture to keep it readable.

```text
Rawm's local LLM/
|
+-- Start-RAWM.ps1           Launch the app
+-- Register-RAWM.ps1        Teach this computer the roman command
+-- Unregister-RAWM.ps1      Remove that registration
+-- Install-RAWM.ps1         Obtain the engine and model files
+-- RAWM.portable.json       Identify the application package
+-- README.md               Short setup explanation
+-- RAWM-CONCEPT-AND-SOL-HANDOFF.md
|                           Original planning document
|
+-- app/
|   +-- RAWM.psm1            Main application logic
|
+-- config/
|   +-- settings.json        Models, limits, connection, appearance
|
+-- context/
|   +-- RAWM-BEHAVIOR.md      Instructions given to the local model
|
+-- models/
|   +-- [0.8B model].gguf    Smaller model
|   +-- [4B model].gguf      Larger model
|
+-- runtime/
|   +-- llama.cpp/
|       +-- llama-server.exe
|       +-- *.dll            Supporting engine libraries
|       +-- ...              Other files from the runtime package
|
+-- data/
|   +-- chats/              Saved conversation JSON files
|   +-- logs/               Local inference server logs
|
+-- exports/               Conversations exported as Markdown
+-- tests/                 Existing short chat test inputs
+-- docs/                  Guides and handoff notes
    +-- [this guide]
```

### The extensions tell you what kind of file you are looking at

| Extension | What it is | What reads it |
|---|---|---|
| `.ps1` | A PowerShell script. | PowerShell. |
| `.psm1` | A PowerShell script module containing reusable functions. | PowerShell through `Import-Module`. |
| `.cmd` | A Windows command script, sometimes called a batch script. | Windows Command Prompt's command interpreter. |
| `.json` | Structured text containing data: names, values, lists, and objects. | RAWM's JSON reader. |
| `.md` | Markdown: readable text with simple formatting marks. | People, Markdown viewers, and sometimes app code. |
| `.gguf` | A binary model format containing model data and metadata. | The inference engine. |
| `.exe` | A Windows executable program. | Windows starts it as a process. |
| `.dll` | A library of compiled code an executable can load. | Programs such as the inference engine. |
| `.log` | Recorded diagnostic output. | A person or a troubleshooting tool. |
| `.txt` | Plain text without an application-specific format implied. | The existing tests use it for sample inputs. |
| `.partial` | This installer's name for an unfinished download. | The installer renames it after success. |
| `.tmp` | This app's temporary file while saving a conversation. | The save routine replaces the final file with it. |

Changing a filename's extension does not translate its contents. Renaming a Markdown note to `.ps1` would cause PowerShell to *try* to interpret the note as code; it would not make the note a functioning script.

The original concept document is a historical plan. Some of its statements describe intended future behavior. For the working version, the code tells us what is implemented now.

### Some launcher files live outside the application folder

Registration created or updated these files on this computer:

```text
C:\Users\ROMAN\Documents\WindowsPowerShell\
    Microsoft.PowerShell_profile.ps1

C:\Users\ROMAN\Documents\PowerShell\
    Microsoft.PowerShell_profile.ps1

C:\Users\ROMAN\AppData\Local\RAWM\
    Launch-RAWM.ps1

C:\Users\ROMAN\AppData\Local\Microsoft\WindowsApps\
    roman.cmd
```

Think of the main app folder as the workshop and these small files as signposts that help Windows find it.

## 5. What happens when you type roman

`roman` is a custom launch command. It feels like a personal passcode because it opens your experience, but it does not check a password or authenticate a user. Anyone already able to use the command in your Windows account can launch it.

There are two paths to the same app:

```text
                        type roman
                            |
               +------------+-------------+
               |                          |
               v                          v
     Profile-defined function      roman.cmd fallback
               |                          |
               |                   Launch-RAWM.ps1
               |                          |
               +------------+-------------+
                            |
                            v
                     Start-RAWM.ps1
                            |
                            v
                       RAWM.psm1
```

Normally, a loaded profile defines a function named `roman`. PowerShell finds that function and executes it. If the function is unavailable, the `roman.cmd` file can provide another route through a folder PowerShell searches for commands. That search list is called **PATH**.

The `.cmd` helper tries `pwsh.exe`, the PowerShell 7 executable, and otherwise uses `powershell.exe`. The main start script also checks the version and hands the app to PowerShell 7 if needed. That extra check is what made the normal Windows PowerShell route work reliably in our tests.

The main start script then imports the module and calls its public entry function:

```powershell
Import-Module $modulePath -Force
Start-RAWMChat -Root $rawmRoot -Mode $Mode -Resume $Resume -New:$New -NoBanner:$NoBanner
```

Read this as: “Load the app's functions, then start the chat using this folder and these options.” Here, `-Force` requests that the module be loaded again. It is useful after an edit because a new launch should pick up the saved code.

Launching the interface does not immediately run a model. The engine starts when your first actual chat request needs it. Looking at `/help` therefore does not require generating an AI answer.

## 6. Profiles and why two profiles were normal

A PowerShell profile is a startup script. It runs when an applicable PowerShell session opens and can define commands for that session. PowerShell has profiles for different users, editions, and host programs; having several is normal. The `$PROFILE` variable tells you the profile path relevant to the current session. See [Microsoft's profile explanation](https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.core/about/about_profiles?view=powershell-7.5).

On your computer, the two files we repaired belonged to different PowerShell editions:

| Edition | Executable | Your profile folder |
|---|---|---|
| Windows PowerShell, the older edition | `powershell.exe` | `Documents\WindowsPowerShell\` |
| PowerShell 7, the newer edition | `pwsh.exe` | `Documents\PowerShell\` |

```text
Open Windows PowerShell             Open PowerShell 7
          |                                  |
          v                                  v
WindowsPowerShell/profile            PowerShell/profile
          |                                  |
          v                                  v
    define roman                       define roman
          |                                  |
          +----------------+-----------------+
                           |
                           v
                 Same local RAWM app
```

The two profiles were not two competing copies of your AI. They were two entrances that should lead to the same application.

In the broken state, both entrances contained malformed launcher text. Repairing only one would have left the other shell with the old problem.

The registration script can update both through its `-AllPowerShellEditions` option. It also makes timestamped profile backups before writing the updated contents.

A currently open shell already has its functions in memory. Saving a corrected profile does not automatically replace those loaded definitions. That is why opening a **new PowerShell window** mattered after the launcher repair. See [Microsoft's guidance on applying profile changes](https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.core/about/about_profiles?view=powershell-7.5#how-to-edit-a-profile).

## 7. What broke and how we repaired it

The repair had several layers. These are the observed problems and the actions taken in this conversation, rather than a claim that every earlier version was inspected.

| Layer | What we found | What we did |
|---|---|---|
| Profile syntax | Multiple copies of the launcher had been inserted inside one another. | Re-registered the launcher using the corrected local registration script, with profile backups. |
| Target location | Launchers pointed at `E:\RAWM POWERSHELL\Start-RAWM.ps1`. | Registered the local C-drive app as the first location to use. |
| Local dependencies | The local `models` and `runtime` folders initially contained only placeholder files. | Copied a previously extracted CPU runtime from this computer's temporary folder and downloaded both models locally. |
| Script policy | Ordinary Windows PowerShell rejected scripts because its effective settings did not allow them. | Set `RemoteSigned` for the current Windows user. |
| PowerShell version | Direct execution through older Windows PowerShell hung during tests. | Added a version check that launches the app with available PowerShell 7. |
| Readability | Streamed output was printed without app-managed wrapping to visible width. | Added window-width-aware output wrapping and narrower status boxes. |

### Why the red error referred to braces and a pipe

PowerShell first **parses** a script: it reads the text and checks whether it forms valid instructions. Your screenshot showed errors including an unexpected `}` and an empty pipe element.

The profile had launcher blocks nested inside other launcher blocks, including text where `Join-Path $_.Root ...` should have been. Once the structure was broken, a closing brace no longer had the expected opening structure, and a pipe no longer had a valid expression feeding it.

```text
Expected structure                  Broken structure we found

launcher begins                     launcher begins
  function                            function
    locate app                          partial instruction
    run app                             launcher begins again
  function ends                           more copied code
launcher ends                         leftover braces and pipes
```

The visible symptom was “my command doesn't work,” but the error showed that PowerShell could not correctly load the startup instructions in the first place.

### How the registration repair avoids that kind of corruption

The current registration script finds its named start/end markers and replaces that region using a literal replacement callback:

```powershell
$updated = [regex]::Replace($existing, $pattern, { param($match) $literalBlock })
```

This matters because a regular-expression replacement string has its own special syntax. `$` sequences inside PowerShell source can be interpreted by the replacement system if the source is passed as a replacement string. Returning the block from a callback preserves it as text. The current pattern also spans the repeated marked region so the damaged nested copies can be replaced together.

The corruption we observed is consistent with an earlier replacement escaping problem. We did not prove which exact historical edit first created it. We did verify that the current repair produced clean profiles pointing at the local app.

### Why PowerShell 7 was part of the repair

The outer window can remain Windows PowerShell while a newer PowerShell process runs RAWM inside that same terminal. A child process is simply a program started by another program.

The launcher checks for `pwsh.exe`. If that command is unavailable, this local version can use the PowerShell runtime already supplied in your Codex runtime cache:

```text
C:\Users\ROMAN\.cache\codex-runtimes\codex-primary-runtime\
    dependencies\native\powershell\pwsh.exe
```

That fallback is a dependency of this computer's current setup. It is not a promise that every other computer has that same folder.

The confirmed result was that relaunching through PowerShell 7 removed the hang in our tests. We did not isolate the precise internal cause of the older runtime's hang, so this guide does not pretend that we did.

## 8. Execution policies in ordinary language

An execution policy controls the conditions under which PowerShell runs scripts. It can affect profiles because profiles are scripts too. It does not repair invalid code or grant administrator access. Microsoft describes it as a precaution, not a complete security boundary. See [Microsoft's execution-policy documentation](https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.core/about/about_execution_policies?view=powershell-7.5).

| Term | Meaning |
|---|---|
| `Restricted` | Individual commands can run, but scripts cannot. |
| `RemoteSigned` | Local scripts can run; internet-marked scripts generally require a trusted signature unless unblocked. |
| `Bypass` | This policy does not block or prompt for scripts. |
| `CurrentUser` | The setting applies to your Windows user. |
| `Process` | The setting lasts for that process. |
| `Undefined` | That scope has no explicit setting; another scope or a default determines the result. |

During the repair we used:

```powershell
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned -Force
```

This records what we changed; you do not need to repeat it. The launcher's `-ExecutionPolicy Bypass` applies to its child session. Organization-managed policies can take precedence, so a launcher flag cannot universally overcome an enforced policy. See [policy scopes and precedence](https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.core/about/about_execution_policies?view=powershell-7.5#execution-policy-scope).

Our development sandbox initially reported different settings from your normal Windows account. An outside-sandbox check confirmed `CurrentUser: RemoteSigned` and a successful `roman` launch. That is a useful debugging lesson: verify in the environment the person actually uses.

## 9. Reading PowerShell without knowing every word

Start by looking for names and structure. Most RAWM functions use the pattern `Verb-RAWMThing`, which is a readable label for their responsibility.

### A small piece of the real launcher

This is a shortened teaching version of the profile function; the actual file also contains fallback-location handling:

```powershell
function global:roman {
    $rawmStart = 'C:\Users\ROMAN\Documents\ChatGPT\Rawm''s local LLM\Start-RAWM.ps1'
    & $rawmStart @args
}
```

| Piece | How to read it |
|---|---|
| `function` | “Define a named action.” |
| `global:roman` | “Call it roman and make it available throughout this PowerShell session.” |
| `{ ... }` | “These instructions belong to this function.” |
| `$rawmStart` | “A variable holding the script's location.” |
| `=` | “Assign the value on the right to the name on the left.” |
| `'...'` | “Treat this as literal text.” |
| `& $rawmStart` | “Execute the command or script whose path is stored here.” |
| `@args` | “Pass through the arguments the caller supplied.” |

Notice `Rawm''s` in the code. The actual folder is named `Rawm's local LLM`, with one apostrophe. Inside a single-quoted PowerShell string, doubling the apostrophe represents one literal apostrophe. Otherwise, it would prematurely close the string. See [Microsoft's quoting rules](https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.core/about/about_quoting_rules?view=powershell-7.5).

That is **escaping**: expressing a character as data when the language would otherwise treat it as punctuation with a special job.

### Variables and types

```powershell
[string]$Mode = 'auto'
[switch]$NoBanner
```

`[string]` says the value is text. `[switch]` defines an option that can be present or absent, like `-NoBanner`. A variable's name is chosen by the programmer; the `$` tells PowerShell that it is a variable reference.

In the module, `$script:Mode` holds shared state for the module. The `script:` part describes where that value lives. It lets several functions use the same selected mode.

### Conditions

```powershell
if (-not (Test-Path -LiteralPath $modulePath -PathType Leaf)) {
    throw "RAWM module is missing: $modulePath"
}
```

Read it aloud: “If the module file does not exist, stop and explain which file is missing.”

`Test-Path` checks existence. `-LiteralPath` treats the path literally, rather than as a wildcard pattern. `Leaf` means a file here. `throw` raises an error. In the double-quoted message, PowerShell substitutes the value of `$modulePath`.

### Loops

```powershell
while ($true) {
    # Read and handle the next message.
}
```

This is a simplified example of the chat loop. It repeats until the code explicitly leaves it. In RAWM, `/exit` eventually causes a `break`, which leaves that loop.

### Pipes

```powershell
Get-Content -LiteralPath $Path -Raw -Encoding UTF8 | ConvertFrom-Json
```

The pipe, `|`, passes the first command's output into the next command. Here it means “read the whole file as text, then turn its JSON into values PowerShell can use.” PowerShell pipelines commonly pass structured objects, not only printed lines.

### Error handling

```powershell
try {
    # Attempt an operation.
} catch {
    # Handle an error.
} finally {
    # Perform cleanup when this block finishes.
}
```

Those comments explain the shape; this is a teaching example. RAWM uses this structure to report request failures and clean up network resources. Its outer chat cleanup saves the session and stops the server process it started during normal exit. A forced process kill or power loss can interrupt normal cleanup.

### A quick symbol decoder

| Symbol or expression | Job in the code |
|---|---|
| `#` | Starts a comment outside a string. |
| `{ }` | A code block, or part of a data structure depending on context. |
| `( )` | Groups an expression or supplies method arguments. |
| `@(...)` | Creates or collects an array: a list of values. |
| `@{...}` | Creates a hashtable: named values. |
| `[pscustomobject]@{...}` | Turns named values into a simple structured object. |
| `-eq`, `-lt`, `-gt` | Equal to, less than, greater than. |
| `-match` | Tests text against a regular expression. |
| `return` | Gives a result back and exits the current function. |
| `[void]` | Discards an expression's return value. |
| `[Console]::WindowWidth` | Reads a property from a .NET type. |

The module's backtick followed by `n` means a newline inside a double-quoted string. Its backtick followed by `e` creates the escape character used in terminal color sequences under PowerShell 7.

Indentation makes code easier for people to read. Matching braces and quotes make its structure understandable to the parser. A beautifully indented file can still be invalid if a quote is missing.

### Why the same symbol can mean different things in different files

PowerShell, JSON, Markdown, and Windows command scripts have different readers and different grammar. `#` can start a PowerShell comment or a Markdown heading; standard JSON does not accept either kind of comment. `%*` forwards arguments in the `.cmd` helper; `@args` forwards arguments in the PowerShell function.

Before asking “Is this syntax correct?”, first ask “Which language is reading this file?” That question would have helped make the original launcher corruption much less mysterious.

## 10. Routing, models, and the local AI engine

The **model** and the **engine** have different jobs. A model file holds learned numerical parameters and supporting information. The engine performs the computations that use that model to generate a response. Running an existing model this way is called **inference**.

```text
+-----------------------+       +--------------------------+
| MODEL FILE            |       | INFERENCE ENGINE         |
| Qwen...gguf           | ----> | llama-server.exe         |
| Learned model data    |       | Runs the calculations    |
+-----------------------+       +-------------+------------+
                                              |
                                              v
                                   +----------------------+
                                   | Generated answer     |
                                   +----------------------+
```

Your application code is PowerShell. The underlying llama.cpp project is implemented in C/C++; we used a compiled Windows package rather than writing or compiling that engine ourselves. Its support for quantized models helps reduce model memory requirements. See the [llama.cpp project](https://github.com/ggml-org/llama.cpp).

### The two models configured in your app

| Mode | Configured model name | Local filename | Response token cap |
|---|---|---|---:|
| `fast` | Qwen3.5 0.8B Q4_K_M | `Qwen3.5-0.8B-Q4_K_M.gguf` | 384 |
| `code` | Qwen3.5 4B Q4_K_M | `Qwen3.5-4B-Q4_K_M.gguf` | 2,048 |

The model family is Qwen3.5. The `0.8B` and `4B` labels refer to approximate parameter counts: roughly 0.8 billion and 4 billion. They do not mean the downloads contain that many gigabytes.

`Q4_K_M` names a quantization format. For your purposes, think “a particular compact representation of model numbers, trading some numerical precision for lower resource requirements.” It does not mean “four tokens,” and it is not a routing mode you type into RAWM.

The installer obtains the fast file from a Hugging Face repository maintained by `notschmee` and the larger file from one maintained by `bartowski`. These are the download sources encoded in your installer; the local filenames are the names your settings expect. The larger download's remote filename includes `Qwen_Qwen3.5`, while the installer saves it under your shorter local name.

The word `code` is an application role assigned to the larger model. That label alone does not prove the model is a separately trained coding specialist or guarantee that all generated code is correct.

### How automatic routing chooses

Automatic routing is a small rule in PowerShell. It does not make a separate AI request to decide which AI to ask.

```text
                      YOUR MESSAGE
                           |
                           v
              +-------------------------+
              | Did you force a mode?   |
              +-----------+-------------+
                          |
                +---------+---------+
                |                   |
               YES                  NO
                |                   |
                v                   v
        Use FAST or CODE     Look for listed keywords
                             or a triple-backtick fence
                                      |
                            +---------+---------+
                            |                   |
                           MATCH             NO MATCH
                            |                   |
                            v                   v
                           CODE                FAST
```

The actual keyword list includes `write`, `implement`, `build`, `create`, `refactor`, `debug`, `fix`, `code`, `script`, `function`, `class`, `module`, `api`, `regex`, `powershell`, `python`, `javascript`, `typescript`, `sql`, `html`, `css`, `compile`, `stack trace`, and `exception`.

| Message while in `/auto` | Expected route | Why |
|---|---|---|
| “Say hello.” | Fast | No listed keyword. |
| “Write a PowerShell function.” | Code | Several listed keywords. |
| “Write me a birthday message.” | Code | `write` is enough to match. |
| “What is 2 + 2?” | Fast | No listed keyword. |

The birthday example teaches an important distinction: a keyword rule recognizes words; it does not fully understand your intent. `/fast` and `/code` let you decide explicitly. `/auto` restores the rule.

The selected mode stays in effect for subsequent requests until you change it. Changing the mode sets the choice; the engine changes models when a request actually needs the new model.

### Why speed varies

The first request needs to load a model. Later requests using the same active model can reuse the running server. Switching models stops the current server and starts a server with the other model, which adds loading time.

Longer prompts, longer replies, model size, memory pressure, and other work running on the computer can affect the wait. The installed runtime we copied was a CPU build. The `gpuLayers: "auto"` setting does not by itself add GPU support to a CPU-only package.

Your usage panel's tokens-per-second figure divides output tokens by the measured request duration, which includes prompt processing. It is useful feedback about that request, but it is not a controlled benchmark of the hardware. The app's timer starts after `Start-RAWMServer` returns, so it does not include the cold model-startup wait.

## 11. A message travels through the app

Suppose you type:

> Write a PowerShell function named Get-Greeting that returns hello.

Here is the journey through the current code:

```text
+----------------------------------------------------------+
| 1. INPUT                                                 |
| Start-RAWMChat reads your line                            |
+----------------------------+-----------------------------+
                             |
                             v
+----------------------------------------------------------+
| 2. COMMAND OR QUESTION?                                  |
| /help is handled locally; this sentence goes to a model   |
+----------------------------+-----------------------------+
                             |
                             v
+----------------------------------------------------------+
| 3. ROUTING                                               |
| Get-RAWMModelMode sees coding keywords -> code            |
+----------------------------+-----------------------------+
                             |
                             v
+----------------------------------------------------------+
| 4. CONVERSATION                                          |
| Add your message and save the session                    |
+----------------------------+-----------------------------+
                             |
                             v
+----------------------------------------------------------+
| 5. ENGINE                                                |
| Start-RAWMServer loads the selected model if needed       |
+----------------------------+-----------------------------+
                             |
                             v
+----------------------------------------------------------+
| 6. REQUEST                                               |
| Send conversation + settings to the local chat endpoint  |
+----------------------------+-----------------------------+
                             |
                             v
+----------------------------------------------------------+
| 7. RESPONSE                                              |
| Read arriving pieces, wrap them, and print them           |
+----------------------------+-----------------------------+
                             |
                             v
+----------------------------------------------------------+
| 8. FINISH                                                |
| Save answer, update usage, wait for your next message     |
+----------------------------------------------------------+
```

### The local address

The request goes to:

```text
http://127.0.0.1:18080/v1/chat/completions
       |         |          |
       |         |          +-- The chat operation
       |         +------------- The server's port
       +----------------------- This same computer
```

A **port** is a numbered destination that helps a computer deliver a connection to the intended service. Here, RAWM is the client asking for work, and the inference process is the server doing it. A server does not have to be a separate physical computer.

The route name resembles a common chat API format, but this request is still going to the local engine. Using HTTP or an API does not inherently mean using the internet.

RAWM also checks a local `/health` endpoint while the server starts. That lets it wait for the engine to be ready or report an error rather than immediately sending a chat request to a server still loading.

### What streaming means

With streaming, the server sends pieces of the answer as they become available. RAWM reads those pieces from events whose lines start with `data:`. It does not wait for the entire answer before displaying anything.

```text
Server sends:   "Here" -> " is" -> " your" -> " function..."
Screen shows:   Here is your function...
```

A **token** is a model's unit of text processing. It may be a word, part of a word, punctuation, or another text segment. A streamed network piece is not guaranteed to be one whole word or exactly one model token.

Your app requests usage totals, reads available token counts, and displays them after the reply. Those are local inference counts; they do not spend your coding assistant's account token allowance.

The app also asks the model template to disable thinking generation through `enable_thinking = $false`. The model and engine determine support for that option. Its purpose in this setup is to favor direct answers without a displayed reasoning transcript.

### Generated code is still text

RAWM can return a PowerShell function, but the current chat implementation does not automatically execute the returned code. Its output handling displays the answer, stores it, and offers copy/export commands. This distinction explains why “ask the AI to write a program” and “run that program on Windows” are separate operations.

## 12. Settings, behavior instructions, and saved chats

These three kinds of information serve different purposes:

```text
+----------------------+ +----------------------+ +----------------------+
| settings.json        | | RAWM-BEHAVIOR.md     | | data/chats/*.json    |
| App configuration    | | Model instructions   | | Conversation history |
| Paths, limits, port  | | Style and behavior   | | Messages and usage   |
+----------------------+ +----------------------+ +----------------------+
```

### Settings: structured values the code reads

Here is a small, valid JSON example using values from your settings. It is an excerpt for teaching, not a replacement for the full file:

```json
{
  "backend": {
    "host": "127.0.0.1",
    "port": 18080,
    "contextSize": 4096
  }
}
```

The braces hold an object: a collection of named values. The names use double quotes. A colon separates a name from its value. Commas separate entries. `18080` is a number; `"127.0.0.1"` is text. Standard JSON uses `true` and `false` for booleans and does not use PowerShell's `$true` or `$false`.

This is why file type matters. A missing comma in JSON is a structural error, even if a person can guess what you meant. The reader follows the grammar rather than guessing.

Some important values in your actual configuration:

| Setting | Current value | What it means here |
|---|---:|---|
| `contextSize` | 4,096 | Context size requested when starting the server. It is a token budget, not a count of chats. |
| Fast `maxTokens` | 384 | Maximum output tokens requested for a fast response. |
| Code `maxTokens` | 2,048 | Maximum output tokens requested for a code response. |
| Fast `temperature` | 0.25 | A sampling setting; lower values generally favor more predictable choices. |
| Code `temperature` | 0.15 | The corresponding sampling setting for code mode. |
| `startupTimeoutSeconds` | 300 | How long startup may wait for engine readiness before reporting failure. |
| `unicodeBorders` | `true` | Use the curved box-drawing characters. |
| `showUsageAfterEachTurn` | `true` | Display the usage box after a completed response. |

Settings only have an effect if code actually reads them. For example, this file includes `routing.default`, but the present launcher supplies its own default of `auto`. Changing that JSON field alone would not change the launcher's default. This is a useful lesson to carry forward: a configuration label is not proof of a connected feature.

### Behavior Markdown: instructions to the local assistant

`context/RAWM-BEHAVIOR.md` contains natural-language directions such as answering directly, keeping ordinary replies short, providing complete code for the requested scope, and not claiming to have run tools without evidence.

When a new conversation is created, the application reads that text and puts it into a message with the role `system`. It influences the local model's behavior; it is not PowerShell code and does not itself enforce permissions or make correctness guaranteed.

The roles in a saved conversation are:

| Role | Purpose |
|---|---|
| `system` | The initial behavior instructions. |
| `user` | Your messages. |
| `assistant` | The model's replies. |

A resumed conversation restores its saved messages, including its original system message. Editing the behavior file later would affect newly created conversations; the current resume routine does not replace the old saved system message.

### Markdown syntax: the same format as this guide

Markdown is plain text with readable formatting cues. `#` introduces a heading, `-` introduces a list item, and backticks mark code. A fenced code block starts and ends with three backticks. A label such as `powershell`, `json`, or `text` after the opening fence helps a viewer display it appropriately.

The boxes in this guide are ordinary characters inside `text` code blocks. A fixed-width font keeps their edges aligned. They do not need a special diagram extension or a separate image file.

Markdown can be documentation in one place and model input in another. What matters is whether a program reads that file and what it does with the text. Merely placing a `.md` file in a folder does not execute it.

### Saved chats: remembering without retraining

`New-RAWMSession` creates an identifier from a timestamp and a short random suffix. The identifier becomes the filename under `data/chats`.

When saving, the app converts the session into JSON, writes a temporary `.tmp` file, then replaces the final `.json` file. This reduces the chance of leaving a partially written final file if the write is interrupted, although it is not a full backup or recovery system.

The app remembers a chat by loading its saved messages and sending conversation history with later requests. Your conversations do not retrain the model or change the `.gguf` weights.

There is also a difference between storage and context. A conversation can be saved on disk even when it is too long to fit into a future model request. This version does not implement its own automatic conversation summarizer; its configured context is finite.

Exports use Markdown and omit the system message. `/copy` uses the last completed answer, while `/copy code` extracts the first fenced code block from that answer.

Local chat saves are plain files, not encrypted by RAWM itself. When you eventually publish project material, select the code and documentation you intend to share; the `data/chats` and `exports` folders may contain your personal conversations.

## 13. How the word wrapping works

You noticed that some text extended beyond the area you could comfortably see. That was a product usability problem: a response is less useful when you have to chase it across the window.

The previous response path printed each incoming piece directly with `Write-Host ... -NoNewline`. The update added two helper functions:

| Function | Responsibility |
|---|---|
| `Get-RAWMTextWidth` | Measure visible console width, use a fallback if needed, and leave a one-column margin. |
| `Write-RAWMWrappedText` | Track the current output position and move words to another line when needed. |

```text
                   INCOMING RESPONSE PIECES
                              |
                 +------------+------------+
                 |                         |
                 v                         v
       Answer text accumulator     Display wrapping state
       Keeps the answer text       Pending word + column
                 |                         |
                 v                         v
       Save / copy / export         Wrapped terminal output
```

The state has two main values. `Pending` holds unfinished text that may still be part of a word. `Column` tracks how far across the current output line we have printed.

If one network piece ends in `str` and the next begins with `eaming`, the wrapper can wait for enough text to know the word is `streaming`. It does not assume every incoming piece ends at a sensible line break.

For ordinary words, the wrapper starts a new line when the next word will not fit. For a single very long string, it splits that string into chunks that fit. Existing newlines are honored. Tabs are expanded into spaces in the display path.

```text
Example at a deliberately small width:

+----------------------+
| This is a streaming  |
| response with words  |
| that fit the window. |
+----------------------+
```

The end of a response calls the wrapper with `-Flush`, meaning “print any pending final text; no more pieces are coming.” Without that step, a final word with no trailing space could remain buffered.

The answer accumulator is separate from this display transformation. Wrapping adds line breaks to what you see without inserting those display breaks into copied/exported code. The app already removes certain control characters and trims the completed answer; preserving formatting here means the wrapping itself does not rewrite the stored answer.

The status boxes also use the measured width instead of always assuming their previous fixed width. They retain a maximum inner width of 62 characters, becoming narrower when necessary.

This implementation wraps newly printed output. It does not rebuild old console history after you resize a window, and it does not replace the input editor. It counts string characters, so unusual wide characters or complex emoji may not line up as exactly as ordinary English text and code. Those are the practical limits of this small wrapper.

## 14. The function map

Nearly all of the application's behavior lives in `app/RAWM.psm1`. You do not have to read that file from top to bottom. Search for the function that owns the behavior you want to understand.

| Responsibility | Functions to look for | What to ask yourself |
|---|---|---|
| Overall chat flow | `Start-RAWMChat` | Where does a message enter, and what happens next? |
| Slash commands | `Invoke-RAWMCommand`, `Show-RAWMHelp` | Which commands are recognized? |
| Model selection | `Get-RAWMModelMode`, `Get-RAWMModelConfig` | How does a mode become a model path? |
| Engine lifecycle | `Start-RAWMServer`, `Test-RAWMServer`, `Stop-RAWMServer` | When is the model loaded and unloaded? |
| AI request and streaming | `Invoke-RAWMCompletion` | What gets sent, and how is the answer read? |
| New and resumed chats | `New-RAWMSession`, `Resume-RAWMSession` | Where does conversation state come from? |
| Message storage | `Add-RAWMMessage`, `Save-RAWMSession`, `Read-RAWMJson` | What is kept in memory and saved to disk? |
| Screen output | `Get-RAWMTextWidth`, `Write-RAWMWrappedText`, `Write-RAWMColor`, `Write-RAWMBox` | How does text become the interface? |
| Text cleanup | `Remove-RAWMControlSequence` | Which control characters are removed? |
| Usage display | `Write-RAWMUsage` | Which measurements are being shown? |
| Multiline input | `Read-RAWMMultiline` | What makes an input complete? |
| Clipboard | `Get-RAWMCodeBlock`, `Set-RAWMClipboard` | Which part of the last answer is copied? |
| Export | `Export-RAWMSession` | How is a chat turned into Markdown? |

The module ends with:

```powershell
Export-ModuleMember -Function Start-RAWMChat
```

This exposes one public starting function to callers. The other helpers remain internal to the module's implementation. Here, “export” means “make available outside the module”; it is different from exporting a conversation to a Markdown file.

### A practical way to read one function

Use five questions:

1. What is its name telling me it does?
2. Which inputs does `param(...)` accept?
3. Does it read or write a file, call another program, or just calculate a value?
4. What does it return or print?
5. What happens if something goes wrong?

For `Get-RAWMModelMode`, the answer is short: it accepts your text, checks the selected mode and keyword pattern, and returns `fast` or `code`. That is a manageable piece of the whole system.

## 15. Your everyday command guide

There are two places you type things: the PowerShell prompt and RAWM's own prompt.

```text
PS C:\Users\ROMAN> roman       <- PowerShell launches the app

roman > /fast                 <- RAWM changes its mode
roman > Hello!                <- RAWM sends a chat message
roman > /exit                 <- RAWM saves and closes

PS C:\Users\ROMAN>            <- Back in PowerShell
```

### At the PowerShell prompt

| Command | Meaning |
|---|---|
| `roman` | Open a new RAWM chat with automatic routing. |
| `roman -Mode fast` | Open with the smaller model selected. |
| `roman -Mode code` | Open with the larger model selected. |
| `roman -Resume SESSION_ID` | Load the named saved conversation; replace `SESSION_ID` with an actual saved ID. |
| `roman -NoBanner` | Open without the initial RAWM title box. |

The scripts also accept `-New`. In this version, starting without a resume ID already creates a new session, and that switch does not add separate behavior.

### Inside RAWM

| Command | What it does |
|---|---|
| `/help` | Displays available commands. |
| `/new` | Starts a clean conversation. |
| `/resume` | Loads the newest saved chat, which can be the current one if it is newest. |
| `/resume SESSION_ID` | Loads a particular saved chat. |
| `/auto` | Uses the keyword-based route for each new message. |
| `/fast` | Forces the smaller model for subsequent requests. |
| `/code` | Forces the larger model for subsequent requests. |
| `/model` | Shows the configured models, file presence, and routing mode. |
| `/usage` | Shows last-response and current-session token information. |
| `/paste` | Starts multiline input. End with `.send` on its own line or cancel with `.cancel`. |
| `/copy` | Copies the last completed answer to the Windows clipboard. |
| `/copy code` | Copies the first fenced code block from the last answer. |
| `/export` | Writes the current conversation to a Markdown file under `exports`. |
| `/stop` | Stops the tracked model server; a future chat request can start it again. |
| `/exit` | Saves, stops the app's tracked server, and returns to PowerShell. |

`/model` checks whether the configured files exist. It is useful status information, but file presence alone does not prove a model can load and answer. That is why we also performed actual response tests.

## 16. How we knew the repair worked

Testing means observing the intended behavior, not only checking that code looks reasonable.

These were the repair's concrete results:

| Check | Observed result | What that established |
|---|---|---|
| Profile inspection | Both repaired profiles pointed at the local start script. | The registration matched the requested local location. |
| Normal Windows account policy | `CurrentUser` showed `RemoteSigned`. | The setting was applied to the user's actual environment. |
| Fast-mode chat | A short greeting produced a real response and returned to the prompt. | The launcher, fast model, engine, and response path worked together. |
| Code-mode chat | The app returned a `Get-Greeting` PowerShell function that returned `"hello"`. | The larger model loaded and generated a coding response. |
| Final normal PowerShell launch | Calling `roman` produced a response without the earlier startup errors. | The real user entry command worked after the version handoff. |
| Word-wrapping check | Artificially split chunks, a long unbroken string, and indented text fit a simulated 20-column width. | The wrapper handled those cases while preserving the tested text content. |

The wrapping test used a controlled width and captured output; it was not a visual test of every terminal, font, emoji, or window size. The code-response test confirmed that the app generated the requested function; it did not automatically execute all model-generated code.

We did not retest the E-drive version during the local repair. You reported getting a similar experience on two computers; this guide's recorded technical verification covers the local computer repaired in this conversation.

### A small troubleshooting map for future understanding

These are clues to investigate, not a request to change your working setup:

| Symptom | A useful first place to look |
|---|---|
| Red errors appear before you type anything. | Profile path and the first parser error. |
| `roman` is not recognized. | Profile registration and command lookup. |
| “Running scripts is disabled.” | Execution policy in that exact shell/user environment. |
| “Module is missing.” | The app path and `app/RAWM.psm1`. |
| “Model is not installed.” | Configured model filename and the local model folder. |
| Interface opens, but the engine fails to start. | `data/logs` and the runtime dependencies. |
| A writing request uses Code unexpectedly. | The keyword router, particularly the word `write`. |
| An edit seems to have no effect. | Whether an old process still has the previous code loaded. |

For read-only inspection at a PowerShell prompt, these commands are useful to recognize:

```powershell
$PSVersionTable.PSVersion
$PROFILE
Get-Command roman -All
Get-ExecutionPolicy -List
```

They ask “Which PowerShell is this?”, “Which profile belongs here?”, “What does roman resolve to?”, and “Which policy values apply?” They do not reinstall the app or change its configuration.

## 17. How to approach your next project

You can use what you already did as a repeatable development process. The most useful improvement is to make your decisions and the evidence easier to carry between conversations.

```text
+-----------------------+
| Describe the outcome  |
+-----------+-----------+
            |
            v
+-----------------------+
| Name the constraints  |
+-----------+-----------+
            |
            v
+-----------------------+
| Sketch the pieces    |
+-----------+-----------+
            |
            v
+-----------------------+
| Build one useful path |
+-----------+-----------+
            |
            v
+-----------------------+       +-----------------------+
| Try it as the user    | ----> | Capture what failed    |
+-----------+-----------+       +-----------+-----------+
            ^                               |
            |                               v
            |                   +-----------------------+
            +-------------------| Fix the relevant part |
                                +-----------------------+
```

### Step 1: Describe the experience before naming a technology

You did this well by specifying an action and a result: “I want to open PowerShell, type roman, and talk to my assistant in the same window.” That gives the builder something observable to aim at.

A reusable sentence is:

> When I do **this action**, I want **this result**, because **this is how I will use it**.

### Step 2: State the boundaries

Your “do not touch the E-drive version” instruction mattered as much as the requested fix. It defined which files were in scope and protected a separate version while the local one was repaired.

Other concrete boundaries might be “keep my existing conversation files,” “use only local inference,” or “create documentation without changing the application.”

### Step 3: Ask for the components and their jobs

Before reading every line, ask:

> Show me the entry point, the main logic, the settings, the saved data, and the external dependencies. Tell me which file owns each responsibility.

That request produces a map like the one in this guide. It helps you recognize whether a future edit belongs in the launcher, the router, the display code, or somewhere else.

### Step 4: Define an observable success check

For RAWM, “the files exist” was too weak. A better check was “open normal Windows PowerShell, type roman, receive a fast response, receive a coding response, and exit successfully.”

For the wrapping feature, the specific check was “streamed text fits a narrow width, including words split across incoming chunks.” Different features need different evidence.

### Step 5: Give evidence when something feels wrong

Your screenshot contained the file path, line numbers, and parser complaints. That made the startup problem much more concrete than “nothing works.”

A helpful report has three parts: what you did, what you expected, and what actually appeared. Exact error text often lets the assistant start at the relevant layer instead of guessing.

### Step 6: Match the AI work session to the task

You described switching between Astra settings and continuing work with Luna when resources were tight. The transferable skill is choosing how much reasoning and context a particular task needs, then giving the next session a clear handoff.

Broad architecture questions and confusing failures benefit from careful investigation. A bounded follow-up such as “explain this function” or “update only this document” can be much easier to hand over. Whatever assistant or setting you use, ask for evidence before accepting that the behavior is fixed.

This guide does not assign permanent capability rankings to those model names. The useful part of your process is the judgment: recognizing when a task is narrow enough to continue and when it needs a fresh, more careful look.

### Step 7: Keep the decision and the reason together

A note such as “PowerShell 7 required” is helpful. A note such as “Direct Windows PowerShell execution hung; the startup script now forwards to PowerShell 7, which passed real launch tests” is better. It explains why the code exists and prevents another conversation from casually removing it.

You do not need to memorize syntax to begin doing this. As your vocabulary grows, you can ask increasingly precise questions: “Is this a parser error or a runtime error?”, “Is the setting actually read?”, “Are we testing the real entry point?”, and “Does this change the display or the saved data?”

## 18. What you can say when you share this

Here is a short description you can adapt in your own voice:

> I built RAWM, a local AI chat app that opens inside PowerShell when I type `roman`. I designed the experience and used AI coding assistants to help implement and troubleshoot it. PowerShell handles the interface, routing, and saved chats. llama.cpp runs the Qwen models locally, with a smaller model for quick replies and a larger one for code requests. I also added the features I wanted to use every day, including conversation export, copying code, usage information, and word wrapping.

For someone interested in the technical detail:

> The main app is a PowerShell module. A registered launcher finds it, ensures a compatible PowerShell runtime, and starts the chat loop. A keyword router chooses a model. The app sends the conversation to a local HTTP server at `127.0.0.1:18080`, streams the response, and saves the chat as JSON.

For a personal project story:

> I started with an experience I wanted, then learned by building it. I supplied the requirements, decided the priorities, tested it, and used the failures to understand things like profiles, execution policies, dependencies, and syntax. AI helped me write the code; I stayed responsible for what I wanted the product to do.

You can talk about being new to programming without treating that as an apology. Learning the names for the work you already participated in makes your story more precise.

## 19. A handoff note for a future conversation

The box below is written as a reusable note. It describes the implementation reviewed for this guide; a future assistant should inspect the then-current files before making changes.

```text
PROJECT: RAWM, Roman's local PowerShell AI chat application

USER EXPERIENCE
Open PowerShell, type roman, chat in the same terminal.
Keep the experience direct and readable.

LOCAL ROOT
C:\Users\ROMAN\Documents\ChatGPT\Rawm's local LLM

ENTRY POINT AND APP
Start-RAWM.ps1 -> app/RAWM.psm1 -> Start-RAWMChat

RUNTIME
Use PowerShell 7 for the application.
The start script forwards from older Windows PowerShell.
It can find pwsh.exe or use the known local Codex cache.
llama.cpp CPU runtime lives under runtime/llama.cpp.

MODELS
fast: Qwen3.5 0.8B Q4_K_M
code: Qwen3.5 4B Q4_K_M
auto: a PowerShell keyword rule chooses between them.

CONFIGURATION AND DATA
config/settings.json: engine, models, limits, interface
context/RAWM-BEHAVIOR.md: system instructions for new chats
data/chats: saved JSON conversations
data/logs: inference process logs
exports: Markdown conversation exports

KNOWN REPAIR HISTORY
Both edition-specific profiles had malformed nested code.
Registration repaired them and pointed roman at local C:.
The repair installed the missing local runtime and models.
Current-user RemoteSigned was set in Windows PowerShell.
PowerShell 7 forwarding resolved the tested startup hang.
Fast and Code produced real responses in local tests.
Display wrapping was added without altering saved line breaks.

BOUNDARIES
The local app was working to Roman's satisfaction.
Do not change it merely to modernize or refactor it.
Treat planning documents as historical intentions.
Do not touch the E-drive version unless Roman requests it.
Work only on the changes Roman asks for in the new task.
```

### Where this guide's details came from

The primary evidence is the current local source plus the observed repair and wrapping tests in our conversation. No private saved chat was needed to explain the implementation.

These links open the actual files on this computer:

- [Main application module](<C:/Users/ROMAN/Documents/ChatGPT/Rawm's local LLM/app/RAWM.psm1>)
- [Start script](<C:/Users/ROMAN/Documents/ChatGPT/Rawm's local LLM/Start-RAWM.ps1>)
- [Registration script](<C:/Users/ROMAN/Documents/ChatGPT/Rawm's local LLM/Register-RAWM.ps1>)
- [Installer](<C:/Users/ROMAN/Documents/ChatGPT/Rawm's local LLM/Install-RAWM.ps1>)
- [Unregistration script](<C:/Users/ROMAN/Documents/ChatGPT/Rawm's local LLM/Unregister-RAWM.ps1>)
- [Settings](<C:/Users/ROMAN/Documents/ChatGPT/Rawm's local LLM/config/settings.json>)
- [Behavior instructions](<C:/Users/ROMAN/Documents/ChatGPT/Rawm's local LLM/context/RAWM-BEHAVIOR.md>)

Those file links are specific to your computer. The explanation and text diagrams remain readable if you share the Markdown elsewhere. Official Microsoft and llama.cpp links appear beside the general technical explanations they support.
