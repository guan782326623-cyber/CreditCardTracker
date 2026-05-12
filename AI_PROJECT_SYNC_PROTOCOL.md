# AI Project Sync Protocol

## Purpose

This file defines how this project is synchronized between Teddy, ChatGPT, Claude Code, GitHub, and project evidence files.

The goal is to keep project memory accurate, local, version-controlled, and reviewable while minimizing Teddy's manual filing work.

---

## Active roles

| Role | Tool / Person | Responsibility |
|---|---|---|
| Final approver | Teddy | Final engineering and project approval |
| Strategic reviewer | ChatGPT | Analysis, strict review, architecture, decision-support, consistency checking |
| Sole local executor | Claude Code | Local file updates, project memory updates, evidence ingest, Git operations |
| Source of truth | GitHub repo | Persistent project record and audit trail |

---

## Inactive / retired roles

| Tool | Status |
|---|---|
| Claude Web | Optional backup / second opinion only. Not part of the active sync loop. |
| Codex CLI | Retired / historical only. No active project role. |
| Downloads folder | Temporary only. Not a project archive. |

---

## Core workflow

```text
Teddy or project evidence
    |
ChatGPT review / GPT Handoff Patch
    |
Teddy approval
    |
Claude Code pre-execution review
    |
Teddy approval
    |
Claude Code executes local file updates
    |
Claude Code writes Feedback to GPT
    |
Claude Code shows git diff
    |
Teddy approval
    |
Claude Code commit + push
    |
ChatGPT reviews GitHub state
```

---

## Source of truth hierarchy

When files disagree, use this priority:

1. `00_Control_Plane/NOW.md`
2. Formal project ledgers:
   * Decision log
   * Risk register
   * Action tracker
   * Open questions
   * Assumptions
   * Validation tracker
   * Communications log
3. Current project source files and evidence summaries
4. `04_Stakeholders/` derived views
5. `07_Context_Packs/` generated/curated AI context
6. AI working memory files, if present
7. Old drafts and historical notes

AI working memory is never authoritative unless confirmed by a formal ledger or `NOW.md`.

---

## Claude Code execution rule

Claude Code must not directly execute a GPT recommendation without first writing a pre-execution review at:
`08_Handoff_Patches/ClaudeCode_PreExecution_Review/`

Claude Code must wait for Teddy approval before executing.

---

## Claude Code feedback rule

After execution, Claude Code must create a feedback file at:
`08_Handoff_Patches/ClaudeCode_Feedback_To_GPT/`

---

## GPT handoff patch rule

ChatGPT should not directly rewrite project files.

ChatGPT should provide structured update instructions using the template at `_GLOBAL_PROTOCOLS/GPT_HANDOFF_PATCH_TEMPLATE.md`.

---

## Project inbox rule

This project must process only its own `_INBOX_RAW/`.

It must not directly process `_GLOBAL_INBOX_RAW/`.

Raw files arrive here only after the Global Router routes them into this project.

Claude Code project ingest should:

1. Scan this project's `_INBOX_RAW/`.
2. Group related files by topic/event.
3. Create project evidence packages when useful.
4. Generate summaries.
5. Update project communication logs if they exist.
6. Update stakeholder views if relevant.
7. Propose ledger changes but wait for Teddy approval before creating new formal decisions, risks, or actions.
8. Move processed files to `_INBOX_PROCESSED/`.

---

## Stale memory rule

Any AI memory, draft, or project note older than the current `NOW.md` must be treated as non-authoritative unless confirmed by formal ledgers.

Do not delete historical records. Mark them:

* SUPERSEDED
* CLOSED
* RETIRED
* HISTORICAL ONLY

---

## Do-not-overwrite rule

Claude Code must not overwrite:

* prior drafts;
* decision history;
* old risk records;
* old action records;
* historical AI memory;
* evidence files.

If a conclusion changes, append a new record or mark the old one superseded.

---

## Git rule

Claude Code must:

1. Show `git status` before changes.
2. Show a summary of modified files after changes.
3. Show `git diff` or a concise diff summary.
4. Ask Teddy before committing.
5. Ask Teddy before pushing.
6. Include clear commit messages.
