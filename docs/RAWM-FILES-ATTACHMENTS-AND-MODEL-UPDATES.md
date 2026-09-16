# RAWM attachments and automatic model updates

## A plain-English engineering guide for the next version

This document answers two connected questions:

1. Why can you drag a file toward a terminal, but RAWM cannot automatically understand that file yet?
2. How could RAWM discover and install newer models in the future instead of depending on today's fixed model files?

This is a design and learning document. It describes future capabilities; it does not add them to the working application. The current local application and the E-drive version remain unchanged.

## The quick answer

When you drag an image or file into a terminal, the terminal usually inserts a **path** such as:

```text
C:\Users\ROMAN\Pictures\idea.png
```

It usually does not send the image's pixels or the file's contents into the program. RAWM currently reads text from the keyboard with `[Console]::ReadLine()`. It receives the path as text and has no attachment pipeline that says:

```text
path -> identify file -> read file -> understand file -> include it in AI request
```

That is why the current app cannot automatically understand a dragged image.

This is partly a software-feature issue and partly a model-capability issue. A bigger model alone would not fix it. RAWM would first need code that accesses and prepares the file. For images, the selected model and inference runtime would also need vision support.

Model updates work in a similar way. A newer model does not announce itself to RAWM automatically. The app needs a trusted catalog that says what models exist, where their files are, which capabilities they have, which runtime they require, and how to verify the downloads.

```text
Current version:
fixed settings -> fixed filename -> fixed download URL

Future version:
model catalog -> choose compatible release -> verify -> install -> activate
```

## 1. What the terminal actually receives

There are three different things people casually call “pasting a file.” They are not the same.

| Action | What normally reaches a text terminal | Does RAWM currently understand it? |
|---|---|---|
| Type words | Characters from standard input. | Yes. |
| Copy and paste text | Characters inserted into the prompt. | Yes, including multiline input through `/paste`. |
| Drag a file from Explorer | Often the file path, usually quoted if it contains spaces. | It sees text, but does not treat it as an attachment. |
| Copy a file in Explorer and paste into a terminal | Host-dependent text or path behavior. | No file-object handling exists. |
| Drop image pixels into a terminal | Usually no pixel data is delivered. | No. |

The terminal is primarily a **text stream**. Its normal contract looks like this:

```text
keyboard / paste / drag action
              |
              v
       characters in stdin
              |
              v
        PowerShell ReadLine
              |
              v
         RAWM receives text
```

A file is different:

```text
Explorer file object
       |
       v
file path + permissions + bytes on disk
       |
       v
application must open and interpret it
```

The terminal does not decide what an image means. It does not know whether a `.pdf` should be converted to text, whether a `.png` should go to an OCR system, or whether a `.ps1` should be treated as code or merely discussed. That decision belongs in the application.

## 2. What happens when you drag an image

Imagine dragging this image into the terminal:

```text
C:\Users\ROMAN\Pictures\concept.png
```

The terminal may insert:

```text
roman > "C:\Users\ROMAN\Pictures\concept.png"
```

RAWM's current input code reads the entire line as a string. In simplified form:

**File type:** PowerShell module (`.psm1`)  
**File:** `app/RAWM.psm1`

```powershell
Write-RAWMColor 'roman > ' Cyan -NoNewline
$inputText = [Console]::ReadLine()
```

At this moment, `$inputText` contains something like:

```text
"C:\Users\ROMAN\Pictures\concept.png"
```

It does not contain:

```text
the image pixels
the image dimensions
the image color data
the image's visual meaning
```

The current router then searches the text for keywords. A path ending in `.png` is not a keyword that tells RAWM to load an image. The current request body also contains a `messages` collection made from text roles and content. There is no file lookup, byte read, OCR step, image encoder, or image message object.

This is not the model “being too dumb” in the first instance. The application has not handed the model the image.

## 3. Why copy and paste is different from a file attachment

When you copy text, the clipboard contains text. The terminal can insert that text into its input buffer.

When you copy a file in Windows Explorer, the clipboard can contain a list of file objects. A normal text reader such as `[Console]::ReadLine()` does not automatically ask the clipboard for that list. It only waits for characters typed or pasted into the terminal.

