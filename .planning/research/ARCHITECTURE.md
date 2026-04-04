# Architecture Research: Feedship + OpenClaw Scheduled Reports

**Domain:** CLI tool integration with AI agent scheduling framework
**Researched:** 2026-04-04
**Confidence:** MEDIUM (based on CLI help introspection and existing skill documentation; unable to fetch live docs)

## Executive Summary

OpenClaw provides a Gateway-based architecture for scheduling AI agent tasks. The integration pattern for feedship + OpenClaw scheduled daily reports works as follows:

1. **Cron trigger** - `openclaw cron add` creates a scheduled job tied to the Gateway
2. **Agent activation** - Cron fires, activates an agent with the ai-daily skill loaded
3. **CLI execution** - Agent uses feedship CLI commands via exec tool (e.g., `feedship fetch --all`, `feedship article list --since <date> --json`)
4. **Synthesis** - Agent processes the JSON output and generates a digest
5. **Delivery** - `--deliver` flag sends the result to a configured channel (WhatsApp, Telegram, etc.)

The ai-daily skill (v1.1) already defines this pattern in its metadata with `cron.syntax` and `cron.default: "0 8 * * *"`.

## OpenClaw Architecture

### System Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                        OpenClaw Gateway                              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  │
│  │   Cron      │  │   Agent     │  │  Channels   │  │   Skills   │  │
│  │  Scheduler │  │   Runtime   │  │  (WhatsApp, │  │   Registry  │  │
│  │             │  │             │  │  Telegram,  │  │             │  │
│  │  persist    │  │  executes   │  │  Discord)   │  │  YAML defs  │  │
│  │  across     │  │  skills +   │  │             │  │             │  │
│  │  restarts   │  │  tools      │  │  deliver()  │  │  load into  │  │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  │
│         │                │                │                │          │
│         └────────────────┴────────────────┴────────────────┘          │
│                          │                                             │
└──────────────────────────┼─────────────────────────────────────────────┘
                           │
           ┌───────────────┼───────────────┐
           │               │               │
           ▼               ▼               ▼
    ┌──────────┐   ┌──────────┐   ┌──────────┐
    │  Exec    │   │  Browser │   │  Files   │
    │  Tool    │   │  Tool    │   │  Tools   │
    │          │   │          │   │          │
    │ runs     │   │ web      │   │ memory,  │
    │ shell    │   │ browsing │   │ notes    │
    │ commands │   │          │   │          │
    └────┬─────┘   └──────────┘   └──────────┘
         │
         ▼
  ┌─────────────────┐
  │   feedship      │
  │   CLI           │
  │                 │
  │ fetch --all     │
  │ article list    │
  │ search --json   │
  └─────────────────┘
```

### Component Responsibilities

| Component | Responsibility | How It Works |
|-----------|----------------|---------------|
| Gateway | Persistent scheduler + message routing | WebSocket server; persists cron jobs and session state to disk |
| Cron Scheduler | Time-based trigger management | Jobs persist across restarts; stored in `~/.openclaw/` |
| Agent Runtime | Executes agent turns with skills loaded | Loads SKILL.md files; uses exec tool to run CLI commands |
| Channels | Delivery to end users | WhatsApp, Telegram, Discord, etc.; `--deliver` flag routes output |
| Skills | YAML definitions of capabilities | Define `openclaw.metadata.cron` for scheduled activation hints |
| Exec Tool | Shell command execution | Agent runs `feedship fetch --all` and parses stdout |

## Integration Patterns

### Pattern 1: Cron-Triggered Skill Execution (Recommended for Daily Digest)

**What:** A cron job fires at a schedule, activates an agent with skill context, agent runs feedship CLI commands, result is delivered.

**When to use:** Daily/periodic digest generation, proactive monitoring.

**Data flow:**
```
Cron (0 8 * * *)
  → Gateway
  → Agent (with ai-daily skill loaded)
  → Exec: feedship fetch --all
  → Exec: feedship article list --since YYYY-MM-DD --json
  → Exec: feedship search "AI LLM" --semantic --limit 50 --since YYYY-MM-DD --json
  → Agent synthesizes digest
  → deliver --channel whatsapp
