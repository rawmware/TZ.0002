# ROMAN / RAWM: What I Want From My Local AI

## Purpose of this handoff

This document captures my requirements for the next conversation. The request in this conversation was to write this handoff, not to modify the application yet.

## The problem

I want a local AI assistant that understands normal language and actually does things on my computer. The current experience is unacceptable because it makes me learn commands and still fails to perform a simple action.

In my Windows terminal, I entered `roman` to start the program. The interface displayed RAWM, routing AUTO, and Agent ON. I asked:

> open note pad and write - hello green world /agent

The application routed the request to CODE using Qwen3.5 4B Q4_K_M. It answered that it could not open applications or write to the local file system and told me to use `/act`.

I then asked:

> open note pad and write hello green world /act

It again refused to act and told me to run the command in the application's agent controller.

This left me stuck in a loop. The screen said the agent was on, but the assistant behaved as if it had no ability to take action.

These are observed symptoms. The underlying cause still needs to be established from the project and a focused reproduction.

## The experience I want

I should be able to say, in ordinary language:

> Open Notepad and write hello green world.

The assistant should understand the request, prepare the action, and ask for approval in plain language:

> Open Notepad and type “hello green world”? Approve: y / Decline: n

- If I enter `y`, it should perform the action, check the result, and briefly report what happened.
- If I enter `n`, it should cancel without performing the action.
- If it needs essential information, it should ask a short, understandable question.
- If execution fails, it should explain the actual failure and a useful next step.

I should not have to type `/agent`, `/act`, select an internal mode, or understand an agent controller. Optional advanced commands can exist, but ordinary users must be able to complete ordinary tasks without them.

The goal is fluent conversation followed by useful action. GPT, Claude, and my recent experience using Qwen Code are the interaction references: I describe what I want, and the system handles the technical steps.

## Product requirements

1. **Natural language is the main interface.** Recognize requests to act as requests to act, rather than answering with instructions for me to execute manually.
2. **Simple approval.** Present the proposed action clearly and accept `y` or `n`. Keep the consent interaction understandable to someone who does not program.
3. **Real execution.** Connect the assistant to the capabilities needed for supported local tasks, including opening an application and entering text.
4. **Accurate capability awareness.** The assistant's answers and the interface's agent status must reflect what the application can actually execute.
5. **Honest completion.** Report success only after checking the result. Distinguish completed, declined, and failed actions.
6. **Preserve my program identity.** ROMAN is my chosen entry/passcode for the program; the existing interface displays RAWM. Do not rename or replace this experience without discussing it.
7. **Keep the local-assistant objective.** Do not silently introduce a cloud dependency or new paid service as the solution.

“Talk to it” means a conversational interaction here. A voice interface is not an established requirement for this fix.

## Review Qwen Code and existing infrastructure first

I used Qwen Code recently and found it much more fluent. Investigate whether the existing Qwen Code installation, its architecture, or another established agent framework can supply the execution and approval infrastructure this project needs.

Do not assume that using a Qwen model automatically provides Qwen Code's surrounding agent behavior. Inspect what this application actually has: input handling, request routing, model instructions, available tools, execution, approvals, and result feedback.

Prefer reusing suitable existing infrastructure over rebuilding an agent system unnecessarily. Explain the fit and limitations before choosing an approach; Qwen Code's suitability for desktop actions still needs verification.

I mentioned C, C++, and C# because I am unsure why there is such a disconnect. That was not an instruction to rewrite the project. Determine the actual cause before proposing a language change or a large rebuild.

## How I want the next work approached

I was unhappy with the previous token cost relative to the result. Keep the investigation focused and produce a concrete improvement.

1. Inspect the relevant existing project code and installed agent infrastructure.
2. Explain briefly why Agent ON still leads to refusals and command instructions.
3. Recommend the smallest sound approach that delivers the interaction above, including whether Qwen Code can help.
4. Implement and verify the agreed scope without unrelated refactoring or an unnecessary rewrite.
5. Report what changed, what was demonstrated, and any remaining limitation.

## Acceptance criteria

The basic demonstration must work through the normal `roman` entry point:

- I enter `Open Notepad and write hello green world` without a slash command.
- The assistant proposes the action and accepts a plain `y` or `n` response.
- With `y`, Notepad opens and visibly contains `hello green world`.
- With `n`, the proposed action does not execute.
- The assistant does not send me back to `/act`, `/agent`, or another controller.
- The completion message matches the observed result.

**Core request:** Make ROMAN / RAWM a fluent local assistant that gets things done through conversation and simple approval, using established infrastructure where it fits.
