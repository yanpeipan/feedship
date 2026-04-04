# Pitfalls Research: OpenClaw Scheduled Messaging

**Domain:** OpenClaw cron job configuration for external CLI tools
**Researched:** 2026-04-04
**Confidence:** MEDIUM

Research based on auto-updater SKILL.md (clawdbot cron add patterns) and proactive-agent SKILL.md (autonomous vs prompted crons architecture). Web search was unavailable for direct verification, so findings are derived from existing skill documentation and architectural patterns.

## Critical Pitfalls

### Pitfall 1: Using `systemEvent` with `main` Session for Background Tasks

**What goes wrong:**
Cron fires but the task never actually executes. The prompt appears in the main session but sits there ignored while the agent is busy with other work.

**Why it happens:**
Misunderstanding the architecture. `systemEvent` sends a prompt to the main session - but main session only processes when the agent is free and attention is available. Background cron jobs using `systemEvent` + `main` are just notifications, not autonomous execution.

From proactive-agent SKILL.md:
> You create a cron that says "Check if X needs updating" as a `systemEvent`. It fires every 10 minutes. But: Main session is busy with something else. Agent doesn't actually do the check. The prompt just sits there.

**How to avoid:**
Use `isolated` session with `agentTurn` for any task that must execute without requiring main session attention:

```bash
clawdbot cron add \
  --name "Daily AI Digest" \
  --cron "0 8 * * *" \
  --session isolated \
  --deliver \
  --message "AUTONOMOUS: Run feedship fetch --all, generate daily digest, deliver report"
```

**Warning signs:**
- Cron fires but nothing happens
- Main session shows pending prompts that never get addressed
- Task appears to run but output is never delivered

**Phase to address:** Implementation Phase - cron configuration

---

### Pitfall 2: Missing `--deliver` Flag Results in Lost Output

**What goes wrong:**
Cron job runs successfully (exit code 0) but no report appears. Output is generated but not delivered anywhere visible.

**Why it happens:**
Without `--deliver`, the isolated agent executes but has no destination for results. The output exists somewhere in the system but never reaches the user.

**How to avoid:**
Always include `--deliver` when setting up informational cron jobs:

```bash
clawdbot cron add \
  --name "Daily AI Digest" \
  --cron "0 8 * * *" \
  --session isolated \
  --deliver \
  --message "AUTONOMOUS: Run feedship fetch --all, generate daily digest"
```

**Warning signs:**
- Logs show cron fired and completed
- No visible output or report received
- Agent executed but results not visible

**Phase to address:** Implementation Phase - cron configuration

---

### Pitfall 3: Gateway Not Running Breaks All Cron Jobs

**What goes wrong:**
Cron jobs simply never fire. No error messages, no indication anything is wrong - just silence.

**Why it happens:**
OpenClaw cron jobs depend on the gateway process running continuously. If the gateway is stopped, restarted, or crashes, cron jobs do not fire. There is no queue or retry mechanism - missed cron jobs are simply lost.

**How to avoid:**
1. Verify gateway is running before creating cron jobs: `clawdbot gateway status`
2. Set up process monitoring (launchd, systemd) to keep gateway alive
3. Use `--wake now` on cron creation to verify immediate execution works

```bash
# Verify gateway is running
clawdbot gateway status

# Create cron with immediate test
clawdbot cron add \
  --name "Test Cron" \
  --cron "0 8 * * *" \
  --session isolated \
  --wake now \
  --deliver \
  --message "Test message"
```

**Warning signs:**
- `clawdbot cron list` shows jobs but they never fire
- Gateway status shows stopped or restarting
- System reboot causes all cron jobs to stop

**Phase to address:** Infrastructure Phase - gateway reliability

---

### Pitfall 4: Session Isolation Loses Context Between Runs

**What goes wrong:**
Isolated session runs successfully but has no access to previous state. Each cron execution starts fresh with no memory of prior runs, previous reports, or accumulated context.

**Why it happens:**
`--session isolated` creates a fresh sub-agent for each execution. Unlike `main` session which persists context across interactions, isolated sessions have no memory of previous turns. This is by design for autonomous background tasks, but breaks workflows that need continuity.

**How to avoid:**
1. For stateful workflows, write state to persistent storage (files, database)
2. Read prior state at start of each isolated execution
3. Use workspace files (`~/.openclaw/workspace/`) for cross-run persistence

Example pattern for feedship daily digest:
```bash
# In the cron message, include state management
clawdbot cron add \
  --session isolated \
  --message "AUTONOMOUS: Read ~/.feedship/.last-digest-date, fetch articles since that date, generate digest, write new date to ~/.feedship/.last-digest-date"
```

**Warning signs:**
- Report duplicates content from previous runs
- Isolated agent cannot find context it should have
- Each run behaves as if it's the first run ever

**Phase to address:** Design Phase - stateful cron architecture

---

### Pitfall 5: External CLI Tool Missing in Isolated Session Environment

**What goes wrong:**
Cron fires, isolated agent starts, but immediately fails with "command not found". The CLI tool works in normal sessions but is unavailable in isolated agent environment.

**Why it happens:**
Isolated agents may have different PATH or environment than the main session. Tools installed in user's PATH (via pipx, uv tool, etc.) may not be available in the isolated agent's shell environment.

