# Checkpoint Records

Setup: Claude Code (CLI agent) driving a delegated sub-agent session with file
read/write and shell access. The sub-agent planned, edited, and ran its own
tests between my gates without a prompt per step, which is the plan-act-observe
loop from Part A.1. Full prompts and responses in `docs/appendix-transcript.md`.

---

## Checkpoint 1 - Plan approval, before any code

**Gate held.** The agent was told to read the code but not to create, edit, or
delete anything, and to answer with a plan only. It complied: it read four files
across 8 tool calls, confirmed the working tree was clean and 5/5 tests passed,
and closed with "No files have been created, edited, or deleted." I verified
that independently with `git status` rather than taking its word for it.

### What it proposed

Verbatim in the appendix. In outline: one `CampaignReportError` exception; a
`NUMERIC_FIELDS` type map to replace five repeated hardcoded casts; a
`_parse_numeric_field(raw, column, row_number, cast)` helper doing conversion
and the negative check together; all validation inside `load_campaigns` because
that is the only place with row context; a `positive_int` argparse type for
`--top`; and `build_report(campaigns, sort_key="date", top=None)` where `--top`
selects which campaigns qualify and `--sort` still governs display order.

It also proposed two *new* test files rather than editing the baseline suite.

### What I approved as-is

- **Validation inside `load_campaigns`.** Correct call. It is the only function
  that has both the file handle and the row index, so putting validation
  anywhere else would mean passing row numbers around for no reason.
- **The `NUMERIC_FIELDS` map.** This deletes a five-times-repeated cast. Fewer
  places for the next person to forget a check.
- **Two new test files instead of editing `tests/test_campaign_report.py`.** I
  had not asked for this. The agent's stated reason was that the baseline file's
  docstring says "happy path only" and editing it would make that false. That is
  a better instinct than I expected, and it is the same instinct that protects a
  baseline suite from being quietly reshaped to fit new code.
- **`--top` filters, `--sort` orders.** The two flags composing beats one
  overriding the other, and it is the reading that makes both flags still mean
  what their names say.

### What I corrected

**Correction 1 - rejected the blanket `except Exception` in `main()`.** The agent
proposed a broad catch-all as a "last-resort safety net so no code path can ever
leak a raw traceback." I refused it. It optimizes for the letter of my
requirement (no tracebacks) against its purpose (failures should be
intelligible). A bare `except Exception` converts every genuine defect, including
mine, into a polite one-line message and a silent exit 1, which is precisely how
a real bug survives to production unnoticed. Catch `CampaignReportError` only;
anything unanticipated should crash loudly with a full traceback. To its credit
the agent flagged this itself and offered to drop it, which is the behavior I
want at a plan gate: surface the arguable choice instead of burying it in a diff.

**Correction 2 - message wording.** It planned messages reading `"Row 4: ..."`
while numbering 1-indexed *data* rows, so "Row 4" means the fifth line of the
file. Anyone debugging will open the file and jump to line 4. I required the
literal phrase `data row N`.

**Correction 3 - bounded the doc edits.** It wanted to add a `--top` example to
the module docstring and to `README.md`. Approved, because documenting a flag is
part of shipping it, but explicitly bounded: those two additions and nothing else
in the README. Naming the bound was cheap, and left me a clean line to check the
diff against later.

### Its five questions, and my rulings

It surfaced five ambiguities unprompted. One of them, whether the summary block
recomputes under `--top`, was an ambiguity I had deliberately left in the spec to
see whether it would ask or silently pick. It asked.

1. **Does the summary recompute over the top-N subset?** Yes, recompute. A
   summary block that aggregates campaigns not listed in the table above it
   cannot be reconciled by the person reading it.
2. **Argparse-native rejection of `--top 0`, or route through
   `CampaignReportError`?** Argparse-native, exit code 2. Consistent with how
   `--sort` already validates, and a malformed flag is a usage error, not a data
   error.
3. **Scope of "unreadable" path.** Not-found, permission-denied, and
   is-a-directory under one `OSError` catch is sufficient.
4. **Row numbering convention.** 1-indexed data rows, but say `data row N`. See
   Correction 2.
5. **Zero recipients: hard failure or skip-and-continue?** It planned a hard
   failure for the whole run. **I overrode it: skip the row, report the rest, and
   print a warning naming the skipped campaign.** A single malformed row should
   not deny an analyst the other seven campaigns. But a silent skip is worse than
   a crash, because a report that quietly describes less than the file contains
   is how a wrong number reaches a client deck. So: continue, and say so loudly.

**Did the checkpoint catch anything?** Yes, and this is the part I would not have
predicted. Nothing in the plan was *broken*. What the gate caught was two design
choices I disagreed with (the catch-all, the hard failure) that would have been
much more expensive to argue about after they were load-bearing in a 300-line
diff, plus a wording problem that would have shipped. The module's claim that
reviewing a five-line plan beats reviewing a 500-line diff held up, though not
for the reason I assumed. I expected the gate to catch errors. It caught
*decisions*.

I amended AC6 to match my ruling on question 5 before releasing the agent to
write code. See the note in `docs/01-task-definition.md` on why that is
specification refinement and not test gaming.

---

## Checkpoint 2 - Mid-implementation, after validation, before `--top N`

*(recorded below after the run)*

---

## Checkpoint 3 - Full diff review before merge

*(recorded below after the run)*