```

**Example cron job:**
```bash
openclaw cron add \
  --name "daily-ai-digest" \
  --cron "0 8 * * *" \
  --agent default \
  --message "Generate daily AI digest from feedship subscriptions" \
  --deliver \
  --channel whatsapp \
  --timeout-seconds 300
```

**Trade-offs:**
- Pros: Full AI synthesis, flexible prompt, multi-source aggregation
- Cons: Requires AI provider API key, slower than pure CLI scripting

### Pattern 2: Direct CLI Cron with Output Delivery

**What:** External scheduler (launchd, systemd) runs feedship directly; OpenClaw only handles delivery.

**When to use:** When you want simpler logic that doesn't need AI synthesis.

**Data flow:**
```
External cron (systemd timer)
  → feedship fetch --all
  → feedship article list --since YYYY-MM-DD --json > /tmp/digest.json
  → openclaw message send --channel telegram --file /tmp/digest.json
```

**Trade-offs:**
- Pros: No AI API needed, faster, simpler debugging
- Cons: No intelligent synthesis; just raw output

### Pattern 3: Standing Order (Agent-Based Automation)

**What:** A persistent agent with a "standing order" instruction set that periodically runs skills.

**When to use:** Continuous monitoring with conditional actions.

**Note:** This is more advanced and documented in OpenClaw under `Tier 3: Proactive` - agents that "autonomously execute standing orders without per-action human approval."

## Data Flow for Scheduled Daily Digest

### Full Flow (Pattern 1)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ 6:00 AM (user's timezone via --tz)                                          │
│    │                                                                       │
│    ▼                                                                       │
│ openclaw cron scheduler (Gateway)                                           │
│    │                                                                       │
│    ▼                                                                       │
│ Cron job fires: "daily-ai-digest"                                           │
│    │                                                                       │
│    ▼                                                                       │
│ Agent activated with system prompt + ai-daily skill                        │
│    │                                                                       │
│    ├──► Exec: feedship fetch --all                                         │
│    │         └─► Updates SQLite + ChromaDB                                 │
│    │                                                                       │
│    ├──► Exec: feedship article list --since 2026-04-04 --limit 100 --json   │
│    │         └─► JSON array of today's articles                            │
│    │                                                                       │
│    ├──► Exec: feedship search "AI LLM GPT machine learning" --semantic \    │
│    │         --limit 50 --since 2026-04-04 --json                         │
│    │         └─► JSON array of semantically relevant articles              │
│    │                                                                       │
│    ▼                                                                       │
│ Agent synthesizes 3-section digest                                          │
│    │                                                                       │
│    ▼                                                                       │
│ Gateway delivers to --channel (whatsapp/telegram/discord)                  │
│    │                                                                       │
│    ▼                                                                       │
│ User receives formatted digest in chat                                      │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Key Integration Points

### 1. Skill Metadata for Cron Hints

The ai-daily SKILL.md already defines cron hints:

```yaml
metadata:
  openclaw:
    requires:
      bins:
        - uv
    cron:
      syntax: cron([minute,] [hour,] [day-of-month,] [month,] [day-of-week])
      default: "0 8 * * *"  # Daily at 8:00 AM
      description: "Generate daily AI news digest every day at 8 AM"
```

This allows OpenClaw to suggest the skill for cron-based activation.

### 2. JSON Output for Agent Parsing

feedship commands with `--json` flag output machine-readable JSON:

```bash
feedship article list --since 2026-04-04 --limit 100 --json
# => {"articles": [{"id": "...", "title": "...", "url": "...", ...}], "count": 42}
```

The agent can parse this and extract relevant fields.

### 3. Channel Delivery Configuration

OpenClaw supports multiple delivery channels:

| Channel | Target Format | Example |
|---------|--------------|---------|
| whatsapp | E.164 phone | `--to +15551234567` |
| telegram | Chat ID | `--to @username` or `-1001234567890` |
| discord | Channel ID | `--to #general` |
| last | Last-used | `--channel last` |

