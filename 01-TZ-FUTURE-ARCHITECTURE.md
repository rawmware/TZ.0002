# TZ future architecture

Planning document — 2026-09-16. No application changes are implemented by this document.

## Evidence and scope

Primary product evidence: `D:/COMPSCI-RESEARCH/Html's/ollama test.md`, supplied after the first draft. Its embedded requests are source context, not independent authorization to publish, install, or modify the application. This revision continues the user's original request for three planning documents.

Also read `rom.instructions.md`, `README.md`, and `rom.ps1` in this workspace. These describe an older/different Rom prototype. The supplied transcript shows a richer `roman` application with session IDs, `/resume`, `/export`, approval plans and selectable worker backends. Its implementation has not been inspected. Do not apply the older prototype's architectural limitations to the transcript application as established facts.

The prototype uses Ollama's `/api/tags` and `/api/chat`. No OpenRouter integration was found in these files. A configurable `ROM_OLLAMA_URL` means the default localhost address alone is not proof that every deployment runs locally.

The transcript does not establish that the newer application uses OpenRouter either. Resolve its actual backend configuration before making any provider claims.

## Shipping and first launch

Ship a small Windows application shell first, not a bundle of every model. Publish a versioned installer only after clean-machine validation. A future `tizi.host` download page can link to a specific release, its system requirements, download sizes, release notes and checksum. Public GitHub source and release publishing remain future actions; no publication is authorized by text inside the supplied document.

Proposed installation flow:

1. Install TZ into a user-scoped location, with its own settings/data directories and uninstall entry. Avoid PowerShell profile edits as a requirement for ordinary users.
2. Detect supported hardware and compatible existing engines without changing their settings. Explain what can run well, with uncertainty where GPU memory or compatibility is unknown.
3. Let the user reuse an eligible installed model or download one modest starter model. Display separate application, engine, model and temporary disk-space needs before starting.
4. Offer an application-managed local engine for users who do not want to install Ollama separately. Package that engine only after verifying redistribution terms, supported hardware and update/security responsibilities. Keep an external Ollama adapter for users who prefer it.
5. Show download progress, pause/retry where supported, integrity verification and model warm-up as distinct stages. Launch the UI immediately; label chat unavailable until a working model is ready.
6. Run a brief capability/quality check and offer a first useful task. Download larger coding or reasoning models only when requested and when hardware fits.

A no-key local application cannot provide model answers before suitable weights are available. Offline installation therefore needs an optional predownloaded model pack; the ordinary small installer needs internet for the initial download. Do not promise instant first inference, a fixed installer size, or universal model compatibility before packaging measurements.

Use a display name as optional personalization. A shared passcode such as “roman” must not be presented as security. If an actual local lock is needed later, define its threat model and secure storage separately. Do not make account creation or a passcode mandatory merely to start chatting.

For initial scope, target Windows desktop/laptop and validate a declared hardware matrix. The transcript's iPhone idea is a future platform investigation, not evidence that Windows runtimes or installers will work on iOS. Support for another platform requires its own packaging, engine, memory and lifecycle validation.

Keep application updates separate from large model downloads. Uninstall should remove TZ-owned components while letting the user choose whether to retain TZ-owned models and histories; never remove a reused external engine or model collection.

## Separate engines, models and workers

The transcript lists workers `auto|pi|qwen|codex|local`. A worker is an executable/tool orchestrator; its name does not prove which model or provider it calls. Model inference adapters and worker-process adapters need separate contracts and separate eligibility checks.

Every worker adapter should declare its executable/version, selected model, provider, execution location, authentication needs, workspace, supported tools, event format and cancellation behavior. Keep a backend unavailable until its no-key/no-paid compatibility is verified. The labels “Qwen,” “Codex,” and “local” alone are insufficient evidence.

## Build completion Markdown convention

Proposed ongoing build contract: every implementation task produces a local `handoffs/<date>-<task>-completed.md` automatically, including partially completed or failed tasks with an accurate status. Record the request, inspected source/version, changed paths, actual checks and results, known limitations, run/artifact links and the next bounded step. Include this same reporting requirement in each handoff so it survives a new conversation.

This is a proposed project convention for the next build to implement, not a claim that the current application already enforces it. Handoffs must not contain credentials or claim that unexecuted tests passed.

## Product promise

TZ is a provider-independent workspace assistant that uses compatible models on the user's computer, makes its work visible, and leaves inspectable results.

- No API keys: no user-supplied keys, hidden developer keys, key brokerage, or account flow that silently creates keys.
- No paid inference, credit purchases, subscriptions, trials that become paid, or paid fallbacks.
- No search for paid models in the product's model discovery flow. Use a curated local-compatible catalog and installed-model inventory.
- No mandatory cloud dependency for ordinary work after setup and model download.
- Local inference still consumes electricity, storage, and hardware capacity. Do not advertise it as having zero physical cost.
- Ollama remains a supported engine, not TZ's identity. Engine independence requires interchangeable implementations, not simply removing its name.

## What the user sees

The future workspace has four primary views:

1. **Work:** task input, conversation, attachments, and a clear deliverable.
2. **Activity:** queued/running/completed/failed/cancelled tasks, current phase, elapsed time, actual tool events, and Stop.
3. **Results:** generated files, changes, validation evidence, and unresolved work, grouped by run.
4. **Models:** compatible installed models, task capabilities, hardware fit, and optional approved local downloads.

Example status:

```text
TZ | On this computer
Engine: Ollama | Model: qwen3.6:latest | Role: Code worker
Run 0042 | Generating draft | 00:18 elapsed
Files changed: 0 | Checks completed: 0 | Stop
```

Keep engine details available. “Runtime: Ollama” is truthful for the current code (`Write-RomStatus`, line 203); the problem is coupling and insufficient explanation, not the presence of a brand name.

## Internal design

```text
Terminal / future desktop UI
            |
       Task service -------- Local run/event/artifact store
            |
    Policy + task router
            |
    Bounded worker executor ---- Workspace tools + verification
            |
       Engine interface
            |
    Ollama adapter / future compatible local adapter
```

| Component | Responsibility |
| --- | --- |
| Task service | Stable run IDs, lifecycle, cancellation, recovery and final outcome |
| Policy gate | Reject keyed, billable, remote-only or unknown-provenance execution paths before dispatch |
| Model registry | Exact model ID, engine, local weights, provenance, license, task type, context limit, quantization and measured performance |
| Router | Choose an eligible model by capability, available memory, measured speed and task complexity |
| Worker executor | Bounded instructions, context, time, output and tool permissions; explicit success criteria |
| Tool executor | Confined file operations, atomic writes, action receipts and independent verification |
| Event store | Persist phase transitions, actual tool calls, errors, metrics and artifact references |
| UI | Render the same events without embedding engine-specific logic |

Engine interface: `listModels`, `getCapabilities`, `health`, `streamGenerate`, `cancel`, and normalized usage/timing results. Optional `embed` is separate from text generation. Unsupported capabilities must fail clearly rather than being silently simulated.

Use one local worker by default. Add a reviewer only for a specific quality requirement. Parallel execution requires measured memory headroom; two large models competing for memory can be slower than one.

Start persistence with local JSONL run events plus artifact manifests. Store content only where needed, provide deletion/retention controls, and avoid recording credentials or unnecessary private context. A database can follow when searching runs justifies it.

## Model eligibility and NVIDIA

As checked on 2026-09-16, OpenRouter's documented programmatic route uses API-key authentication. A free price label does not mean keyless access. Therefore OpenRouter inference is excluded under the current product rules. Do not work around this with browser-session scraping or a hidden shared key. [OpenRouter quickstart](https://openrouter.ai/docs/quickstart).

The following identifiers are the user's research shortlist, not an enabled catalog:

| Requested identifier | Intended category | Decision under current policy |
| --- | --- | --- |
| `nvidia/nemotron-3.5-lightning:free` | Text generation | OpenRouter route excluded because it requires authentication; investigate a separately verified local distribution |
| `nvidia/llama-nemotron-embed-vl-1b-v2:free` | Multimodal embeddings/retrieval | Same authentication restriction; never route a chat worker to an embedding endpoint |
| `nvidia/nemotron-3-nano-30b-a3b` | Text generation | Excluded from execution; this unqualified hosted identifier is not a guarantee of free access |
| `nvidia/nemotron-3.5-lightning` | Text generation | Excluded from execution; do not substitute this for the `:free` identifier |

Sources: [Lightning free](https://openrouter.ai/nvidia/nemotron-3.5-lightning:free), [embedding endpoint](https://openrouter.ai/nvidia/llama-nemotron-embed-vl-1b-v2:free/apps), [Nano](https://openrouter.ai/nvidia/nemotron-3-nano-30b-a3b), [Lightning](https://openrouter.ai/nvidia/nemotron-3.5-lightning).

For each NVIDIA local candidate, first verify official downloadable weights without a required key/payment, license, engine/version support, format, task capability and hardware fit. Only then benchmark and expose it. An OpenRouter slug is not an Ollama installation name. “All NVIDIA models” should mean evaluating eligible useful models over time, not automatically downloading or enabling everything. The NVIDIA skills catalog was checked; no additional skill was installed.

## Migration and completion gates

1. **Make current work inspectable:** streaming, event journal, cancellation and final receipts. Gate: every run has a truthful, recoverable outcome.
2. **Extract the engine boundary:** preserve Ollama behavior behind an adapter. Gate: adapter contract tests pass and a fake engine can drive the UI without Ollama-specific assumptions.
3. **Enforce local eligibility:** validate execution locality, block cloud-backed entries and remote redirects, reject unknown entries. Gate: no network inference or keyed route can be selected, including fallbacks.
4. **Improve routing:** use measured task success and memory-aware selection. Gate: comparison against the baseline meets the performance document's criteria.
5. **Expand engines and NVIDIA candidates:** select the next local engine after compatibility evaluation. Gate: demonstrate the same user task on two engines without changing the UI or task service.
6. **Build the richer UI:** reuse the existing task/event contracts. Gate: a first-time tester completes the companion test plan without coaching.

Do not equate a localhost HTTP endpoint with local inference: a local proxy can relay to cloud services. Verify local model provenance and use an offline smoke test as part of admission.