```text
Text clipboard:
    "Write a function that says hello"
            |
            v
    terminal inserts characters

File clipboard:
    [image.png file object]
            |
            v
    terminal needs special clipboard code
    to discover the file path
```

A future PowerShell helper could inspect the Windows clipboard through .NET APIs, but that is a separate feature from ordinary console input. It must also handle situations where the host does not expose a graphical clipboard, where the clipboard is locked by another application, or where the terminal host converts a file drop to a path instead.

The easier first feature is path-based attachment:

```text
roman > /attach "C:\Users\ROMAN\Pictures\concept.png"
```

The terminal only needs to deliver the path. RAWM can then open the file itself.

## 4. Is the problem memory?

Memory matters, but it is only one part of the problem. There are four separate bottlenecks.

```text
file access
     |
     v
file interpretation
     |
     v
model capability
     |
     v
memory and context limits
```

### File access

RAWM needs permission to open the path. The path may be wrong, disconnected, protected, or outside the application's allowed workspace.

### File interpretation

The app needs a reader for the file type:

| File | First processing step |
|---|---|
| `.txt`, `.md`, `.ps1`, `.json` | Read text with the correct encoding. |
| `.csv`, `.tsv` | Parse rows and columns, then summarize or select relevant rows. |
| `.pdf` | Extract text, and possibly run OCR for scanned pages. |
| `.docx` | Read the document package and extract paragraphs, tables, and metadata. |
| `.png`, `.jpg` | Decode pixels, then send them to a vision-capable model or OCR/captioner. |
| `.xlsx` | Read workbook sheets and ranges with a spreadsheet library. |
| `.zip` | Inspect its contents carefully; do not blindly send every file. |

A model cannot understand a PDF merely because the PDF path was placed in a prompt. The application must extract useful information first.

### Model capability

A text-only model can work with text extracted from an image, but it cannot reason about the original visual scene unless an image-processing step translates the scene into words. A vision-language model can accept image data when the runtime and request format support it.

The current RAWM application sends text chat messages. It does not currently send an image payload. Even if a future `.gguf` file supports vision, RAWM would still need to prepare and send the image correctly.

### Context size

The **context window** is how much conversation and input the model can consider in one request. A large document can exceed that limit even when the computer has plenty of RAM.

```text
computer RAM / VRAM
    -> can the model and runtime stay loaded?

context window
    -> can this request contain the conversation and file text?

response limit
    -> how much new text may the model generate?
```

These are different limits. RAWM's current `contextSize` is 4,096, while Fast and Code have different output caps. Increasing the model's context setting would not automatically teach the app how to extract a PDF or interpret an image.

### Computation time

Images need decoding and possibly visual encoding. PDFs may need OCR. Large files may need chunking and summarization. Those steps cost CPU, memory, and time before the model starts answering.

## 5. What a file-aware RAWM feature would look like

A practical attachment feature could use this pipeline:

```text
1. User drags a file or types /attach path
                         |
                         v
2. RAWM extracts and normalizes the path
                         |
                         v
3. RAWM verifies the file exists and is allowed
                         |
                         v
4. RAWM identifies type, size, and encoding
                         |
                         v
5. RAWM extracts text, OCR, metadata, or image input
                         |
                         v
6. RAWM limits or chunks the prepared content
                         |
                         v
7. RAWM adds an attachment summary to the request
                         |
                         v
8. The local model answers using that prepared context
```

The model should not receive an unbounded file automatically. The app should show the user what it found:

```text
Attached: concept.png
Type: image/png
Size: 1.8 MB
Visual processing: available / unavailable
Ready to send with your next message.
```

That gives the user a chance to catch a wrong path or a private file before it is processed.

## 6. A beginner-friendly attachment design

The simplest user experience would be:

```text
roman > /attach "C:\Users\ROMAN\Documents\notes.md"
Attached notes.md.
roman > Summarize the attached notes in five bullets.
```

For a picture:

```text
roman > /attach "C:\Users\ROMAN\Pictures\concept.png"
Attached concept.png.
roman > What do you notice in this image?
```

The attachment would become part of the current RAWM session, but the app should keep the original path and a prepared representation separately:

```text
attachment record
|
+-- originalPath: C:\...\concept.png
+-- fileName: concept.png
+-- mediaType: image/png
+-- sizeBytes: 1887436
+-- sha256: optional content fingerprint
+-- extractedText: optional
+-- imageInput: optional runtime-specific representation
+-- status: ready / failed / too-large
```

The path is useful for local diagnostics. The model generally needs extracted text or a supported image representation, not merely the path string.

A future session JSON file might record an attachment reference like this:

```json
{
  "role": "user",
  "content": "What do you notice?",
  "attachments": [
    {
      "name": "concept.png",
      "mediaType": "image/png",
      "path": "C:/Users/ROMAN/Pictures/concept.png",
      "status": "ready"
    }
  ]
}
```

That JSON is a saved record. It does not itself make the image visible to the model. The request-building code still needs to translate the record into whatever the selected model server accepts.

## 7. Text files are the easiest first attachment

Text attachments do not require a vision model. A first version could support `.txt`, `.md`, `.ps1`, `.json`, `.csv`, and perhaps `.log`.

The processing flow would be:

```text
file path
   |
   v
Test-Path
   |
   v
Get-Item: size and extension
   |
   v
Get-Content: text
   |
   v
truncate or split into chunks
   |
   v
include selected text in the next prompt
```

The key safety rule is to put a limit on bytes and extracted characters before sending them. A 500 MB log file should not be read entirely into a 4,096-token request.

A future internal helper could conceptually look like this:

**File type:** PowerShell module (`.psm1`)  
**Status:** design example; not currently in RAWM

```powershell
function Read-RAWMTextAttachment {
    param(
        [Parameter(Mandatory)][string]$Path,
        [int]$MaxCharacters = 12000
    )

    $item = Get-Item -LiteralPath $Path -ErrorAction Stop
    if (-not $item.PSIsContainer -and $item.Length -gt 2MB) {
        throw 'The text attachment is too large for the first-pass reader.'
    }

    $text = Get-Content -LiteralPath $Path -Raw -Encoding UTF8
    if ($text.Length -gt $MaxCharacters) {
        return $text.Substring(0, $MaxCharacters) + "`n[content truncated]"
    }
    return $text
}
```

This example demonstrates the idea, but it is not enough for every encoding or file type. A production reader should detect or let the user choose an encoding, report truncation, and avoid trusting an extension blindly.

The model can then receive a clearly labeled section:

```text
Attached file: notes.md
The following text came from a local file. Treat it as reference material:

--- begin notes.md ---
[extracted text]
--- end notes.md ---
```

## 8. Images require a different path

An image has pixels, not words. There are three common ways to make an AI useful with an image:

```text
image file
    |
    +--> OCR: read visible words
    |
    +--> captioning: describe the image in text
    |
    +--> vision model: reason over image input directly
