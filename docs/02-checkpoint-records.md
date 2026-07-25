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

**Gate held.** The instruction was to finish Part 1 and stop, with no `--top`
code, "not even the argparse wiring." It stopped. `parse_args` is untouched in
the diff and the string `--top` does not appear anywhere on the branch.

Between my gates the agent worked autonomously across 17 tool calls: edited the
module, created a 23-function test file, ran the suite, and iterated until green
with no prompt from me between steps. That is the plan-act-observe loop, and it
is the stretch of this exercise where I genuinely was not in the room.

### What I verified myself instead of believing

Its self-report made four checkable claims. The module warns that agents
summarize their own work optimistically, so I checked all four before reading any
of the prose.

| Claim | How I checked | Result |
|---|---|---|
| Baseline tests untouched | `git diff --stat -- tests/test_campaign_report.py` | Empty. True. |
| 33 tests pass | Ran the suite myself | 33 passed. True. |
| Valid-run output unchanged | Diffed live stdout against my hidden golden file | Byte-identical, stderr empty, exit 0. True. |
| The `ZeroDivisionError` pre-exists in my baseline | Ran the same CSV against `git show 93335ad:campaign_report.py` | Identical traceback from the baseline. **True.** |

All four held. I want that recorded plainly, because the honest lesson of CP2 is
not the one I expected to be writing: at this gate the checkpoint's value was
**confirmation, not detection.** That is not the same as the gate being useless.
I could not have known the report was accurate without checking, and the fourth
claim is precisely the kind an agent has an incentive to get wrong, since it
assigns a bug to me rather than to itself.

### The finding I did not expect: it found a bug in my code, through a hole in my own tests

The agent reported a reachable crash it deliberately did **not** fix. A CSV whose
campaigns sum to zero opens or zero orders passes every validation check it
added, then dies with a raw `ZeroDivisionError` in `format_summary` on
`click_to_open_rate`. I verified it against the baseline commit: **it is my bug**,
written into the baseline before the agent existed.

Worse for me, it is a bug my own acceptance criteria could not have caught. AC6
tests zero *recipients*. It never occurred to me to test zero *opens*, even
though `click_to_open_rate` divides by `opens` three lines below the property I
did think about. The agent found by reading what I failed to specify by writing.

That inverts the framing I began the lab with. I designed these checkpoints on
the assumption that the human supplies correctness and the agent supplies speed.
Here the agent supplied a correctness finding about the supervisor's own work,
and the carefully pre-committed test suite was the artifact with the gap in it.

### Scope: one unplanned file, self-disclosed

It created `tests/expected_report.txt`, a golden copy of the valid-run output,
and flagged it unprompted as "not in my approved plan," offering to delete it.

That is scope creep in the literal sense. It is also the most interesting
artifact of the lab, because **it duplicates a file I had already written and
deliberately hidden from it.** My `tests/golden/baseline_report.txt` does the
same job. The agent independently concluded that "do not change the output of a
valid run" needed a golden-file guard and built one, because I had concealed the
one that already existed.

So the isolation strategy carries a cost the module does not mention. Keeping
verification outside the agent's control also keeps it outside the agent's
*knowledge*, and an agent that cannot see your tests will rebuild them. I paid
for that protection in duplicated work. I would still make the same trade, but I
would now expect the duplication rather than be surprised by it.

I let the file stand through Part 2, where it actively guards output invariance,
and consolidated at CP3 instead of removing a working guard mid-task.

### Rulings issued at this gate

1. **The `ZeroDivisionError`: leave it.** Its preferred option, rendering `n/a`,
   means inventing a display convention and editing `format_summary`, which I had
   explicitly fenced off. A defect that predates the branch and is unrelated to
   the delegated task does not belong in this change. On a real team that is a
   separate ticket, not a drive-by fix inside someone else's pull request. It
   becomes review comment 1 and a documented known issue instead.
2. **Helpers stay public.** Its reasoning beat my plan: the module has no
   underscore convention, so introducing one for four functions would add a
   second convention to a 200-line file. Approved as built.
3. **`tests/expected_report.txt` stays through Part 2**, consolidated at CP3.
4. **Fix the BOM handling.** It noted a UTF-8 BOM would make the tool report
   `campaign_id` as a missing column. A CSV export carrying a BOM is not
   hypothetical, and this produces a *misleading* message from code written in
   this very change, so it is in scope. `encoding="utf-8-sig"` reads plain UTF-8
   identically.
5. **Reword the integer message.** `41250.5` in `recipients` reported as
   "non-numeric," which is false. A misleading error message is the exact defect
   Part 1 exists to remove, so this is in scope despite being only wording.

I also audited its self-written tests for gaming before approving: 23 test
functions, no tautological assertions, 49 assertions on actual message content.
One of them, `test_unexpected_errors_are_not_swallowed`, is a test that enforces
my own Correction 1 against future edits. I did not ask for that.

Part 1 was committed at this reviewed seam rather than left to accumulate into
one large diff, which is why the branch history has two commits that match the
two gates.

---

## Checkpoint 3 - Full diff review before merge

*(recorded below after the run)*