**How to avoid:**
1. Use full paths for CLI tools in cron messages
2. Verify tool availability in isolated environment with diagnostic cron first
3. Document required PATH additions in SKILL.md

```bash
# Test if feedship is available in isolated session
clawdbot cron add \
  --name "Diagnostic Check" \
  --cron "0 8 * * *" \
  --session isolated \
  --deliver \
  --message "Check if feedship is available: which feedship || echo 'NOT FOUND'; feedship --version"
```

**Warning signs:**
- "command not found" in cron output
- Works in interactive session but fails in cron
- Tool installed via pipx/uv tool but isolated session cannot find it

**Phase to address:** Testing Phase - isolated environment verification

---

### Pitfall 6: Dependency Missing (uv, Python, Extras)

**What goes wrong:**
Cron job starts but fails because feedship's dependencies are incomplete. Common: `feedship fetch --all` fails with import error because `cloudflare` or `ml` extras are missing.

**Why it happens:**
Basic `pip install feedship` does not include ML (sentence-transformers, chromadb) or cloudflare (scrapling, playwright) extras. The ai-daily skill requires full functionality.

**How to avoid:**
Ensure feedship is installed with all required extras:

```bash
# Install with all extras
uv tool install 'feedship[ml,cloudflare]' --python 3.12 --force

# Or verify installation
feedship info --json | jq '.extras'
```

**Warning signs:**
- `feedship info --json` shows missing extras
- Semantic search commands fail with import errors
- Fetch commands work but related articles fails

**Phase to address:** Setup Phase - complete installation

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Using `systemEvent` + `main` for cron | Simpler config | Tasks never execute | Never - use isolated |
| Skipping `--deliver` flag | Faster setup | Output lost | Never |
| No gateway monitoring | Simpler ops | Missed cron jobs | Only for non-critical jobs |
| No state persistence in isolated | Simpler cron message | Duplicate reports | Never for recurring tasks |
| Basic feedship install | Less disk space | Missing functionality | Never for production |

---

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| feedship + OpenClaw | Not installing ml/cloudflare extras | `uv tool install 'feedship[ml,cloudflare]'` |
| Isolated session | Assuming PATH persistence | Use full paths or verify in diagnostic cron |
| Cron delivery | Missing `--deliver` | Always include for informational jobs |
| Timezone | Assuming UTC | Use `--tz` flag explicitly |
| Gateway | Not monitoring | Set up launchd/systemd service |

---

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Large embedding model in cron | Long execution times, timeouts | Use smaller model or pre-compute embeddings | At 100+ articles per day |
| Concurrent fetches overwhelming system | High CPU, slow response | Limit `--concurrency` in fetch | At 50+ feeds |
| Daily digest too long | Token limits, incomplete reports | Implement pagination or summary truncation | At 200+ articles per day |

---

## "Looks Done But Isn't" Checklist

- [ ] **Cron fires:** Verify with `clawdbot cron list` and check last execution time
- [ ] **Session type:** Verify `--session isolated` not `main` for background tasks
- [ ] **Delivery:** Verify `--deliver` flag present (unless output is written to file)
- [ ] **Dependencies:** Verify `feedship info --json` shows all required extras
- [ ] **Environment:** Test isolated session can actually run feedship commands
- [ ] **State:** Verify prior run state is accessible if continuity required
- [ ] **Gateway:** Verify `clawdbot gateway status` shows running
- [ ] **Timezone:** Verify cron fires at intended local time, not UTC

---

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Cron never fires (gateway down) | LOW | Restart gateway, verify with `--wake now` |
| Output lost (no --deliver) | LOW | Re-run cron manually with `--wake now`, add --deliver |
| Command not found (PATH) | MEDIUM | Install tool in isolated env, use full paths |
| Duplicate reports (no state) | MEDIUM | Implement state file, re-run with fresh state |
| Partial execution (timeout) | MEDIUM | Reduce scope, implement checkpointing |

---

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| systemEvent + main session | Design: Choose correct session type | Test with `--wake now` |
| Missing --deliver | Implementation: Add flag | Send test cron, verify delivery |
| Gateway downtime | Infrastructure: Set up monitoring | Check `clawdbot gateway status` |
| Session isolation context loss | Design: Implement state persistence | Run twice, verify continuity |
| CLI tool unavailable | Testing: Diagnostic cron first | Run diagnostic before production |
| Missing dependencies | Setup: Complete installation | `feedship info --json` shows extras |

---

## Sources

- Auto-updater SKILL.md: `/Users/y3/clawd/skills/auto-updater/SKILL.md` — cron add command examples with `--session isolated`
- Proactive-agent SKILL.md: `/Users/y3/clawd/skills/proactive-agent/SKILL.md` — "Autonomous vs Prompted Crons" section explaining session architecture
- feedship SKILL.md: `/Users/y3/feedship/skills/feedship/SKILL.md` — installation with extras guidance
- ai-daily SKILL.md: `/Users/y3/feedship/skills/ai-daily/SKILL.md` — cron trigger documentation

---

*Pitfalls research for: OpenClaw scheduled messaging*
*Researched: 2026-04-04*
*Confidence: MEDIUM (based on skill documentation, web search unavailable for direct verification)*
