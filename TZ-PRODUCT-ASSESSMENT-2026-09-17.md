# TZ — Product & Commercial Assessment

Written 2026-09-17. Read-only analysis of the repository at this date (commit `a38469c`, 5 commits, 54 tests green, ~1,800 lines of Python). Nothing in the application was modified to produce this document.

---

## 1. The short answer

| Question | Answer |
|---|---|
| Is it proprietary? | **Not in practice.** The source is on a public GitHub repo with no LICENSE file. You own the copyright, but anyone can read, fork and learn from it. |
| Can I take ownership of it? | **Yes.** The ~1,800 lines of Python and the docs are yours. The name, brand, and "trust posture" are yours to register. The dependencies are permissively licensed except Gemma (see §4). |
| Am I ready to sell it? | **No — it's a strong prototype, not a product.** It is at the *late hobbyist / early pre-product* stage. It is a well-engineered local agent, but nothing about it is currently something a stranger would pay for that they can't get free from Ollama, OpenCode, Open WebUI, or Claude Code. |
| Could it become sellable? | **Yes, with a specific positioning** (§7). The code is not the asset. The asset would be the packaged experience + the trust guarantees + the Rawmware brand. |
| Web-hosted on Vercel with models "built in"? | **Possible, but it changes the product completely** — see §5. Vercel cannot run your models; the models would run either in the visitor's browser (WebGPU) or on a GPU server you pay for. |

---

## 2. What TZ actually is (technical inventory)

### Architecture

```
tz.py ──► app/tz_agent.py     Agent class: 8 tools, bounded 8-round tool loop, Ollama streaming
          ├── tz_terminal.py  Rich + prompt_toolkit UI, CPU/RAM/GPU/VRAM telemetry
          ├── tz_team.py      /team: 2–4 bounded subagents with receipts (data/tz/teams/)
          ├── tz_opencode.py  Shells out to `opencode` CLI for coding tasks
          ├── tz_preview.py   Loopback HTTP server, live-reload HTML previews
          └── tz_install.py   Alias/shortcut registration, model setup
```

- **Inference:** Ollama only, loopback only (`127.0.0.1`), cloud model names explicitly rejected, redirects disabled. No API keys anywhere.
- **Tools:** `file_read` (text/PDF), `file_write` (verified by byte comparison + SHA-256, backup on overwrite, exclusive-create), `list_files`, `fetch_url` (2 MB cap, HTML → text), `web_search` (Bing RSS scrape / GitHub API), `run_command` (argv array, no shell, 60 s, confirm), `open_target`, `system_info`.
- **Safety model:** deterministic tools before inference; writes bounded to the workspace; destructive actions confirmed; audit log (`events.jsonl`); session persistence as JSON.
- **Routing:** deterministic heuristic (short greeting → small model, otherwise task model). Not an AI classifier.
- **Dependencies:** `rich`, `prompt_toolkit`, `psutil`, `pypdf` — all permissive. Runtime deps: Ollama, OpenCode (npm), Python 3.10+, Node.
- **CI:** GitHub Actions matrix on Windows/Linux/macOS running unittest.
- **Legacy:** ~33 KB PowerShell runtime (`Start-RAWM.ps1`, `app/RAWM*.ps1`) still in-tree.

### What's genuinely good

1. **The trust posture is unusually disciplined.** "Never invent success", byte-verified writes, receipts for subagents, incomplete output never labeled verified, explicit "cloud models are disabled". Most hobby agents don't do this. This is the most product-like thing in the repo.
2. **Small, readable, dependency-light.** 1,800 lines with stdlib HTTP. Easy to audit — which matters for a privacy-focused product.
3. **Cross-platform CI already green.** Rare for a 5-commit project.
4. **Subagent design is bounded on purpose** (round limits, one inference slot by default, read-only by default). That's the correct instinct.
5. **Doc discipline.** Handoff and build notes are detailed and honest about limits.

### What's missing for a product (technical)

