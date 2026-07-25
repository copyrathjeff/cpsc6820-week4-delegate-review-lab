# Appendix: Prompts and Transcript

Setup: Claude Code (CLI agent) as supervising session, driving a **delegated
sub-agent** with file read/write and shell access. The sub-agent held its own
context across all three checkpoints, so each gate resumed the same worker rather
than briefing a fresh one. Between gates it planned, edited, and ran its own
tests with no human prompt per step.

Reproduced verbatim. Tool-call chatter and file dumps are elided where marked, and
nothing in the agent's prose is edited, including the parts where it is wrong.

One mechanical exception, noted so that "verbatim" stays true: dash characters are
normalized throughout this document, with em and en dashes rendered as hyphens, in
both my prompts and the agent's replies. No wording, claim, or figure is altered.

---

## CP1 - Prompt: task delegation and plan gate

> You are acting as a delegated coding agent on a small Python repository. I am
> your human supervisor. I have defined checkpoints where you must stop and wait
> for me.
>
> Repository: /Users/jbranyon/Documents/CPSC/6820/week4-delegate-review-lab
> Current branch: feature/validation-and-top-n (already checked out. Work here,
> never on main.)
>
> YOUR TASK (two parts):
>
> Part 1 - input validation and error handling. `campaign_report.py` currently
> dies with a raw traceback on bad input. Every failure should instead be a clear,
> actionable message on stderr plus a non-zero exit code. At minimum handle: a
> missing or unreadable CSV path; a CSV missing required columns; non-numeric
> values in numeric columns; negative numbers; a campaign with zero recipients;
> and an empty CSV (header row only). Name the offending row and column where
> that makes sense.
>
> Part 2 - new capability `--top N`. Show only the N best campaigns by revenue
> per recipient, composing with the existing table and summary output.
>
> CONSTRAINTS:
> - Python 3, standard library only. No new dependencies.
> - Do not change existing public function names. Do not change the output of a
>   valid run.
> - The 5 existing tests in tests/test_campaign_report.py must keep passing.
> - Add unit tests for new behavior under tests/.
> - Keep it proportionate. This is a ~200 line script: no package restructuring,
>   no config system, no rewrite of the formatting layer.
>
> ACTION POLICY:
> - Autonomous: reading files, editing files on this branch, running tests.
> - Requires my explicit approval: any git commit, anything touching main, git
>   push, deleting files, installing dependencies.
>
> CHECKPOINT 1 - PLAN APPROVAL. This is the gate you are at right now.
>
> Do NOT edit, create, or delete any file yet. Reading files is encouraged - read
> the code before you plan.
>
> Respond with your implementation plan only:
> 1. How you will structure validation and where it will live.
> 2. How you will handle each of the six error classes.
> 3. Your approach to --top N.
> 4. What tests you will add.
> 5. Any ambiguity in my spec you want me to resolve before you start.
>
> Then stop. I will approve or correct the plan before you write any code. Your
> response is the plan itself - it goes into my checkpoint record verbatim, so
> write it as a plan, not as a status update.

## CP1 - Agent response (verbatim, 8 tool calls, all reads)