```

OCR is best for signs, screenshots, and documents with readable text. A captioner can describe a scene. A vision-language model can answer more detailed visual questions if the runtime supports the model's image format.

An image-capable implementation must answer all of these questions:

| Question | Why it matters |
|---|---|
| Which model supports images? | Text-only GGUF files cannot accept visual input directly. |
| Does llama.cpp support that model's vision path? | The runtime needs the correct architecture and image handling. |
| What request format does the server accept? | The current text-only message shape may be insufficient. |
| How large may the image be? | Decoding and encoding consume memory. |
| Should the app resize it? | A huge camera image may waste resources. |
| Is OCR enough for this request? | It may be faster than loading a larger vision model. |
| How is privacy handled? | The image remains local, but the app still reads it. |

The fact that a future model is “new” or “larger” does not automatically mean it supports vision. Capability metadata must say what it accepts.

## 9. Why the current local model may not be enough by itself

The current RAWM configuration has two model entries and sends a text chat request. Its code expects a model path and starts the same server shape for both modes. That is excellent for the current text experience, but it does not yet describe:

```text
vision encoder
image projector
OCR engine
PDF reader
spreadsheet reader
attachment metadata
file permission checks
```

A future attachment feature could begin with text files and add image support later. That is a sensible progression because text extraction uses the existing text-model path, while direct image understanding introduces a new model and runtime contract.

## 10. How the current model installer works

The present installer is intentionally simple. It has a fixed component list:

```powershell
param(
    [ValidateSet('runtime','fast','code','all')]
    [string]$Component = 'all'
)
```

It checks whether an expected file exists. If not, it downloads a fixed URL:

```powershell
if ($Component -in @('fast','all')) {
    $target = Join-Path $modelsDir 'Qwen3.5-0.8B-Q4_K_M.gguf'
    if (-not (Test-Path -LiteralPath $target)) {
        Get-RemoteFile 'https://huggingface.co/notschmee/Qwen3.5-0.8B-GGUF/resolve/main/Qwen3.5-0.8B-Q4_K_M.gguf?download=true' $target
    }
}
```

The Code model follows the same pattern:

```powershell
if ($Component -in @('code','all')) {
    $target = Join-Path $modelsDir 'Qwen3.5-4B-Q4_K_M.gguf'
    if (-not (Test-Path -LiteralPath $target)) {
        Get-RemoteFile 'https://huggingface.co/bartowski/Qwen_Qwen3.5-4B-GGUF/resolve/main/Qwen_Qwen3.5-4B-Q4_K_M.gguf?download=true' $target
    }
}
```

This means the current application does **not** automatically know that a new Qwen release exists. It knows only the URLs written into `Install-RAWM.ps1` and the filenames written into `config/settings.json`.

That is not a flaw in the current working setup. Fixed versions are easier to test and less likely to change unexpectedly. Automatic updating is a new product feature with its own safety and compatibility requirements.

## 11. Where a future updater gets its information

A model updater needs a catalog. The catalog can be hosted by a model provider, an organization, a release server, or a repository such as Hugging Face.

The catalog should contain metadata, not only a display name:

```text
model ID
human-readable name
publisher
repository
exact revision or release
exact filename
download URL or provider coordinates
SHA-256 checksum
file size
format
capabilities
context limit
recommended quantization
minimum runtime version
hardware requirements
status: stable / beta / deprecated
```

The model's name does not tell the app where to download it. A repository identifier and filename do. The catalog is the map.

The Hugging Face Hub documentation describes downloading individual files or complete repository snapshots, and supports revisions so a consumer can identify a particular version rather than relying only on a moving `main` branch: [Hugging Face download documentation](https://huggingface.co/docs/huggingface_hub/guides/download).

The llama.cpp server documentation also describes selecting a Hugging Face repository with `-hf`, including a repository and optional quantization selection: [llama.cpp server documentation](https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md).

Those mechanisms make discovery possible, but they do not remove the need for compatibility checks, checksums, storage checks, and a rollback plan.

## 12. A future model catalog

**File type:** JSON (`.json`)  
**Suggested file:** `config/model-catalog.json`  
**Status:** design example; not currently in RAWM

```json
{
  "catalogVersion": 1,
  "publishedAt": "2026-09-13T00:00:00Z",
  "models": [
    {
      "id": "qwen-fast-0.8b-q4km",
      "displayName": "Qwen Fast 0.8B Q4_K_M",
      "mode": "fast",
      "provider": "huggingface",
      "repository": "publisher/repository",
      "revision": "exact-commit-or-release",
      "filename": "model-file.gguf",
      "sha256": "known-checksum",
      "sizeBytes": 590880672,
      "capabilities": ["text"],
      "contextTokens": 4096,
      "minimumRuntime": "known-compatible-version",
      "status": "stable"
    }
  ]
}
```

The names in this example are placeholders. The actual publisher, repository, revision, filename, checksum, and compatibility values must come from a real verified release.

The catalog separates two questions:

```text
What model should the user see?
        |
        v
What exact bytes should the computer download?
```

That separation is what lets an app display friendly names while still using exact, reproducible artifacts.

## 13. How an updater would decide what to install

The updater should not simply choose the newest name. It should filter the catalog against the computer and the user's request.

```text
fetch catalog
     |
     v
