# RAWM Local Agent Vision

## The idea

RAWM should grow from an excellent local chat application into a local AI assistant that can safely take real actions on the computer.

The experience should stay as simple and personal as it is now:

1. Open PowerShell, Command Prompt, Windows Terminal, or another supported terminal.
2. Type `roman`.
3. RAWM opens in the terminal.
4. Speak to it naturally.
5. When a request requires action, RAWM understands the goal, chooses an approved tool, performs the action, and reports what happened.

The user should not need to think about which shell command, script, or automation system is required. RAWM should translate an ordinary request into safe, visible, local computer actions.

## Example experience

```text
C:\Users\ROMAN> roman

RAWM is ready.

You: Open Notepad and type "hi"
roman: Opening Notepad and typing "hi".
roman: Done.
```

Behind that simple conversation, the agent could:

1. Interpret the request.
2. Match it to a known, allowed action.
3. Ask for confirmation if the action is sensitive or destructive.
4. Launch Notepad using a controlled Windows tool.
5. Wait until the Notepad window is ready.
6. enter `hi` through an approved UI automation method.
7. Verify that the action succeeded.
8. Tell the user the result.

## Core goal

Build a deterministic, local agent into the existing RAWM application without losing what already makes RAWM great.

The finished system should combine:

- the existing `roman` launch command and RAWM terminal interface;
- local language-model inference;
- open routing between locally available models;
- a deterministic agent controller;
- a controlled set of local tools;
- Windows command and application automation;
- clear permission and confirmation rules;
- verification after actions;
- local storage, configuration, logs, and memory;
- an offline-first design with no API key required for normal local use.

## What "deterministic agent" means here

The language model may help understand the user's intent, A deterministic controller should decide what is actually allowed to run.

The controller should use explicit rules and structured actions:

```text
User request
    -> local model interprets intent
    -> model proposes a structured action plan
    -> deterministic policy validates the plan
    -> RAWM requests confirmation when required
    -> a limited tool executes the approved action
    -> RAWM verifies the result
    -> RAWM reports success, failure, or uncertainty
```

Whenever possible, the same approved request and the same computer state should produce the same tool choice, permission decision, and execution path. The model can reason creatively, while the controller remains predictable.

## Local-first requirements

- Conversations and ordinary inference remain on the local computer.
- Agent decisions, tool calls, audit logs, and configuration are stored locally.
- RAWM can function without a cloud account or hosted API.
- Network access is off by default or clearly disclosed when a task needs it.
- Any optional cloud model or service is an explicit user choice, not a hidden dependency.
- Existing RAWM chat behavior remains available even if agent features are disabled.

## Open routing

RAWM should not be permanently tied to one model or one agent framework. It should be able to route work to the best locally installed model for the job while presenting one consistent RAWM experience.

Possible responsibilities include:

- a conversational model for natural dialogue;
- a coding or tool-use model, such as a compatible Qwen model, for structured action planning;
- a small, fast model for intent classification and routing;
- deterministic application code for permission checks and execution.

Models should be replaceable through configuration. RAWM—not Qwen Code, Ollama, or any other individual dependency—remains the product and the main user interface.

## Agent capabilities

The initial agent should focus on small, dependable actions:

- open an approved Windows application;
- type text into the active, verified application;
- create, read, rename, or organize files inside approved locations;
- run approved PowerShell or command-line operations;
- inspect the result of a command;
- perform a short sequence of steps;
- stop and explain when the state is uncertain;
- ask for permission before sensitive actions.

Later versions could add:

- richer application control;
- browser automation;
- multi-step workflows;
- reusable personal routines;
- specialized local agents for coding, research, files, or system maintenance;
- optional integrations with outside services.

## Safety model

The agent should be useful without becoming reckless.

### Action levels

1. **Read-only:** inspect files, applications, system state, or command output.
2. **Low risk:** open an app, type unsent text, or create a new file in an approved workspace.
3. **Confirmation required:** overwrite files, install software, change system settings, send messages, submit forms, or access the network.
4. **Blocked by default:** destructive bulk deletion, credential extraction, disabling security controls, or commands outside defined safety policy.

### Required safeguards