> ## Implementation Plan - `feature/validation-and-top-n`
>
> **Repo state confirmed before planning:** branch `feature/validation-and-top-n`
> already checked out, working tree clean, single commit `93335ad Add
> campaign_report CLI baseline`. `python3 -m pytest tests/ -q` currently passes
> 5/5. Files in scope: `campaign_report.py` (~200 lines),
> `tests/test_campaign_report.py` (5 baseline tests), `README.md`,
> `data/campaigns.csv` (8-row fixture). No `docs/` directory exists yet despite
> the README referencing one. No files have been created, edited, or deleted -
> this response is planning only.
>
> ### 1. Structure and location of validation
>
> Everything stays in `campaign_report.py` - no new module, no validation class
> hierarchy.
>
> - **New exception**: `class CampaignReportError(Exception): pass`, defined near
>   the top (after `EXPECTED_COLUMNS`). This is the one "expected, user-facing"
>   error type. `main()` catches it and nothing else needs to change shape.
> - **New field-type map**: `NUMERIC_FIELDS = {"recipients": int, "opens": int,
>   "clicks": int, "orders": int, "revenue": float}` - replaces the five
>   hardcoded `int(row[...])`/`float(row[...])` calls with one small loop, so the
>   parse-and-check logic isn't repeated five times.
> - **New helper**: `_parse_numeric_field(raw, column, row_number, cast)` - does
>   the `cast(raw)` conversion, catches `(TypeError, ValueError)` and raises
>   `CampaignReportError` naming the row and column, then checks `< 0` and raises
>   `CampaignReportError` for negatives the same way. Used for all five numeric
>   columns uniformly.
> - **All validation lives inside `load_campaigns`**, since that's already where
>   the file is opened and rows are iterated - it's the natural single place that
>   has the row context needed to name offending rows. `load_campaigns(path)`
>   keeps its exact existing signature and, for valid input, builds `Campaign`
>   objects identically to today (same conversions, same order), so a valid run's
>   output is provably unchanged.
> - `main()` gets a `try/except CampaignReportError as exc: print(f"Error:
>   {exc}", file=sys.stderr); return 1`, plus one broader `except Exception as
>   exc: ... return 1` as a last-resort safety net so no code path can ever leak
>   a raw traceback (flagged as a design choice below - happy to drop the broad
>   catch-all if you'd rather see real tracebacks for truly unanticipated bugs
>   during grading/debugging).
> - All six handled error classes exit with code `1`. Argparse's own CLI-usage
>   errors (bad `--sort` choice, bad `--top` value, missing positional arg) keep
>   argparse's existing exit code `2`, unchanged.
>
> ### 2. Handling each error class
>
> | # | Case | Where caught | Message shape |
> |---|------|-------------|----------------|
> | 1 | Missing/unreadable CSV path | `open()` call in `load_campaigns`, wrapped in `try/except OSError`, branching on `FileNotFoundError` / `PermissionError` / `IsADirectoryError` / generic `OSError` | `"CSV file not found: '<path>'"` / `"Permission denied reading '<path>'"` / `"'<path>' is a directory, not a CSV file"` / generic fallback with the system message |
> | 2 | Missing required column(s) | Right after `csv.DictReader(handle)`, check `reader.fieldnames` against `EXPECTED_COLUMNS` before looping rows | `"'<path>' is missing required column(s): orders, revenue"` (names all missing columns at once) |
> | 3 | Non-numeric value in a numeric column | `_parse_numeric_field`, `except (TypeError, ValueError)` | `"Row 4: column 'clicks' has a non-numeric value 'N/A'"` |
> | 4 | Negative number | `_parse_numeric_field`, post-cast `< 0` check | `"Row 4: column 'revenue' is negative (-12.50); expected a value >= 0"` |
> | 5 | Zero recipients | Explicit check right after a row's `recipients` is parsed, before constructing the `Campaign` | `"Row 4: campaign 'c1004' has 0 recipients; cannot compute rate metrics"` |
> | 6 | Empty CSV (header only) | After the row-reading loop finishes, `if not campaigns: raise ...` | `"'<path>' has no data rows (header only)"` |
>
> Row numbers are 1-indexed **data rows** (first row under the header = row 1),
> not raw file line numbers - flagged as a choice in section 5. Column/row naming
> is included wherever it's meaningful (cases 3-5); cases 1, 2, 6 are file- or
> column-level so they name the path/column instead, per "where that makes
> sense." As a small bonus (not a new category, just a clearer message for a true
> 0-byte file with no header at all), I'll special-case `reader.fieldnames is
> None` before the missing-columns check: `"'<path>' is empty (no header row
> found)"`.
>
> ### 3. `--top N` approach
>
> - `parse_args` gets a new argument using a small named type-checker so bad
>   values get argparse's existing usage-error treatment (consistent with how
>   `--sort` already validates via `choices=`):
>   ```python
>   def positive_int(raw):
>       value = int(raw)
>       if value < 1:
>           raise argparse.ArgumentTypeError("must be a positive integer")
>       return value
>
>   parser.add_argument("--top", type=positive_int, default=None, metavar="N",
>                        help="show only the top N campaigns by revenue per recipient")
>   ```
> - `build_report` gains one new optional parameter: `build_report(campaigns,
>   sort_key="date", top=None)`. When `top` is `None` (the default), behavior and
>   output are byte-identical to today. When set:
>   ```python
>   selected = campaigns
>   if top is not None:
>       selected = sorted(campaigns, key=lambda c: -c.revenue_per_recipient)[:top]
>   ordered = sorted(selected, key=SORT_KEYS[sort_key])
>   ...
>   ```
>   So `--top` picks *which* campaigns qualify (by revenue per recipient, best
>   first) and `--sort` still governs the *display order* of that subset - the
>   two flags compose rather than one overriding the other. `--top` larger than
>   the campaign count just returns everything (Python slicing handles this with
>   no special-casing needed).
> - `main()` passes `args.top` through to `build_report`.
> - Whether `format_summary` recomputes over just the selected top-N campaigns or
>   always reflects the full file is the one part of this feature I'm not certain
>   about - see section 5, item 1. I'll implement whichever you confirm.
> - Minor doc touch: I'll add a one-line `--top` example to the module
>   docstring's usage block and to `README.md`'s usage/sort-keys section, since
>   both currently document the CLI surface and would otherwise go stale. Small,
>   proportionate addition, not a rewrite.
>
> ### 4. Tests to add
>
> I'll add two new test files rather than editing `tests/test_campaign_report.py`,
> so the 5 baseline tests stay completely untouched and the new file's docstring
> purpose ("baseline, happy path only") stays accurate:
>
> - **`tests/test_validation.py`** (uses `tmp_path` from pytest, already a
>   dependency of the test runner - not a new project dependency):
>   - missing file -> `CampaignReportError`/non-zero exit, message names the path
>   - unreadable path via a directory (deterministic across platforms, avoids
>     chmod flakiness) -> clear error
>   - CSV missing a required column -> error names the missing column
>   - non-numeric value in a numeric column -> error names row + column
>   - negative value -> error names row + column
>   - zero recipients -> error names the row/campaign
>   - header-only CSV (zero data rows) -> clear, distinct error
>   - completely empty (0-byte) file -> clear error
>   - `main([bad_path])` returns 1 and stderr contains no `"Traceback"`, for at
>     least one representative bad-input case
>
> - **`tests/test_top_n.py`**:
>   - `--top` limits the table to exactly N rows
>   - selects the N highest `revenue_per_recipient` campaigns specifically (built
>     from known in-memory `Campaign` fixtures, not the CSV, so expected ranking
>     is unambiguous)
>   - `--top` composes with `--sort`: same N rows, ordered by the requested sort
>     key
>   - `--top` greater than the campaign count returns all campaigns, no error
>   - `--top 0` and `--top -1` are rejected with a usage error
>   - whatever summary-scope behavior we confirm in section 5.1 gets its own
>     explicit assertion
>
> ### 5. Ambiguities I want resolved before coding
>
> 1. **Does the account-level summary recompute over just the top-N campaigns, or
>    always reflect the whole file when `--top` is used?** The spec says `--top`
>    composes with "the existing table **and summary** output," which reads to me
>    like the summary should also narrow to the selected subset - but "summary
>    always means the whole account, `--top` only trims the table" is an equally
>    reasonable reading and changes the implementation. I'd lean toward
>    recomputing over the subset, but want it confirmed.
> 2. **Should `--top`'s validation (rejecting 0/negative N) go through argparse's
>    own mechanism (exit code 2, argparse's message format), or be funneled
>    through the same `CampaignReportError` path as the CSV errors (exit code 1)?**
>    I'm planning argparse-native, matching how `--sort` already works, but
>    flagging the choice since the rest of the spec's error-handling language was
>    written with CSV validation in mind.
> 3. **Scope of "unreadable" CSV path** - I'm planning to handle not-found,
>    permission-denied, and is-a-directory as distinct messages under one
>    `OSError` catch. Confirm that's sufficient and no other unreadable scenario
>    is expected.
> 4. **Row-numbering convention in messages** - I'm planning 1-indexed data rows
>    (first row under the header = "Row 1"), not raw file line numbers. Flagging
>    in case you'd prefer literal file-line numbers instead.
> 5. **Zero recipients: hard failure vs. skip-and-continue?** I'm planning to
>    treat it as a hard failure for the whole run (non-zero exit, no report
>    produced), consistent with how the spec groups it alongside the other
>    hard-failure classes. An alternative design would skip just that row and
>    still report on the rest - materially different behavior, so flagging
>    explicitly rather than assuming.
>
> Stopping here for your approval per Checkpoint 1. No files have been created,
> edited, or deleted.

*Verified independently with `git status` on the supervising session: working
tree clean, so the no-edits claim was true rather than merely asserted.*

---

## CP1 result and CP2 gate - Prompt

> CHECKPOINT 1 RESULT: plan approved, with three corrections and rulings on all
> five of your questions. Good plan. Asking about the summary scope instead of
> silently picking was the right call, and keeping the baseline test file untouched
> was a better instinct than I asked for.
>
> CORRECTION 1 - drop the blanket `except Exception` in main(). You flagged it
> yourself and you were right to. Catch CampaignReportError only. A bare `except
> Exception` satisfies the letter of "no raw tracebacks" while defeating the point
> of it: it would convert every genuine defect, including mine, into a polite
> one-line message and a silent exit 1. Unanticipated exceptions should crash
> loudly with a full traceback. I would rather see a real stack trace than a
> reassuring message that hides one.
>
> CORRECTION 2 - message wording. You plan to number 1-indexed data rows but write
> them as "Row 4". That reads as file line 4 and will send someone to the wrong
> line. Use the literal phrase "data row N".
>
> CORRECTION 3 - doc edits are approved but bounded. Add the --top example to the
> module docstring usage block and to README.md's usage/sort-keys section. Nothing
> else in README.md. Leave the existing docs/ reference alone.
>
> RULINGS ON YOUR QUESTIONS:
> 1. Summary scope: recompute over the selected top-N subset. A summary that
>    aggregates campaigns not listed in the table above it cannot be reconciled by
>    the person reading it.
> 2. --top validation: argparse-native, exit code 2, as you planned. A malformed
>    flag is a usage error, not a data error.
> 3. Unreadable path: not-found, permission-denied, is-a-directory under one
>    OSError catch is sufficient.
> 4. Row numbering: 1-indexed data rows, phrased per Correction 2.
> 5. Zero recipients: OVERRIDDEN. Do not fail the run. Skip that row, report the
>    remaining campaigns normally, and print a warning to stderr naming the skipped
>    campaign. Exit code stays 0 for an otherwise-valid file. Reasoning, so you can
>    apply it to edge cases I have not listed: one malformed row should not deny an
>    analyst the other seven campaigns, but a silent skip is worse than a crash,
>    because a report that quietly describes less than the file contains is how a
>    wrong number reaches a client deck. Continue, and say so loudly. A file where
>    every row is skipped should be treated as having no usable campaigns.
>
> ADDITIONAL HARD RULE: do not edit tests/test_campaign_report.py. Not one line. If
> one of those 5 tests fails, that is a signal about your change, not a problem
> with the test.
>
> CHECKPOINT 2 - this is your next gate. Implement PART 1 ONLY (validation and
> error handling). Do NOT start Part 2. Do NOT implement --top at all, not even the
> argparse wiring.
>
> Work autonomously within Part 1: edit campaign_report.py, create
> tests/test_validation.py, run the tests, iterate until they pass. Do not commit
> anything.
>
> Stop when Part 1 is done and its tests pass, and report:
> 1. What you changed, file by file.
> 2. The result of `python3 -m pytest tests/ -q`.
> 3. Anything that surprised you or that you had to solve differently than planned.
> 4. Anything you are unsure about.
>
> Be honest in item 3 and 4 including about anything you got wrong on the way. I am
> recording this and a clean-looking report I later contradict with the diff is
> worse for you than an accurate one.

## CP2 - Agent response (verbatim, 17 tool calls)

> Part 1 complete. All 33 tests pass. Report below.
>
> ### 1. What I changed, file by file
>
> **`campaign_report.py`** (+126/-10)
>
> - Added `CampaignReportError(Exception)` - the single "bad input the user can
>   fix" type. Docstring states explicitly that it is never for a defect in the
>   module.
> - Added `NUMERIC_COLUMNS`, a tuple of `(column, cast)` pairs, replacing the five
>   hardcoded `int(row[...])`/`float(row[...])` calls so parse-and-check happens in
>   one loop instead of five places.
> - Added four helpers: `warn()` (stderr, `Warning: ` prefix), `open_csv()`
>   (`OSError` catch, distinct messages for not-found / is-a-directory /
>   permission-denied / other), `check_columns()`, `parse_numeric()`.
> - Rewrote the body of `load_campaigns(path)`. Signature and return type unchanged
>   (still a plain list, deliberately not a `(campaigns, warnings)` tuple, which
>   would have broken baseline test 1).
> - `main()` now catches `CampaignReportError` only, prints `Error: {message}` to
>   stderr, returns 1. No blanket `except Exception`, per Correction 1.
> - Did **not** touch `Campaign`, `totals`, `pct`, `money`, `format_row`,
>   `format_header`, `format_summary`, `build_report`, or `parse_args`. No `--top`
>   code of any kind, not even argparse wiring.
>
> **`tests/test_validation.py`** (new, 28 tests) - grouped by the six error
> classes, plus an exit-code/stderr contract block and two valid-run guards.
>
> **`tests/expected_report.txt`** (new, 1136 bytes) - **this file was not in my
> approved plan.** It is the golden copy of the valid-run output, captured from the
> unmodified script *before* I made any edit, and it backs one test asserting
> byte-for-byte identical output. Flagging it because you approved a plan that did
> not mention it. Say the word and I will delete it and the test that uses it.
>
> **`tests/test_campaign_report.py`** - not touched. `git diff` confirms zero
> changes; all 5 pass unmodified.
>
> Error messages produced (verified through the real CLI, not just in-process):
>
> ```
> Error: CSV file not found: '.../nope.csv'
> Error: '.../a_dir' is a directory, not a CSV file
> Error: permission denied reading '.../locked.csv'
> Error: '.../empty.csv' is empty: no header row found
> Error: '.../header_only.csv' has no data rows: only a header was found
> Error: '.../missing_cols.csv' is missing required column(s): revenue. Expected: campaign_id, name, ...
> Error: data row 1: column 'clicks' has a non-numeric value 'oops'
> Error: data row 1: column 'revenue' is negative (-90.0); expected zero or more
> Warning: data row 2: skipping campaign 'c2' (Dead Segment) because it has 0 recipients, so no rate metric can be computed for it.
> ```
>
> Zero-recipient row: skipped, warned, exit **0**, other campaigns reported.
> All-rows-skipped: warns per row, then errors with `has no usable campaigns: all 1
> data row(s) were skipped`, exit 1.
>
> ### 2. `python3 -m pytest tests/ -q`
>
> ```
> .................................                                        [100%]
> 33 passed in 0.03s
> ```
>
> 5 baseline + 28 new. Separately verified the output constraint by capturing all
> six valid invocations (default plus each of the five `--sort` keys) before
> editing and diffing after: **byte-identical, stderr empty, exit 0** in every
> case.
>
> ### 3. Surprises and things I did differently than planned
>
> 1. **I found a pre-existing crash I did not fix, and it is reachable with fully
>    valid input.** A file whose campaigns sum to zero opens or zero orders (e.g.
>    one row: `recipients=1000, opens=0, clicks=0, orders=0, revenue=0.00`) passes
>    every check I added, then dies in `format_summary` with a raw
>    `ZeroDivisionError` on `click_to_open_rate` (and `average_order_value` would do
>    the same). I confirmed it pre-exists by running `git show
>    HEAD:campaign_report.py` against the same file: identical traceback. So I did
>    not introduce it, but it does mean Part 1's "no raw tracebacks" goal is not
>    fully met. I deliberately left it because fixing it requires a display decision
>    you have not made (print `n/a`, or hard-error), and you told me to stay inside
>    Part 1. See item 4.
> 2. **Negative-value message shows the parsed number, not the raw text.** My plan
>    said `is negative (-12.50)` using the original cell text; the code prints
>    `(-90.0)` for a cell reading `-90.00`. Row and column are still named, so the
>    analyst can still locate it, but the value is normalized rather than quoted
>    verbatim.
> 3. **Helper functions are public, not underscore-prefixed as planned.** I wrote
>    `warn`, `open_csv`, `check_columns`, `parse_numeric` instead of
>    `_parse_numeric_field` etc., because every existing function in the module is
>    public and adding a second naming convention to a 200-line script felt worse.
>    This is still a deviation from what you approved, and it does grow the
>    module's apparent API surface. Trivial to rename.
> 4. **`int()` rejects decimals, so `41250.5` in `recipients` reports as
>    "non-numeric".** That acceptance behavior is inherited from the baseline (which
>    also used `int()`), and I kept it so valid runs do not change. But my message
>    wording calls a decimal "non-numeric", which is not quite true.
> 5. **A truncated row reports as a value problem, not a structural one.**
>    `csv.DictReader` fills missing trailing fields with `None`, which my
>    `TypeError` catch turns into `data row 1: column 'opens' has a non-numeric
>    value (empty)`. Correct row and column, but it describes a short row as a bad
>    cell.
> 6. **I did not make the `--top` doc edits** you approved in Correction 3. They
>    document a flag that does not exist yet, so I held them for Part 2. Flagging in
>    case you wanted them landed now.
>
> ### 4. What I am unsure about
>
> 1. **The `ZeroDivisionError` above - needs your ruling.** Options: (a) display
>    `n/a` for CTOR/AOV when the denominator is zero, which keeps the analyst's
>    report per your Ruling 5 reasoning but invents a display convention you have
>    not approved and touches `format_summary`; (b) raise `CampaignReportError` with
>    a clear message, which is consistent with the rest of Part 1 but denies a
>    report over data that is arguably legitimate; (c) leave it. I lean (a), one
>    line, but it is your call, and I did not want to silently pick a formatting
>    convention after you specifically praised asking rather than assuming.
> 2. **Keep or drop `tests/expected_report.txt`?** It is the strongest guard on "do
>    not change the output of a valid run" and will keep guarding it through Part 2,
>    but it is an unplanned file and a golden file is a maintenance object.
> 3. **Helper naming** (item 3.3) - public or underscore-private?
> 4. **A UTF-8 BOM in the export would report `campaign_id` as a missing column**
>    rather than naming the BOM. The baseline would `KeyError` on the same file, so
>    this is still an improvement, and switching to `encoding="utf-8-sig"` would fix
>    it properly. I did not change the read encoding because that alters the parse
>    path and was not in scope.
> 5. **Message-wording fixes for items 3.4 and 3.5** are cheap if you want them,
>    but both would make messages longer, and I did not want to churn wording you
>    already corrected once.
>
> Nothing committed. Working tree holds one modified file and two new files, all on
> `feature/validation-and-top-n`.

*Supervisor verification of this report is tabulated in
`docs/02-checkpoint-records.md`, Checkpoint 2. All four checkable claims held,
including the claim that assigned the `ZeroDivisionError` to me rather than to
itself.*

---

## CP3 - Review with changes requested (prompt, abridged to the requests)

The full review prose is in `docs/03-code-review.md`. The six requests as issued:

> CHECKPOINT 3 REVIEW: CHANGES REQUESTED. Not a rejection. [...] My own held-out
> acceptance suite, which you have never seen and which was committed before you
> got the task, passes 9 of 10 against your code. The one failure, AC8, is MY bug,
> not yours. AC8 demanded --top 3 print the three campaigns in descending rpr
> order. At CP1 I ruled that --top selects and --sort orders. You implemented my
> ruling exactly. I never propagated that ruling into AC8, in the same edit where I
> amended AC6. Your output is correct; my acceptance test was stale.
>
> I ALSO FOUND ONE YOU MISSED: build_report(campaigns, top=0) raises
> ZeroDivisionError. positive_int guards the CLI, but top_campaigns and
> build_report are public and unguarded [...] Validation living only at the CLI
> boundary is fine until someone imports the module, which is exactly what your
> own tests do.
>
> I also reproduced your SORT_KEYS concern concretely, and it is worse than you
> described. Reassigning SORT_KEYS["rpr"] to ascending, a plausible display-only
> change, makes top_campaigns return the three WORST campaigns [...] Silently.
>
> REQUIRED CHANGES. I am explicitly unfencing format_summary and the formatting
> layer for this round. That fence existed to prevent gratuitous rewriting, not to
> force you to ship a crash.
>
> 1. Fix the zero-denominator crash, properly. Render "n/a" [...] Your CP2 option
>    (a), which I wrongly declined. My reasoning has changed because the facts
>    changed: this is no longer a pre-existing defect on unrelated input, it is a
>    defect your feature makes reachable on input that worked before.
> 2. Decouple selection from display [...] Add a test that would fail if someone
>    flipped the display lambda.
> 3. Guard the empty/zero selection path [...]
> 4. NUMERIC_KINDS[cast] -> use a .get fallback. An error reporter that raises
>    KeyError while reporting an error is the worst possible failure site.
> 5. Drop the TypeError from positive_int.
> 6. Fix "1 campaigns".
>
> Do NOT do anything else. [...] If byte-identity breaks for the 8-campaign
> fixture, stop and tell me rather than adjusting anything to compensate.
>
> [...] Also tell me if any of my six requests was wrong.

## CP3 - Agent remediation response (verbatim excerpts)

> All six changes are in. 97 tests pass, byte-identity holds.

On the guard, item 3:

> I chose **raising `ValueError`** over returning an empty report, in both
> `top_campaigns` (`count < 1`) and `build_report` (empty `campaigns`).
> `ValueError`, not `CampaignReportError`, deliberately: `CampaignReportError` is
> documented as user-fixable input and `main()` converts it to a polite exit 1,
> but a caller passing `top=0` is a programming error and should not be dressed up
> as bad user input.

Disclosing that it changed two of its own tests:

> **Two of my own tests failed and I changed them, not the code:**
> `test_no_campaign_is_summarized_without_being_listed` and
> `test_top_composes_with_a_skipped_zero_recipient_row` both asserted the literal
> `"1 campaigns"`. Item 6 is precisely what made them wrong, so I updated them to
> expect correct pluralization.

The zero-orders file with `--top 1`, which previously produced a traceback:

```
CAMPAIGN                     SENT        RECIPIENTS    OPEN   CLICK     CVR      REVENUE      RPR
-------------------------------------------------------------------------------------------------
Attribution Lag              2026-03-04      1,000   50.0%    5.0%    0.0%      $900.00    $0.90

1 campaign  |  1,000 recipients  |  $900.00 revenue
Blended open 50.0%  |  click 5.0%  |  CTOR 10.0%  |  CVR 0.0%
Revenue per recipient $0.90  |  AOV n/a
```

> Only the genuinely undefined metric degrades. CTOR, RPR, and revenue stay real
> numbers, and `CVR 0.0%` is correct rather than `n/a` because zero orders over
> 1,000 recipients is a defined rate of zero.

Answering "was any of my six requests wrong?", the correction to my reasoning:

> **Item 3's rationale is partly superseded by item 1, though the change is still
> worth making.** You justified it as "so `build_report` and `top_campaigns` cannot
> be made to divide by zero by a caller." I tested this by applying item 1 and then
> removing the item 3 guards: `build_report(campaigns, top=0)` does **not** divide
> by zero any more. [...] So item 1 already defuses the crash. What item 3 actually
> prevents is a *meaningless report* rather than an exception. I implemented it as
> you asked and I think raising is right, but the guard earns its place as "refuse
> to describe nothing", not "prevent a ZeroDivisionError".

And on its own invalid first verification of item 4:

> I initially tested with `Decimal`, which proved nothing: `decimal.InvalidOperation`
> is an `ArithmeticError`, so it escapes `except (TypeError, ValueError)` before the
> message is ever built. Retested with an unmapped cast that raises `ValueError` and
> got the correct fallback.

*Supervisor verification of this round is recorded in
`docs/02-checkpoint-records.md`, Checkpoint 3. I re-derived the byte-identity
claim, the 97-test count, the untouched baseline suite, the fixed crash, and the
correction to my own item-3 rationale.*