filter by capability: text or vision
     |
     v
filter by mode: fast or code
     |
     v
filter by operating system and CPU architecture
     |
     v
filter by available RAM / VRAM and storage
     |
     v
filter by runtime compatibility
     |
     v
choose stable release and preferred quantization
     |
     v
show user what will be downloaded
```

For example, the best “new model” for Roman's computer might not be the largest release. It may be a smaller quantized file that fits in memory and answers quickly. A model catalog gives the app enough information to make that decision transparently.

Possible selection rules:

| User request | Catalog filter |
|---|---|
| `/update-models` | Look for newer stable releases of currently installed roles. |
| `/update-models fast` | Look for a newer compatible Fast model. |
| `/install-model vision` | Look for a model whose capabilities include `vision`. |
| `/model latest` | Show eligible releases, then ask which to activate. |
| automatic startup check | Check metadata quietly and notify only if a compatible update exists. |

The app should show the choice before a large download:

```text
Update available

Current Fast: Qwen3.5 0.8B Q4_K_M
Candidate:    Qwen 3.9.1 1.5B Q4_K_M
Size:         1.1 GB
Capability:   text
Runtime:      compatible

Download and install? [y/N]
```

Do not silently replace a working model while the user is in the middle of a chat. Download in the background or on an explicit command, then activate at a controlled boundary.

## 14. Safe download and activation flow

An updater should treat model files like large software artifacts:

```text
1. Fetch catalog over HTTPS
2. Parse and validate catalog
3. Compare revision and checksum to installed record
4. Check free disk space
5. Download to filename.partial
6. Verify file size and SHA-256
7. Move into a versioned model folder
8. Update an active-model pointer atomically
9. Keep the previous model for rollback
10. Test health and one short completion
```

The key word is **verify**. A successful HTTP download only proves that bytes arrived. It does not prove that the bytes are the intended model, that the transfer was complete, or that the model works with the installed runtime.

A versioned folder could look like:

```text
models/
|
+-- qwen-fast-0.8b-q4km/
|   +-- model.gguf
|   +-- model.json
|
+-- qwen-fast-3.9.1-1.5b-q4km/
|   +-- model.gguf
|   +-- model.json
|
+-- installed.json
+-- active.json
```

`active.json` could point to the selected directory. Keeping old versions costs disk space, but it makes rollback possible if the new model is slower, incompatible, or less useful.

An installed record might contain:

```json
{
  "id": "qwen-fast-0.8b-q4km",
  "revision": "exact-commit-or-release",
  "path": "models/qwen-fast-0.8b-q4km/model.gguf",
  "sha256": "verified-checksum",
  "installedAt": "2026-09-13T00:00:00Z",
  "lastHealthCheck": "passed"
}
```

The active pointer should be changed only after the new file is complete and verified. That is an **atomic activation** idea: the app should see either the old complete model or the new complete model, not a half-downloaded file.

## 15. Why “latest” is more complicated than it sounds

“Newest model” can mean different things:

```text
newest training release
newest quantized conversion
newest compatible runtime build
newest file in a repository
newest stable release
newest version that fits this computer
```

Those are not always the same artifact.

A repository can contain several quantizations of one model. A model publisher can update files without changing the friendly name. A community conversion can appear after the original model release. A new format can require a newer runtime. A larger model can be newer but unusable on a low-memory computer.

That is why a robust catalog should use stable IDs and exact revisions. A moving URL such as a repository's `main` branch is convenient for experimentation but weak for reproducible application behavior.

The updater should compare:

```text
installed model ID + revision
against
catalog model ID + revision
```

It should not compare only the human-readable display name.

## 16. How the current installer would evolve

The current implementation has this simple behavior:

```text
if expected filename exists:
    skip download
else:
    download the hard-coded URL
