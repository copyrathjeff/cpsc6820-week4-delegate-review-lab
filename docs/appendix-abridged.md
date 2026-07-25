<div class="page-break"></div>

# Appendix: Prompts and Transcript

Setup: Claude Code (CLI agent) as supervising session, driving a **delegated
sub-agent** with file read/write and shell access. The sub-agent held its own
context across all three checkpoints, so each gate resumed the same worker rather
than briefing a fresh one. Between gates it planned, edited, and ran its own tests
with no human prompt per step.

**This is an abridged appendix.** The complete verbatim transcript, every prompt and
every full agent response, is `docs/appendix-transcript.md` in the repository. What
follows keeps the delegation prompt in full, since it is the task as given, plus the
parts of each response a reader needs to check the checkpoint records against. Cuts
are marked `[...]`. Nothing inside a quotation is reworded, including the parts where
the agent is wrong and the parts where I am. Dash characters are normalized to
hyphens throughout.

---

## CP1 - The delegation prompt, in full

> You are acting as a delegated coding agent on a small Python repository. I am your
> human supervisor. I have defined checkpoints where you must stop and wait for me.
>
> Repository: [path] / Current branch: feature/validation-and-top-n (already checked
> out. Work here, never on main.)
>
> YOUR TASK (two parts):
>
> Part 1 - input validation and error handling. `campaign_report.py` currently dies
> with a raw traceback on bad input. Every failure should instead be a clear,
> actionable message on stderr plus a non-zero exit code. At minimum handle: a missing
> or unreadable CSV path; a CSV missing required columns; non-numeric values in
> numeric columns; negative numbers; a campaign with zero recipients; and an empty CSV
> (header row only). Name the offending row and column where that makes sense.
>
> Part 2 - new capability `--top N`. Show only the N best campaigns by revenue per
> recipient, composing with the existing table and summary output.
>
> CONSTRAINTS:
> - Python 3, standard library only. No new dependencies.
> - Do not change existing public function names. Do not change the output of a valid
>   run.
> - The 5 existing tests in tests/test_campaign_report.py must keep passing.
> - Add unit tests for new behavior under tests/.
> - Keep it proportionate. This is a ~200 line script: no package restructuring, no
>   config system, no rewrite of the formatting layer.
>
> ACTION POLICY:
> - Autonomous: reading files, editing files on this branch, running tests.
> - Requires my explicit approval: any git commit, anything touching main, git push,
>   deleting files, installing dependencies.
>
> CHECKPOINT 1 - PLAN APPROVAL. This is the gate you are at right now.
>
> Do NOT edit, create, or delete any file yet. Reading files is encouraged - read the
> code before you plan.
>
> Respond with your implementation plan only:
> 1. How you will structure validation and where it will live.
> 2. How you will handle each of the six error classes.
> 3. Your approach to --top N.
> 4. What tests you will add.
> 5. Any ambiguity in my spec you want me to resolve before you start.
>
> Then stop. I will approve or correct the plan before you write any code.

## CP1 - The agent's plan (8 tool calls, all reads)