| Gap | Why it blocks sale |
|---|---|
| No installer | Users must install Python, Node, Git, Ollama, then run three commands. That is a >90% drop-off for non-developers. |
| Depends on two third-party runtimes you don't control (Ollama, OpenCode) | Their breaking changes become your support tickets. `tz_opencode.py` already notes OpenCode's stream doesn't report the served model. |
| No GUI | Terminal-only limits the audience to developers, who already have Claude Code / Codex / OpenCode for free or cheap. |
| No update mechanism | `git pull` is not an update mechanism for customers. |
| No telemetry / crash reporting (opt-in) | You can't support what you can't see. |
| `web_search` scrapes Bing RSS | No SLA, no license; will break or get blocked. Not sellable as-is. |
| Model quality ceiling | Qwen3 4B on consumer hardware is fine for demos; it will fail real tasks often enough that paying users churn. The best local models (26B+) need hardware most buyers don't have. |
| `run_command` executes on the user's machine | Fine for a personal tool; for a sold product this needs sandboxing or very clear liability language. |
| Legacy PowerShell runtime still shipped | Two runtimes in one repo = confusion and double maintenance. |
| Working-tree clutter | `hello.md`, `note.md`, `agent-smoke.html`, `.tmp/`, `rom.ps1.backup-*` sitting in the root. Fine for you; bad for a first impression on a public repo. |

---

## 3. Stage assessment: where TZ sits

```
Idea ──► Hobby script ──► Prototype ──► Alpha ──► Beta ──► Product
                              ▲
                              │ TZ is here (solid prototype, ~2 weeks of git history)
```

Honest scoring (1–5):

| Dimension | Score | Note |
|---|---|---|
| Code quality | 4 | Clean, tested, small. |
| Feature completeness vs. free alternatives | 2 | Ollama + Open WebUI + OpenCode cover everything TZ does, with GUIs. |
| Differentiation | 2 | The *posture* is differentiated; the *capability* is not. |
| Installability by a non-developer | 1 | Four prerequisites and a terminal. |
| Brand / identity | 3 | Rawmware has a real aesthetic (the codex/experiments folder). TZ itself has none yet. |
| Legal readiness | 1 | Public repo, no license, Bing scraping, Gemma terms unaddressed. |
| Business readiness | 0 | No pricing, no entity, no payment, no support channel, no ToS/privacy policy. |

**Verdict: hobbyist-to-prototype.** Not an insult — most products start exactly here. But you cannot charge money for it this month.

---

## 4. Ownership, IP and licensing

### What you own
- **Copyright** in the code and docs is yours automatically (US law; no registration required to own it, registration required to sue for statutory damages).
- **The name** "TZ" is too short/generic to trademark meaningfully. "Rawmware" is distinctive and worth a USPTO search + application (~$350/class) if you get serious.

### What you don't own / must respect
| Component | License | Implication |
|---|---|---|
| Ollama | MIT | Free to bundle/redistribute with attribution. |
| OpenCode (`opencode-ai`) | MIT | Same. |
| Qwen3 models | Apache 2.0 | Free for commercial use, attribution required. **Safe to build a business on.** |
| Gemma 3 / Gemma 4 | Gemma Terms of Use | Commercial use allowed but with use restrictions and a prohibited-use policy you must pass through to users. Your `config/settings.json` defaults `pi`/`qwen` workers to `gemma4:26b`. **Prefer Qwen/Llama-class Apache/MIT models for anything you sell.** |
| rich / prompt_toolkit / psutil / pypdf | MIT / BSD | Fine. |
| Bing search via RSS | **No license** — it's scraping | Microsoft's ToS prohibit automated access. Replace with a licensed API (Brave Search API has a free tier and paid plans; SerpAPI; Tavily) before selling. |
| GitHub search API | Free, rate-limited (10 req/min unauthenticated) | OK for discovery; will throttle under load. |

### The public-repo problem
`https://github.com/rawmware/TZ.0002` answers HTTP 200 to unauthenticated requests → public. With no LICENSE file, the legal default is "all rights reserved", **but** GitHub's Terms of Service grant every user the right to view and fork public repos. You cannot un-see code. Practically:

- Anyone could already have cloned it. There is no way to retract that.
- The code is not the moat anyway (see §7), so this is not fatal — but decide now.

**Options:**
1. **Make the repo private today** (Settings → Danger Zone → Change visibility). Keeps future work closed. Costs nothing.
2. **Keep it public and add an explicit license.** Either:
   - A source-available license (e.g. PolyForm Noncommercial, or Business Source License) — "look but don't compete", or
   - A permissive/copyleft OSS license (MIT / AGPL) and sell *services, hosting, or a packaged edition* rather than the code. AGPL specifically discourages competitors from hosting it as a service without open-sourcing their changes.
3. **Do nothing** — the worst option; ambiguous for you and for anyone who wants to use it.

Recommendation: **private now**, decide the license when you know the business model. Reversing "private → public" is easy; "public → private" doesn't erase history.

---

## 5. The web-hosted version: Vercel + DNS + "models built into the site"

### What Vercel can and cannot do

Vercel hosts static sites, Next.js, and serverless/edge functions. Its functions are **CPU-only, short-lived (10 s hobby / 60–300 s pro / up to 800 s with fluid compute), and memory-capped (~1–3 GB)**. **You cannot run Ollama or a 4B-parameter model inside a Vercel function.** So "hosted on Vercel with models built in" resolves to one of three real architectures:

#### Option A — In-browser inference (WebGPU / WebLLM / transformers.js)
The model weights are downloaded *to the visitor's browser* and run on *their* GPU via WebGPU.

