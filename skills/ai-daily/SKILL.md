---
version: 1.12.0
name: feedship-ai-daily
description: "Generate daily AI news digest from feedship subscriptions. Use when user wants today's news summary, daily briefing, periodic news recap, AI daily digest, ai daily, AI 日报, ai 日报, 生成简报, or 大模型日报. Reads existing feedship subscriptions, fetches latest articles, and generates a 6-section digest: (A) AI五层蛋糕, (B) 精选推荐, (C) 创业信号, (D) 创作点, (E) 政策解读, (F) 媒体热点. Requires feedship skill."
metadata:
  openclaw:
    requires:
      bins:
        - uv
    cron:
      syntax: cron([minute,] [hour,] [day-of-month,] [month,] [day-of-week])
      default: "0 8 * * *"  # Daily at 8:00 AM
      description: "Generate daily AI news digest every day at 8 AM
---

# AI 日报 (Feedship AI Daily)

**Version:** 1.12.0
**For:** OpenClaw compatible agents
**Description:** Generate daily AI news digest from feedship subscriptions

## Setup

Before using this skill, install feedship:

```bash
uv tool install 'feedship[ml,cloudflare]' --python 3.12 --force
```

Verify installation: `feedship --version`

---

## Channel Setup

### Telegram Setup

#### Step 1: Create Your Bot
1. Open Telegram and search for @BotFather
2. Send /newbot command
3. Follow prompts to name your bot and get the bot token
4. Copy the token (format: `123456789:ABCdefGhIJKlmNoPQRsTUVwxyZ`)

#### Step 2: Add Channel to OpenClaw
```bash
openclaw channels add --channel telegram --token <YOUR_BOT_TOKEN>
```

#### Step 3: Get Your Chat ID
1. Start a conversation with your bot by sending any message
2. Send /start to the bot
3. Get your chat ID:
```bash
curl -s https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates | jq .message.chat.id
```
4. Note the numeric chat ID (e.g., `123456789`)

#### Step 4: Verify Channel Configuration
```bash
openclaw channels list
```
Confirm your telegram channel appears in the list.

#### Step 5: Add Cron with Telegram
```bash
openclaw cron add \
  --name "feedship-ai-daily" \
  --agent feedship-ai-daily \
  --cron "0 8 * * *" \
  --session isolated \
  --announce \
  --channel telegram \
  --to <YOUR_CHAT_ID> \
  --timeout-seconds 900 \
  --message "使用 feedship-ai-daily skill 生成今日日报。先读取 ~/clawd/skills/ai-daily/SKILL.md 和 REPORT_FORMAT.md 了解格式要求，然后严格遵循 A-F 六段式格式生成报告。"
```

### 飞书 Setup

#### Step 1: Create Feishu OAuth App
1. Go to https://open.feishu.cn/app
2. Click "Create App" → "Enterprise App"
3. Set app name and configure the following permissions:
   - `im:message` — Send messages
   - `im:message.receive_v1` — Receive messages
4. From app settings, get:
   - App ID (e.g., `cli_abc123def456`)
   - App Secret

#### Step 2: Configure OpenClaw for Feishu
```bash
openclaw configure --section channels
```
Select "feishu" when prompted and enter:
- App ID
- App Secret

#### Step 3: Verify Channel Configuration
```bash
openclaw channels list
```
Confirm your feishu channel appears in the list.

#### Step 4: Get Your Feishu Open ID
After configuring, your Open ID will be used as the `--to` destination.
Use `openclaw channels list` output to identify the correct destination format.

#### Step 5: Add Cron with 飞书
```bash
openclaw cron add \
  --name "feedship-ai-daily" \
  --agent feedship-ai-daily \
  --cron "0 8 * * *" \
  --session isolated \
  --announce \
  --channel feishu \
  --to <YOUR_FEISHU_OPEN_ID> \
  --timeout-seconds 900 \
  --message "使用 feedship-ai-daily skill 生成今日日报。先读取 ~/clawd/skills/ai-daily/SKILL.md 和 REPORT_FORMAT.md 了解格式要求，然后严格遵循 A-F 六段式格式生成报告。"
```