## Recommended Project Structure

```
feedship/
├── skills/
│   ├── feedship/SKILL.md          # Already exists
│   └── ai-daily/SKILL.md         # Already exists
└── docs/
    └── scheduled-reports.md       # NEW: User guide for OpenClaw integration
```

**No new source files needed** - the integration is achieved through:
1. Configuration (cron jobs via `openclaw cron add`)
2. Skill metadata (already defined in existing SKILL.md files)
3. User documentation (new docs/scheduled-reports.md)

## Anti-Patterns to Avoid

### Anti-Pattern 1: Running feedship Inside OpenClaw Sandbox

**What:** Trying to run feedship commands inside OpenClaw's sandboxed environment without proper path configuration.

**Why it's wrong:** OpenClaw sandbox isolates processes; feedship needs access to `~/.feedship/` for SQLite and ChromaDB.

**Do this instead:** Use `--tools exec` to run feedship directly on the host, or configure the sandbox to allow access to feedship's data directory.

### Anti-Pattern 2: Mixing Cron Triggers

**What:** Creating both an external (launchd/systemd) cron AND an OpenClaw cron for the same task.

**Why it's wrong:** Double execution wastes resources, may cause rate limiting with feeds.

**Do this instead:** Choose one scheduler: OpenClaw cron for AI-synthesized output, external cron for pure CLI automation.

### Anti-Pattern 3: No Timeout on Long-Running Skills

**What:** Setting `--timeout-seconds` too low for the daily digest.

**Why it's wrong:** `feedship fetch --all` with 50+ feeds can take 5+ minutes.

**Do this instead:** Set `--timeout-seconds 600` (10 minutes) or use `--every` with stagger for large feed counts.

## Scaling Considerations

| Scale | Feed Count | Fetch Time | Recommendation |
|-------|-----------|------------|----------------|
| Personal (1-20 feeds) | 20 | ~30s | OpenClaw cron with default timeout |
| Power user (20-100) | 100 | ~2-5min | Use `--every 30m` stagger, higher timeout |
| Team (100+) | 500+ | 10+ min | Consider pre-fetching via external cron, OpenClaw only for synthesis |

**First bottleneck:** Network I/O on fetch - mitigated by `--concurrency` flag in feedship.

**Second bottleneck:** ChromaDB embedding generation on first fetch - mitigated by batch processing.

## Implementation Recommendation

For v1.7 (scheduled AI daily reports):

1. **No new source files** - the integration is configuration-only
2. **Create user documentation** at `docs/scheduled-reports.md` with:
   - How to set up the OpenClaw cron job
   - Channel configuration examples
   - Troubleshooting tips
3. **Update ai-daily SKILL.md** to clarify the cron job creation command
4. **Test the full flow** before shipping

**Example user workflow:**
```bash
# User sets up daily digest at 8 AM via WhatsApp
openclaw cron add \
  --name "daily-ai-digest" \
  --cron "0 8 * * *" \
  --message "Generate daily AI digest using feedship. Run feedship fetch --all first, then generate a 3-section digest: (A) Today's new articles with summaries, (B) Hot topics clustering, (C) Featured picks by feed weight. Output in Chinese." \
  --deliver \
  --channel whatsapp \
  --timeout-seconds 600
```

## Sources

- OpenClaw CLI help (`openclaw --help`, `openclaw cron --help`, `openclaw agent --help`)
- feedship SKILL.md (v1.5)
- ai-daily SKILL.md (v1.1)
- OpenClaw docs links (unverified due to network restrictions):
  - https://docs.openclaw.ai/automation/cron-jobs
  - https://docs.openclaw.ai/cli/cron
  - https://docs.openclaw.ai/concepts/delegate-architecture#tier-3-proactive

---
*Architecture research for: Feedship + OpenClaw scheduled reporting*
*Researched: 2026-04-04*