- Tools are allowlisted and narrowly scoped.
- Commands use structured arguments instead of arbitrary generated shell text whenever possible.
- RAWM shows what it intends to do before higher-risk actions.
- The user can cancel an operation.
- The agent verifies the target window, file, or process before acting.
- Destructive or externally consequential actions require explicit confirmation.
- Every tool invocation records its purpose, inputs, outcome, and timestamp in a local audit log.
- Secrets and credentials are never placed into model prompts or ordinary logs.
- A chat-only mode and an agent-enabled mode are both available.

## Relationship to Qwen Code and Ollama

The attempted command was:

```text
ollama launch qwen
```

The installation reached a step where it tried to download and silently install Node.js 20, but the process was interrupted before completion. That failure does not invalidate the RAWM agent idea, and installing Qwen Code should not be treated as the entire architecture.

Qwen Code may eventually be useful as:

- a reference implementation;
- an optional coding-agent backend;
- a source of tool-use patterns;
- one replaceable component behind RAWM.

Before adopting it, the project should determine exactly which Qwen package was being installed, why it requires Node.js, how it integrates with Ollama, whether it can operate fully locally, and whether embedding it is better than implementing a small RAWM-native agent controller.

## Proposed RAWM architecture

```text
roman command
    -> existing RAWM terminal application
        -> conversation and local memory
        -> model router
            -> selected local model
        -> agent controller
            -> structured plan
            -> deterministic policy engine
            -> approval gate
            -> local tool registry
                -> Windows app launcher
                -> keyboard/UI automation
                -> filesystem tools
                -> PowerShell tools
            -> result verifier
            -> local audit log
```

The agent controller should be part of RAWM's application flow, not a separate terminal experience that replaces RAWM.

## First proof of concept

The first milestone should demonstrate one complete, safe loop:

```text
You: Open Notepad and type "hi"
```

To count as successful, RAWM must:

- launch from the existing `roman` command;
- recognize the request as an agent task;
- produce a structured plan rather than uncontrolled prose commands;
- open Notepad through an allowlisted tool;
- confirm that the intended window is active;
- type `hi` without automatically saving or sending anything;
- verify the observable result as far as the tool allows;
- report what it did;
- record the action locally;
- work without a cloud API.

## Development phases

### Phase 1: Understand the existing application

- Document RAWM's current startup, runtime, model, routing, chat, and storage architecture.
- Preserve the existing `roman` command and chat experience.
- Identify the cleanest extension points for tools and agent state.

### Phase 2: Choose the agent foundation

- Investigate the failed Qwen Code installation.
- Compare a RAWM-native controller with Qwen Code and other compatible local-agent options.
- Select components based on local operation, Windows support, determinism, maintainability, and integration quality.

### Phase 3: Build the controlled agent loop

- Define a small structured action schema.
- Add model-to-action planning.
- Add deterministic validation and permission policies.
- Create a local tool registry and audit log.
- Add clear failure and cancellation behavior.

### Phase 4: Implement the Notepad proof of concept

- Add an allowlisted application-launch tool.
- Add verified text-entry automation.
- Run the full request-plan-approve-act-verify-report loop.
- Test from PowerShell, Command Prompt, and Windows Terminal where supported.

### Phase 5: Expand carefully

- Add one capability at a time.
- Give every capability explicit permissions, tests, and rollback behavior.
- Preserve chat-only operation and the ability to disable individual tools.

## Success criteria

The project is successful when:

- typing `roman` still opens the RAWM experience the user already loves;
- RAWM can chat or take action based on the request;
- ordinary operation is local and offline-first;
- the model can be changed without rebuilding the entire application;
- tool execution is governed by deterministic code and explicit permissions;
- the user can understand, approve, cancel, and audit actions;
- the Notepad demonstration works reliably;
- failures are safe, visible, and recoverable;
- agent features enhance RAWM instead of replacing its identity.

## Guiding statement

> RAWM should be the personal local interface. Models provide intelligence, deterministic code provides control, and narrowly scoped tools provide action.

The ultimate vision is one command—`roman`—that opens a private, local, model-flexible assistant capable of both conversation and trustworthy computer action.