---

## Before You Begin

Before scheduling automated reports, verify the following:

- [ ] **OpenClaw gateway is running**: `openclaw gateway status`
  - Must show: `Runtime: running`
  - If stopped: `openclaw gateway start`
- [ ] **A delivery channel is configured**: `openclaw channels list`
  - Must show at least one channel (e.g., telegram, whatsapp, feishu)
  - If no channel: `openclaw channels add --channel <type>`
- [ ] **feedship is installed with required extras**: `feedship info --json | jq '.extras'`
  - Must include: `ml` and `cloudflare` for full functionality
  - If missing: `uv tool install 'feedship[ml,cloudflare]' --python 3.12 --force`
- [ ] **OpenClaw CLI is available**: `openclaw --version`
  - Must print: `OpenClaw 2026.4.2` or similar

---

## Usage

### On-Demand

User says: "生成今日日报"、"今日新闻摘要"、"daily digest"

Agent activates this skill and runs the Generate Daily Report flow.

### Automatic (Cron)

Schedule daily reports to run automatically at 8:00 AM using OpenClaw cron.

#### Step 1: Verify Your Delivery Channel

List available channels and note your configured channel type and destination:

```bash
openclaw channels list
```

#### Step 2: Add the Cron Job

Run this command with your channel configuration:

```bash
openclaw cron add \
  --name "feedship-ai-daily" \
  --agent feedship-ai-daily \
  --cron "0 8 * * *" \
  --tz Asia/Shanghai \
  --session isolated \
  --announce \
  --channel <your-channel> \
  --to <your-destination> \
  --timeout-seconds 900 \
  --message "使用 feedship-ai-daily skill 生成今日日报。先读取 ~/clawd/skills/ai-daily/SKILL.md 和 REPORT_FORMAT.md 了解格式要求，然后严格遵循 A-F 六段式格式生成报告。"
```

Replace:
- `<your-channel>` with your channel type (e.g., `telegram`, `whatsapp`, `feishu`)
- `<your-destination>` with your delivery target (e.g., `+15555550123` for WhatsApp, `@your_bot` for Telegram)

**Note:** The `--message` flag with skill instructions is required because cron jobs currently route through the main agent, which does not auto-load skill instructions. The message tells the agent to read the skill files before generating the report.

#### Step 3: Verify the Cron Job

```bash
openclaw cron list
```

Confirm the job shows:
- `name: feedship-ai-daily`
- `session: isolated`
- `announce: true`

#### Step 4: Test Immediately (Optional)

To run the job right now instead of waiting:

```bash
openclaw cron run <job-id>
```

Find `<job-id>` from the `openclaw cron list` output.

---

## Generate Daily Report

**Core Principle:** Process ALL available articles systematically. Do not manually select 5-8 articles. Use clustering and batch processing to cover the full corpus.

Execute these steps in order:

### Step 1: Fetch Latest Articles

```bash
# Fetch all subscribed feeds for latest articles
feedship fetch --all
```

Wait for fetch to complete before proceeding.

### Step 2: Get ALL Recent Articles (Not Just Today)

Due to RSS timezone inconsistencies, expand search window to capture maximum articles:

```bash
# Get articles from last 3 days (covers timezone edge cases)
feedship article list --limit 333 --since YYYY-MM-DD --until YYYY-MM-DD
```

Then use semantic search with multiple topic queries to ensure comprehensive coverage:

```bash
# Search 1: Models & Foundation
feedship search "LLM GPT Claude Gemini Gemini architecture training" --semantic --limit 100 --since YYYY-MM-DD

# Search 2: Applications & Products
feedship search "AI应用 产品 创业 投资 startup funding" --semantic --limit 100 --since YYYY-MM-DD

# Search 3: Infrastructure & Tools
feedship search "Agent框架 代码 开发者工具 devtools" --semantic --limit 100 --since YYYY-MM-DD

# Search 4: Policy & Regulation
feedship search "AI政策 监管 合规 法律 regulation compliance" --semantic --limit 100 --since YYYY-MM-DD

# Search 5: Security & Ethics
feedship search "AI安全 伦理 隐私 争议 safety ethics" --semantic --limit 100 --since YYYY-MM-DD
```