```

The future behavior could become:

```text
read current installed record
fetch trusted catalog
find compatible candidate
compare exact revision
ask before large download
download partial file
verify checksum
install versioned artifact
activate after health test
```

The existing installer can stay as a reliable bootstrapper while a new updater is added separately. That reduces the chance that changing update logic breaks first-time setup.

Possible future commands:

```text
roman --check-updates       launch and check model catalog
roman --update-models       check, ask, download, verify, activate
roman --model-list          show installed and available models
roman --model fast          choose the active Fast model
roman --model rollback      restore the previous active model
```

Inside the chat, equivalent slash commands could be:

```text
/models
/check-updates
/update-models
/model fast
/rollback-model
```

These names are design ideas. They are not commands in the current RAWM application.

## 17. How the app could recognize a dropped file

The first implementation could keep the normal input line and add path detection:

```text
roman > "C:\Users\ROMAN\Pictures\concept.png"
```

The app would then ask:

```text
Does this text look like a path?
        |
        v
Does that path exist?
        |
        v
Is it a file type we support?
        |
        v
Attach it or treat the line as ordinary text?
```

Path detection must be conservative. A message can contain a path as an example without asking RAWM to open it. An explicit `/attach` command is clearer:

```text
/attach "C:\Users\ROMAN\Pictures\concept.png"
```

The application could accept both methods, but the explicit command should be the reliable path.

The future command handler might conceptually contain:

**File type:** PowerShell module (`.psm1`)  
**Status:** design example; not currently implemented

```powershell
function Add-RAWMFileAttachment {
    param([Parameter(Mandatory)][string]$Path)

    $item = Get-Item -LiteralPath $Path -ErrorAction Stop
    if ($item.PSIsContainer) {
        throw 'Attach a file, not a folder.'
    }

    $mediaType = Get-RAWMMediaType $item.Extension
    $attachment = [pscustomobject]@{
        Path = $item.FullName
        Name = $item.Name
        MediaType = $mediaType
        SizeBytes = $item.Length
        Status = 'pending'
    }

    [void]$script:Session.attachments.Add($attachment)
    Write-RAWMColor "Attached: $($item.Name)" Green
}
```

This example introduces two ideas:

- `Get-Item` obtains metadata about a path.
- the session keeps an attachment record instead of pretending the path itself is the file content.

The missing `Get-RAWMMediaType` function would map `.png` to `image/png`, `.md` to `text/markdown`, and so on. A robust implementation should use both extension and detected content where practical.

## 18. File processing by type

After attachment, a dispatcher can choose a preparation function:

```text
extension / detected type
             |
             +--> text       -> Read-RAWMTextAttachment
             +--> PDF        -> extract text / OCR
             +--> DOCX       -> extract paragraphs and tables
             +--> spreadsheet -> select sheets and ranges
             +--> image      -> OCR, caption, or vision input
             +--> archive    -> inspect contents with explicit limits
```

The preparation result should be labeled:

```text
Prepared attachment: notes.md
Characters extracted: 8,240
Included in next request: yes
```

For a large file:

```text
Prepared attachment: server.log
Characters extracted: 240,000
Context budget: too small for all content
Action: split into chunks or summarize first
```

This prevents the user from wondering whether RAWM silently ignored half the file.

A good first release would support a small, explicit set of formats and state unsupported types clearly. “I do not support this file type yet” is more useful than pretending the model read it.

## 19. Images and future vision support

An image-capable path needs more than a larger text model:

```text
image bytes
    |
    v
image decoder
    |
    v
resize / normalize / validate
    |
    +--> OCR text path
    |
    +--> vision encoder / image projector
                    |
                    v
             vision-language model
                    |
                    v
             local response server
```

The engineer must verify that the selected model and runtime support the same vision architecture and request format. The catalog's `capabilities` field should distinguish `text`, `vision`, and possibly `ocr`.

An image request should also declare what happened:

```text
Image attached: screenshot.png
Visual model: available
Image resized: 1,920 x 1,080 -> 1,024 x 576
Included in request: yes
```

If vision is unavailable, the app could offer:

```text
Vision is unavailable for the active model.
Try OCR-only processing, choose a vision model, or continue without the image.
```

That is a capability message, not a memory error. Memory may still determine whether the vision model can run, but the app should explain which condition failed.

## 20. A future attachment-aware request

The current request contains text messages. A future request builder would need a normalized internal representation:

```text
user message
    |
    +--> plain text content
    +--> prepared text attachments
    +--> image inputs for a compatible vision model
