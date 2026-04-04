# Stack Research: OpenClaw Scheduled AI Daily Reports

**Domain:** CLI tool with OpenClaw integration for scheduled AI report delivery
**Researched:** 2026-04-04
**Confidence:** HIGH (verified via OpenClaw CLI v2026.4.2)

## Recommended Stack

### Core Integration Layer

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| **openclaw** | 2026.4.2 | Agent runtime, cron scheduler, channel management | Native CLI for scheduling and delivery; no additional libraries needed |
| **openclaw CLI** | (bundled) | `cron add`, `agent --deliver`, `channels` subcommands | Already installed; provides full scheduling pipeline |

### No New Python Dependencies Required

The feedship project already has all necessary dependencies:
- `scrapling` for HTTP fetching
- `feedparser` for RSS parsing
- `chromadb` + `sentence-transformers` for semantic search
- Existing `feedship` CLI for article retrieval

OpenClaw integration is entirely CLI-based (shell commands), not Python imports.

---

## OpenClaw Commands Reference

### `openclaw cron add` — Schedule Daily Reports

```bash
openclaw cron add [options]
```

**Key options for daily AI report:**

| Option | Purpose | Example |
|--------|---------|---------|
| `--cron <expr>` | Cron expression (5 or 6 fields) | `--cron "0 8 * * *"` (daily 8 AM) |
| `--agent <id>` | Agent ID to invoke | `--agent feedship-ai-daily` |
| `--message <text>` | Message payload for agent | `--message "Generate daily digest"` |
| `--session <mode>` | Session mode: `main` or `isolated` | `--session isolated` |
| `--channel <ch>` | Delivery channel | `--channel whatsapp` |
| `--to <dest>` | Delivery destination | `--to +15555550123` |
| `--announce` | Announce summary to chat (replaces deprecated `--deliver`) | `--announce` |
| `--name <name>` | Job name for identification | `--name "daily-ai-report"` |
| `--description <text>` | Job description | `--description "Daily AI news digest"` |
| `--tz <iana>` | Timezone (IANA) | `--tz Asia/Shanghai` |
| `--timeout-seconds <n>` | Agent timeout | `--timeout-seconds 600` |
| `--thinking <level>` | Thinking level | `--thinking medium` |

**Example command:**
```bash
openclaw cron add \
  --name "feedship-ai-daily" \
  --description "Daily AI news digest from feedship subscriptions" \
  --agent feedship-ai-daily \
  --cron "0 8 * * *" \
  --tz Asia/Shanghai \
  --session isolated \
  --channel whatsapp \
  --to +15555550123 \
  --announce \
  --timeout-seconds 600 \
  --thinking medium
```

### `openclaw agent --deliver` — On-Demand Report Generation

```bash
openclaw agent --message "Generate daily digest" --deliver [options]
```

**Key options:**

| Option | Purpose | Example |
|--------|---------|---------|
| `--message <text>` | Message to agent | `--message "Generate daily digest"` |
| `--deliver` | Send reply to channel | `--deliver` |
| `--channel <ch>` | Delivery channel | `--channel telegram` |
| `--reply-to <target>` | Override delivery target | `--reply-to "#reports"` |
| `--session-id <id>` | Use specific session | `--session-id abc123` |
| `--agent <id>` | Use specific agent | `--agent feedship-ai-daily` |
| `--thinking <level>` | Thinking level | `--thinking medium` |

**Example command:**
```bash
openclaw agent \
  --agent feedship-ai-daily \
  --message "Generate daily digest" \
  --deliver \
  --channel whatsapp \
  --to +15555550123
```

---

## Session Modes: Main vs Isolated

| Mode | Behavior | Use Case |
|------|----------|----------|
| **main** | Shares main conversation context | Interactive chat with context history |
| **isolated** | Fresh session, no prior context | Scheduled jobs; clean slate each run |

**Recommendation:** Use `--session isolated` for cron jobs to avoid polluting main session context.

---

## Channel Configuration

### Supported Channels

| Channel | Setup Required | Command |
|---------|-----------------|---------|
| **whatsapp** | QR code login | `openclaw channels login --channel whatsapp` |
| **telegram** | Bot token | `openclaw channels add --channel telegram --token <TOKEN>` |
| **discord** | Bot token + guild | `openclaw channels add --channel discord --token <TOKEN>` |
| **feishu** | OAuth app config | `openclaw configure --section channels` |
| **slack** | Bot token + workspace | `openclaw channels add --channel slack --token <TOKEN>` |
| **imessage** | Built-in (macOS) | Automatic |

### List Channels

```bash
openclaw channels list
```

### Add Channel (non-interactive example)

```bash
openclaw channels add --channel telegram --token <BOT_TOKEN>
```

---

## Cron Management Commands

| Command | Purpose |
|---------|---------|
| `openclaw cron list` | List all cron jobs |
| `openclaw cron status` | Show scheduler status |
| `openclaw cron run <id>` | Run job immediately (debug) |
| `openclaw cron runs <id>` | Show run history |
| `openclaw cron edit <id>` | Modify job fields |
| `openclaw cron enable/disable <id>` | Toggle job |
| `openclaw cron rm <id>` | Remove job |

---

## What NOT to Add

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| **Python OpenClaw SDK** | OpenClaw is CLI-first | Shell commands via `subprocess` or `click.run()` |
| **Additional cron libraries** | OpenClaw handles scheduling | `openclaw cron add` |
| **Message queue systems** | OpenClaw gateway handles delivery | `openclaw agent --deliver` |
| **APScheduler, celery, etc.** | Overengineering | OpenClaw cron scheduler |

---

## Skill Metadata Update (ai-daily)

The existing `skills/ai-daily/SKILL.md` defines cron in metadata:

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

**v1.7 Update needed:** Add documentation for:
- `--session isolated` flag for cron jobs
- `--announce` for automatic delivery
- `--channel` and `--to` for delivery target

---

## Integration Architecture

```
feedship (Python CLI)
       │
       │ (existing: article list, search, fetch)
       ▼
OpenClaw Gateway (WebSocket)
       │
       ├── cron scheduler ──► agent ──► feedship commands ──► ai-daily report
       │
       └── channels ──► delivery (WhatsApp/Telegram/etc)
```

**No code changes to feedship needed.** OpenClaw integration is entirely CLI-based.

---

## Example: Complete Setup Flow

```bash
# 1. Verify OpenClaw is installed
openclaw --version

# 2. Configure delivery channel (e.g., WhatsApp)
openclaw channels login --channel whatsapp

# 3. Add cron job for daily AI digest
openclaw cron add \
  --name "feedship-ai-daily" \
  --agent feedship-ai-daily \
  --cron "0 8 * * *" \
  --tz Asia/Shanghai \
  --session isolated \
  --announce \
  --channel whatsapp \
  --to +15555550123

# 4. List cron jobs to verify
openclaw cron list

# 5. Test on-demand delivery
openclaw agent --agent feedship-ai-daily --message "Generate daily digest" --deliver
```

---

## Sources

- OpenClaw CLI v2026.4.2 (verified via `openclaw --help`, `openclaw cron add --help`, `openclaw agent --help`)
- https://docs.openclaw.ai/cli

---
*Stack research for: OpenClaw scheduled AI daily report delivery*
*Researched: 2026-04-04*