**Aggregate ALL search results** — each search should return different relevant articles.

### Step 3: Cluster & Generate Report

Use the combined results from Step 2 to:
1. **Cluster articles by semantic similarity** into topics
2. **Count articles per topic** to determine significance
3. **Generate each section** by mapping clusters to section categories

**Section A (AI五层蛋糕)**: Map clusters to the 5 layers
- AI应用: products, consumer apps
- AI模型: LLMs, foundation models
- AI基础设施: infra, tools, dev frameworks
- 芯片: hardware, chips, GPUs
- 能源: energy, manufacturing

**Section B (精选推荐)**: Top 10-15 articles across ALL clusters, grouped by topic

**Sections C-F**: Extract from relevant search results

---

## Report Format

**IMPORTANT: Every report MUST contain exactly 6 sections (A-F) in order.**

Read the full format specification: `SKILL.md/REPORT_FORMAT.md`

### Quick Reference

| Section | Name | Key Output |
|---------|------|-----------|
| A | AI五层蛋糕 | 5 layers with AI摘要 + sources |
| B | 精选推荐 | Top 5-8 ranked articles with links + hot topics merged |
| C | 创业信号 | Funding, acquisitions, trends |
| D | 创作点 | Content angles and story ideas |
| E | 政策解读 | Policy & regulation developments |
| F | 媒体热点 | Viral discussions and media trends |

---

## Tips

- If no articles found today, say "今日无新文" and suggest checking yesterday
- If feedship not installed, install first: `uv tool install 'feedship[ml,cloudflare]' --python 3.12 --force`
- Use `feedship feed list -v` to see feed weights
- For long articles, read summary via `feedship article view <id>` then select key points
- Diversity matters: don't cluster all picks into same topic
- For diagnostic info, run `feedship info --json` to see version, config, and storage details

---

## Configuration

### Ranking Criteria

By default, articles in Section C are ranked by feed weight (权重).

**Option 1: Rank by feed weight (default)**
Sort by 权重 from highest to lowest. Check weights with:
```bash
feedship feed list -v
```

**Option 2: Rank by views (阅读量)**
Sort by 阅读量 from highest to lowest. Articles with more views indicate higher reader interest.

**Option 3: Semantic relevance**
Use `feedship search` with semantic ranking:
```bash
feedship search "your interest keywords" --semantic --limit 10 --since YYYY-MM-DD
```

### Feed Weight Reference

Weights range from 0.1 to 1.0, with higher weights indicating higher priority sources.

---

## Troubleshooting

### Cron Never Fires

**Symptoms:** `openclaw cron list` shows the job but it never executes.

**Diagnosis:**
```bash
openclaw gateway status
```
Must show: `Runtime: running`

If gateway is stopped:
```bash
openclaw gateway start
```

Also verify the job is not disabled:
```bash
openclaw cron list | grep feedship-ai-daily
```

---

### No Output Delivered

**Symptoms:** Cron runs (exit 0) but no report appears in your channel.

**Diagnosis:**

1. Verify `--announce` flag is present in your cron command (see Step 2 above)

2. Verify channel is configured:
```bash
openclaw channels list
```

3. Verify delivery target is correct:
```bash
openclaw cron list | grep -A5 feedship-ai-daily
```
Check that `--to` value matches your expected destination.

---

### Command Not Found in Isolated Session

**Symptoms:** Cron fires but agent reports "command not found" for `feedship`.

**Diagnosis:** Isolated sessions may have different PATH than your terminal.

**Solution:** Use full path to feedship if needed, or verify feedship is in your PATH:
```bash
which feedship
```

If feedship is installed via `uv tool`, the isolated session should find it automatically. If issues persist, test with a diagnostic cron first:
```bash
openclaw cron add \
  --name "diagnostic" \
  --agent feedship-ai-daily \
  --cron "0 8 * * *" \
  --session isolated \
  --announce \
  --message "Check feedship: feedship --version"
```