- **What it looks like:** `tz.rawmware.com` loads; first visit downloads ~1–2.5 GB of weights (cached in the browser afterwards); chat runs locally at 10–40 tokens/s on a decent laptop, much slower on phones.
- **Pros:** Zero inference cost to you. Keeps your "no cloud, no keys, your data never leaves your machine" promise intact — this is the *only* web architecture that preserves TZ's identity. Vercel bill stays near $0–20/month (static + CDN egress for the weights — put weights on Cloudflare R2 or Hugging Face CDN, not Vercel, or the egress bill will hurt).
- **Cons:** Requires WebGPU (Chrome/Edge yes; Safari 18+ yes; Firefox partial). Model quality is capped at what fits in browser memory (~1–4B params in practice). The 2 GB first-load is a hard UX wall for casual visitors. File-system access from a browser is restricted to what the user explicitly grants via the File System Access API; `run_command` is impossible. The `/team` feature would be single-slot and slow.
- **Effort:** Real rewrite. The Python agent loop → TypeScript. The tool set shrinks to read/write within a granted folder, fetch (CORS-limited — you'll need a proxy function on Vercel for `fetch_url`), and nothing else.
- **Verdict:** Technically credible as a *demo/showcase* that embodies the Rawmware aesthetic. As a paid product, hard — people don't pay for something that runs on their own hardware in a browser tab unless it's dramatically better UX than free alternatives.

#### Option B — Hosted inference on GPU servers you rent
Vercel serves the UI; API calls go to a GPU backend (Modal, RunPod, Fly.io GPU, Lambda, or a bare box with Ollama/vLLM).

- **What it looks like:** A normal SaaS chat/agent app. Users sign up, you meter their tokens, models are "built in" from the user's point of view because they run on your servers.
- **Pros:** Works on any device, no download, you can run 26B+ models that actually complete tasks. This is what a customer means when they say "I don't want to download anything."
- **Cons:** **It is the opposite of TZ's stated product promise** ("No mandatory cloud dependency", "no paid inference", "loopback only"). You would be building a competitor to Claude/ChatGPT/Perplexity with a 4B–26B model and no funding. You also inherit content-moderation, abuse, uptime, and data-privacy obligations. Multi-tenant file tools become a security project (sandboxed per-user workspaces, no `run_command`).
- **Cost (approximate, verify current pricing):**
  - Serverless GPU (Modal/RunPod): A10G/L4 class ≈ $0.60–1.20 per GPU-hour, billed per second, scale to zero. An idle product costs ~$0; a busy one at 100 concurrent users on 4B models needs ~2–4 GPUs ≈ $1,500–3,500/month.
  - Dedicated box: one RTX 4090/L40S ≈ $400–900/month rented; serves maybe 20–50 concurrent 4B sessions with vLLM.
  - Or skip hosting entirely and pay per token to an open-model API (Together, Groq, Fireworks, DeepInfra): Qwen/Llama 7–8B class ≈ $0.05–0.20 per million tokens. At 50k tokens/user/day that's roughly $0.10–0.30/user/month — cheap, but then you're a thin wrapper on someone else's API.
  - Vercel itself: Hobby free (non-commercial only — **Hobby plan forbids commercial use**); Pro $20/seat/month + usage.
  - Domain: $10–15/yr; DNS free via Vercel or Cloudflare.
  - Auth (Clerk/Auth0/Supabase): free → $25+/month. Payments: Stripe 2.9% + 30¢.
- **Verdict:** Financially feasible, strategically weak. You'd be selling a small-model chat SaaS in the most crowded market on earth.

#### Option C — Hybrid: web UI, local engine (the "Ollama as backend" model)
Vercel serves a PWA at `tz.rawmware.com`; the page talks to `http://127.0.0.1:11434` on the visitor's own machine (Ollama allows this with `OLLAMA_ORIGINS` set). Or a small local companion daemon (your Python agent, packaged as a single exe) exposes the tools.

- **What it looks like:** "Open the website, it finds your local TZ/Ollama, everything runs on your PC, the site is just the face." Same pattern as Open WebUI, LM Studio's server mode, and Jan.
- **Pros:** Preserves your promise. Hosting cost ≈ $0. Keeps `run_command`, file tools, `/team`, previews — your actual differentiators — because the Python agent still runs locally.
- **Cons:** Mixed content: an `https://` page can't call plain `http://127.0.0.1` without workarounds (Chrome allows loopback as "potentially trustworthy" — it actually works in Chromium; Safari/Firefox are stricter). Still requires the user to install *something* (a single exe/installer — much better than four prerequisites, but not "nothing").
- **Verdict:** **This is the version that fits TZ.** It gives you a shareable URL, a brand surface, a place to put a "Download" button, and doesn't betray the local-only design.

### DNS / hosting mechanics (any option)
1. Buy `rawmware.com` / `tizi.host` (the docs already mention `tizi.host`) at Cloudflare or Porkbun.
2. Point nameservers at Cloudflare (free tier: DNS, CDN, DDoS, R2 for weights).
3. Vercel project → add custom domain → add the CNAME/A records it tells you. ~10 minutes.
4. Put anything >100 MB (model weights, videos) on R2 / Hugging Face, never on Vercel.

---

## 6. Financial reality check

### Cost to keep building (solo)
- Your time is the only material cost. Domain + Vercel Pro + Cloudflare ≈ **$25–40/month** for Option A/C. Option B adds $0 (idle) to thousands (busy).
- Code signing certificate for a Windows installer (so SmartScreen doesn't scare users): **$200–400/yr** (OV) — or use Azure Trusted Signing (~$10/month). Without it, every download shows "Windows protected your PC". This is a non-negotiable product cost.
- Apple notarization if you ever ship macOS: $99/yr developer account.

### Revenue models that could work for a local-first agent
| Model | Precedent | Fit for TZ |
|---|---|---|
| One-time purchase of a packaged desktop app ($20–60) | Sublime Text, Typora, older LM Studio plans | **Best fit.** Matches "no subscription, no cloud" ethos. Ceiling is low but honest. |
| Free core + paid "Pro" features (installer, GUI, team mode, priority support) | Obsidian (free + Sync/Publish), Jan | Good; requires free tier to earn trust first. |
| Sponsorware / GitHub Sponsors / "pay what you want" | Many indie devs | Realistic *first* revenue; validates demand before you build billing. |
| Hosted SaaS subscription ($10–20/month) | Open WebUI cloud, Perplexity | Contradicts your promise; expensive; crowded. Avoid unless you pivot. |
| Consulting: "I'll set up a private local agent for your small business" | Common for local-LLM builders | Immediate money, uses TZ as the deliverable. Not scalable, but it's *real* revenue and *real* user feedback. |

### What would a realistic first year look like?
Without marketing, a packaged local agent from an unknown solo dev typically sells **tens to low hundreds of copies**. At $29, 200 sales = $5,800 gross. That is hobby income, not a salary — *but* it's the only way to find out whether anyone wants the thing. The Rawmware aesthetic (retro OS windows, the Lain nods) is your best shot at standing out, because the technical capability alone won't.

---

## 7. What would actually make this sellable

The competition (all free or near-free): Ollama, LM Studio, Jan, Open WebUI, AnythingLLM, GPT4All, Msty, OpenCode, Aider, Claude Code, Codex CLI. **You cannot win on "it runs local models and has tools."**

You could win on **one** of these:

1. **The trust story, made visible.** TZ already does verified writes, receipts, audit logs, "never claims success". Turn that into UI: a receipt panel, a "what did the agent actually touch" diff, a signed session log. Sell it as *the agent for people who don't trust agents*. No competitor markets this.
2. **Rawmware as an identity.** A retro-OS-styled local agent with personality (passcode/name, the window chrome from your codex folder) is a *vibe product*. Vibe products sell to fans, not to enterprises — which is fine at your scale.
3. **A specific job.** "Local agent that reads your PDFs and writes summaries into your folder, offline, for lawyers/students/researchers." A narrow use case beats a general agent every time for a solo seller.

Non-negotiable steps regardless of which you pick (in order):

1. **Repo → private, or add a license.** (10 minutes)
2. **Delete/archive the PowerShell runtime and root clutter.** One runtime.
3. **Replace Bing scraping** with Brave Search API (free tier: 2,000 queries/month).
4. **Single-file installer** — PyInstaller/Nuitka + Inno Setup on Windows, signed. Bundle Ollama's binary (MIT) or detect an existing install. First-run downloads one Apache-licensed model with a progress bar. Your `01-TZ-FUTURE-ARCHITECTURE.md` already describes this correctly — build it.
5. **A GUI** — either the Option-C web UI over the local daemon, or a minimal Tauri/Electron/PyWebview shell. Terminal-only caps you at developers.
6. **Ten strangers use it.** Not friends. Watch them fail the install. Fix that. Repeat.
7. **Landing page on Vercel** (`tizi.host` or `tz.rawmware.com`): what it is, one 60-second video, a download button, a "pay what you want" or $29 button via Stripe Payment Links / Lemon Squeezy (handles VAT/sales tax for you — recommended over raw Stripe for a solo seller).
8. **Business basics** — an LLC is optional at first (sole proprietorship is fine for a few hundred dollars), but you need a Terms of Use + Privacy Policy (a generator is fine) and a support email.

Estimated effort to reach "someone can pay $29 and successfully install it": **6–12 weeks of focused solo work**, most of it on packaging and GUI, not on the agent.

---

## 8. Bottom line

- **Proprietary?** Only nominally. It's public and unlicensed. Fix that this week.
- **Ownable?** Fully. Dependencies are clean except Gemma (swap it) and Bing scraping (replace it).
- **Sellable today?** No. It's a good prototype with a real point of view and no packaging, GUI, or distribution.
- **Vercel-hosted with built-in models?** Choose Option C (web face + local engine) to stay true to the product; Option A (in-browser WebGPU) for a zero-cost showcase; avoid Option B (hosted GPU SaaS) unless you're consciously pivoting to a different, much harder business.
- **Stage:** late hobbyist / pre-alpha product. The gap to "sellable" is packaging and audience, not code quality. That is the *good* kind of gap — it's work, not a rethink.

*Prices quoted are approximate as of September 2026 — verify current Vercel, Modal, Brave, and code-signing pricing before budgeting.*
