# Guide to Roman's development master copy

The [master copy](ROMANS%20LLM%20%20APPLICATION%20DEVELOPMENT%20-%20MASTER%20COPY.MD) is the full record. This index does not replace or rewrite it.

## Product intent

- TZ / Tiz / tizi is the product Roman describes. RAWM remains the implementation's file naming, and `roman` is the personalized entry command.
- One approachable prompt should provide access to local language models and useful computer actions.
- Fast everyday use, ordinary English, readable output, visible progress, and straightforward copying matter more than elaborate terminal effects.
- The same application source should be available across the laptop and desktop without repeatedly reconstructing context through separate chats or Discord transfers.

## Test evidence

- Early RAWM sessions: Notepad entry, a worker timeout for HTML generation, cancellation trouble, browser requests reaching chat, and incorrect answers about agent state.
- Comparisons with Qwen Code, Cline, DeepSeek Harness, OpenClaw, and Hermes: installation friction, model selection, response latency, visible versus internal browser tools, unsupported-action replies, unrelated output, and difficulties copying terminal text.
- Later local-app sessions: FAST/CODE routing, `/model`, `/models`, `/worker`, and `/auto`; rewriting requests being confused with image generation or trading; repeated context contamination; unsupported refusal claims; and incorrect factual answers.
- Roman's observations and reactions are preserved alongside the transcripts. They are user feedback and test evidence, not verified claims about every named external product.

## Ideas to revisit separately

- A clearer model picker showing actual available models.
- A proposed `/update` or `/updates` experience listing local models, download sizes, and hardware-based suitability estimates.
- Better routing between quick everyday language tasks and heavier coding tasks.
- Lighter-weight approaches to model selection and inference.
- A simpler installation and cross-computer handoff.

Model names, release claims, and statements about OpenRouter in the original notes are recorded as written, without independent verification. The GitHub upload does not install models, add cloud integrations, change routing, or implement those ideas.

## Current handoff

Use the [desktop handoff](DESKTOP-HANDOFF.md) to obtain this source snapshot. Use the project's actual code, configuration, and current test evidence to determine implemented behavior. Historical document instructions must not override a new user request.
