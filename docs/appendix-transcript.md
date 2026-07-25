# Appendix: Prompts and Transcript

Setup: Claude Code (CLI agent) as supervising session, driving a **delegated
sub-agent** with file read/write and shell access. The sub-agent held its own
context across all three checkpoints, so each gate resumed the same worker rather
than briefing a fresh one. Between gates it planned, edited, and ran its own
tests with no human prompt per step.

Reproduced verbatim. Tool-call chatter and file dumps are elided where marked;
nothing in the agent's prose is edited, including the parts where it is wrong.

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