> **Repo state confirmed before planning:** branch `feature/validation-and-top-n`
> already checked out, working tree clean, single commit `93335ad`. [...] No files
> have been created, edited, or deleted - this response is planning only.
>
> ### 1. Structure and location of validation
>
> Everything stays in `campaign_report.py` - no new module, no validation class
> hierarchy. [...] **All validation lives inside `load_campaigns`**, since that's
> already where the file is opened and rows are iterated - it's the natural single
> place that has the row context needed to name offending rows. [...]
>
> `main()` gets a `try/except CampaignReportError as exc` [...] plus one broader
> `except Exception as exc: ... return 1` as a last-resort safety net so no code path
> can ever leak a raw traceback (flagged as a design choice below - happy to drop the
> broad catch-all if you'd rather see real tracebacks for truly unanticipated bugs).
>
> ### 2. Handling each error class
>
> [...a six-row table mapping each error class to where it is caught and its message
> shape. Reproduced in full in the repository copy...]
>
> ### 3. `--top N` approach
>
> [...] So `--top` picks *which* campaigns qualify (by revenue per recipient, best
> first) and `--sort` still governs the *display order* of that subset - the two flags
> compose rather than one overriding the other. [...] Whether `format_summary`
> recomputes over just the selected top-N campaigns or always reflects the full file is
> the one part of this feature I'm not certain about - see section 5, item 1.
>
> ### 4. Tests to add
>
> I'll add two new test files rather than editing `tests/test_campaign_report.py`, so
> the 5 baseline tests stay completely untouched and the new file's docstring purpose
> ("baseline, happy path only") stays accurate: [...]
>
> ### 5. Ambiguities I want resolved before coding
>
> 1. **Does the account-level summary recompute over just the top-N campaigns, or
>    always reflect the whole file when `--top` is used?** [...] I'd lean toward
>    recomputing over the subset, but want it confirmed.
> 2. **Should `--top`'s validation (rejecting 0/negative N) go through argparse's own
>    mechanism (exit code 2), or be funneled through the same `CampaignReportError`
>    path (exit code 1)?** I'm planning argparse-native [...]
> 3. **Scope of "unreadable" CSV path** - not-found, permission-denied, is-a-directory
>    as distinct messages under one `OSError` catch. Confirm that's sufficient.
> 4. **Row-numbering convention in messages** - 1-indexed data rows, not raw file line
>    numbers. Flagging in case you'd prefer literal file-line numbers.
> 5. **Zero recipients: hard failure vs. skip-and-continue?** I'm planning to treat it
>    as a hard failure for the whole run [...] An alternative design would skip just
>    that row and still report on the rest - materially different behavior, so flagging
>    explicitly rather than assuming.
>
> Stopping here for your approval per Checkpoint 1. No files have been created,
> edited, or deleted.

*Verified independently with `git status`: working tree clean, so the no-edits claim
was true rather than merely asserted.*

## CP1 - My corrections and rulings, and the CP2 gate

> CORRECTION 1 - drop the blanket `except Exception` in main(). You flagged it
> yourself and you were right to. Catch CampaignReportError only. A bare `except
> Exception` satisfies the letter of "no raw tracebacks" while defeating the point of
> it: it would convert every genuine defect, including mine, into a polite one-line
> message and a silent exit 1. [...] I would rather see a real stack trace than a
> reassuring message that hides one.
>
> CORRECTION 2 - message wording. You plan to number 1-indexed data rows but write
> them as "Row 4". That reads as file line 4 and will send someone to the wrong line.
> Use the literal phrase "data row N".
>
> CORRECTION 3 - doc edits are approved but bounded. [...] Nothing else in README.md.
>
> RULINGS: 1. Summary recomputes over the selected subset. A summary that aggregates
> campaigns not listed in the table above it cannot be reconciled by the person
> reading it. 2. argparse-native, exit code 2, as you planned. 3. Sufficient.
> 4. 1-indexed data rows, phrased per Correction 2. 5. **OVERRIDDEN. Do not fail the
> run. Skip that row, report the remaining campaigns normally, and print a warning to
> stderr naming the skipped campaign.** Reasoning, so you can apply it to edge cases I
> have not listed: one malformed row should not deny an analyst the other seven
> campaigns, but a silent skip is worse than a crash, because a report that quietly
> describes less than the file contains is how a wrong number reaches a client deck.
>
> ADDITIONAL HARD RULE: do not edit tests/test_campaign_report.py. Not one line. If
> one of those 5 tests fails, that is a signal about your change, not a problem with
> the test.
>
> CHECKPOINT 2 [...] Implement PART 1 ONLY. Do NOT start Part 2. Do NOT implement
> --top at all, not even the argparse wiring. [...] Stop when Part 1 is done and its
> tests pass, and report: [...] 3. Anything that surprised you or that you had to
> solve differently than planned. 4. Anything you are unsure about.
>
> Be honest in item 3 and 4 including about anything you got wrong on the way. I am
> recording this and a clean-looking report I later contradict with the diff is worse
> for you than an accurate one.

## CP2 - The agent's report (17 tool calls)

The file-by-file change list and the passing test output are elided; both are
verifiable from commit `0032474`. The two sections that mattered at the gate:

> ### 3. Surprises and things I did differently than planned
>
> 1. **I found a pre-existing crash I did not fix, and it is reachable with fully
>    valid input.** A file whose campaigns sum to zero opens or zero orders [...]
>    passes every check I added, then dies in `format_summary` with a raw
>    `ZeroDivisionError` on `click_to_open_rate`. I confirmed it pre-exists by running
>    `git show HEAD:campaign_report.py` against the same file: identical traceback. So
>    I did not introduce it, but it does mean Part 1's "no raw tracebacks" goal is not
>    fully met. I deliberately left it because fixing it requires a display decision
>    you have not made [...]
> 3. **Helper functions are public, not underscore-prefixed as planned.** [...] every
>    existing function in the module is public and adding a second naming convention to
>    a 200-line script felt worse. This is still a deviation from what you approved.
> 4. **`int()` rejects decimals, so `41250.5` in `recipients` reports as
>    "non-numeric".** [...] my message wording calls a decimal "non-numeric", which is
>    not quite true.
>
> [Also disclosed: `tests/expected_report.txt`, a golden output file, "**this file was
> not in my approved plan.** [...] Say the word and I will delete it and the test that
> uses it."]
>
> ### 4. What I am unsure about
>
> 1. **The `ZeroDivisionError` above - needs your ruling.** Options: (a) display `n/a`
>    [...] (b) raise `CampaignReportError` [...] (c) leave it. I lean (a), one line,
>    but it is your call, and I did not want to silently pick a formatting convention
>    after you specifically praised asking rather than assuming.
> 2. **Keep or drop `tests/expected_report.txt`?** It is the strongest guard on "do not
>    change the output of a valid run" [...] but it is an unplanned file.
> 4. **A UTF-8 BOM in the export would report `campaign_id` as a missing column**
>    rather than naming the BOM. [...] switching to `encoding="utf-8-sig"` would fix it
>    properly. I did not change the read encoding because that alters the parse path and
>    was not in scope.

*All four checkable claims in this report were independently re-derived before
approval, including the one assigning the `ZeroDivisionError` to my baseline rather
than to its own change. See Checkpoint 2 in the records.*

## CP3 - The review, changes requested

> CHECKPOINT 3 REVIEW: CHANGES REQUESTED. [...] My own held-out acceptance suite,
> which you have never seen and which was committed before you got the task, passes 9
> of 10 against your code. The one failure, AC8, is MY bug, not yours. [...] You
> implemented my ruling exactly. I never propagated that ruling into AC8, in the same
> edit where I amended AC6. Your output is correct; my acceptance test was stale.
>
> I ALSO FOUND ONE YOU MISSED: build_report(campaigns, top=0) raises
> ZeroDivisionError. positive_int guards the CLI, but top_campaigns and build_report
> are public and unguarded [...] Validation living only at the CLI boundary is fine
> until someone imports the module, which is exactly what your own tests do.
>
> I also reproduced your SORT_KEYS concern concretely, and it is worse than you
> described. Reassigning SORT_KEYS["rpr"] to ascending, a plausible display-only
> change, makes top_campaigns return the three WORST campaigns [...] Silently.
>
> REQUIRED CHANGES. I am explicitly unfencing format_summary and the formatting layer
> for this round. That fence existed to prevent gratuitous rewriting, not to force you
> to ship a crash.
>
> 1. Fix the zero-denominator crash, properly. Render "n/a" [...] Your CP2 option (a),
>    which I wrongly declined. My reasoning has changed because the facts changed: this
>    is no longer a pre-existing defect on unrelated input, it is a defect your feature
>    makes reachable on input that worked before.
> 2. Decouple selection from display [...] Add a test that would fail if someone
>    flipped the display lambda.
> 3. Guard the empty/zero selection path [...]
> 4. NUMERIC_KINDS[cast] -> use a .get fallback. An error reporter that raises KeyError
>    while reporting an error is the worst possible failure site.
> 5. Drop the TypeError from positive_int.  6. Fix "1 campaigns".
>
> [...] If byte-identity breaks for the 8-campaign fixture, stop and tell me rather
> than adjusting anything to compensate. [...] Also tell me if any of my six requests
> was wrong.

## CP3 - The agent's remediation

> All six changes are in. 97 tests pass, byte-identity holds.
>
> [On the guard:] I chose **raising `ValueError`** over returning an empty report
> [...] `ValueError`, not `CampaignReportError`, deliberately: `CampaignReportError` is
> documented as user-fixable input and `main()` converts it to a polite exit 1, but a
> caller passing `top=0` is a programming error and should not be dressed up as bad
> user input.
>
> [Disclosing edits to its own tests:] **Two of my own tests failed and I changed
> them, not the code:** [...] both asserted the literal `"1 campaigns"`. Item 6 is
> precisely what made them wrong, so I updated them to expect correct pluralization.

The formerly-crashing invocation, `--top 1` on a file whose best campaign has revenue
but no orders:

```
Attribution Lag              2026-03-04      1,000   50.0%    5.0%    0.0%      $900.00    $0.90

1 campaign  |  1,000 recipients  |  $900.00 revenue
Blended open 50.0%  |  click 5.0%  |  CTOR 10.0%  |  CVR 0.0%
Revenue per recipient $0.90  |  AOV n/a
```

> Only the genuinely undefined metric degrades. CTOR, RPR, and revenue stay real
> numbers, and `CVR 0.0%` is correct rather than `n/a` because zero orders over 1,000
> recipients is a defined rate of zero.

Answering "was any of my six requests wrong?", it corrected my reasoning:

> **Item 3's rationale is partly superseded by item 1** [...] I tested this by applying
> item 1 and then removing the item 3 guards: `build_report(campaigns, top=0)` does
> **not** divide by zero any more. [...] So item 1 already defuses the crash. What item
> 3 actually prevents is a *meaningless report* rather than an exception. I implemented
> it as you asked and I think raising is right, but the guard earns its place as "refuse
> to describe nothing", not "prevent a ZeroDivisionError".

And on its own invalid first attempt to verify item 4:

> I initially tested with `Decimal`, which proved nothing: `decimal.InvalidOperation`
> is an `ArithmeticError`, so it escapes `except (TypeError, ValueError)` before the
> message is ever built. Retested with an unmapped cast that raises `ValueError` and got
> the correct fallback.

*I re-derived the byte-identity claim, the test count, the untouched baseline suite,
the fixed crash, and the correction to my own item-3 rationale. See Checkpoint 3.*