```

One possible internal model is:

```json
{
  "role": "user",
  "parts": [
    {
      "type": "text",
      "text": "What do you notice?"
    },
    {
      "type": "image",
      "path": "C:/Users/ROMAN/Pictures/concept.png",
      "mediaType": "image/png"
    }
  ]
}
```

This is a design representation. The exact wire format depends on the local server and model. The application should convert this internal structure into the format supported by the selected runtime rather than assuming every model accepts the same payload.

## 21. Suggested development phases

```text
Phase 1: text attachments
    .txt, .md, .ps1, .json, .log

Phase 2: structured documents
    CSV, PDF, DOCX, XLSX

Phase 3: clipboard file lists
    detect files copied from Explorer

Phase 4: image preparation
    OCR and basic image metadata

Phase 5: direct vision
    compatible vision model + runtime payload

Phase 6: model catalog
    list, check, verify, install, rollback
```

Text attachments are the best starting point because they use the existing model request path. Model updating can be developed separately behind a catalog and installed-model record.

Avoid combining every future feature into the first attachment change. File access, document extraction, vision support, model selection, and updating each create their own failure modes.

## 22. A simple mental model for model updates

Think of the app as a phone with an app store, except the models are large local packages:

```text
catalog = store shelf
model ID = product identity
revision = exact edition
checksum = seal proving the package is intact
installed record = receipt
active pointer = which edition to use now
rollback = reinstall the previous edition
```

The model does not need to “know” where to look. The updater code knows because the catalog tells it. If a provider changes repository names, filenames, or conversion formats, the catalog is updated rather than scattering new URLs through the chat code.

## 23. What “staying updated” should feel like to Roman

The user experience should stay simple:

```text
roman > /check-updates

Checking the model catalog...
New compatible model found: Qwen 3.9.1
Size: 1.1 GB | Capability: text | Fits this computer: yes

Install it now? [y/N]
```

After installation:

```text
Downloaded: complete
Checksum: verified
Compatibility: passed
Active model: Qwen 3.9.1
Previous model: available for rollback
```

If no update exists:

```text
RAWM is up to date for the current Fast and Code roles.
```

If the catalog cannot be reached:

```text
The model catalog could not be reached.
Continuing with the locally installed models.
```

The chat should remain available with the installed model when an update check fails. An update service should be an enhancement, not a requirement for existing local functionality.

## 24. Engineer handoff summary

The current application has two independent future opportunities:

```text
Attachment support                         Model update support
------------------                         --------------------
accept path or file object                 fetch catalog metadata
validate file                              choose compatible artifact
extract text / prepare image               download partial file
respect context budget                     verify checksum
add prepared input to request              activate versioned model
show what was attached                     preserve rollback path
```

The terminal is not the main limitation. It is the narrow entry channel. The application can expand that channel by treating a dropped path as a reference to a file and then doing the real file work itself.

The local model is not the only limitation either. Memory, context size, runtime support, file readers, image capability, and safety boundaries all matter. A larger model may improve answers, but it cannot replace the missing attachment pipeline.

For model freshness, the app needs a catalog and exact artifact metadata. A new release will not be discovered by the current fixed installer until someone changes its URL or adds an update mechanism. A catalog-driven updater can make that process visible, verifiable, and reversible.

## References

The current RAWM behavior described here comes from the local files:

```text
app/RAWM.psm1
Install-RAWM.ps1
config/settings.json
```

The future model-discovery design is informed by these primary project references:

- [llama.cpp README](https://github.com/ggml-org/llama.cpp)
- [llama.cpp server documentation](https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md)
- [Hugging Face Hub download guide](https://huggingface.co/docs/huggingface_hub/guides/download)

The exact model repository, revision, quantization, runtime compatibility, and vision support must be verified for each future release. A friendly display name alone is not enough to safely install a model.
