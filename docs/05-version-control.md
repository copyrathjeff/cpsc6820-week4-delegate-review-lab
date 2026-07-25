# Version Control Record

The graph, the commit structure, and the attribution convention. Generated from
the repository, not transcribed.

## Branch strategy

`main` never received a direct commit from the agent. The agent worked only on
`feature/validation-and-top-n`, and that branch was cut from the **baseline**
commit `93335ad` rather than from the tip of `main`. That single choice is what
made "keep verification outside the agent's control" structural instead of
advisory: the task definition, the acceptance criteria, and the ten acceptance
tests were committed to `main` at `ed6ad9f`, which is not an ancestor of the
agent's branch, so those files were never present in its working tree. It could
not read them and could not edit them.

The topology below shows this directly. The branch leaves history at `93335ad`,
below every docs commit, and rejoins only at the merge.

## The graph

```
* 9a05ddb Consolidate duplicate golden output fixture
*   7f6408a Merge branch 'feature/validation-and-top-n'
|\  
| * 50959d0 Add --top N ranking by revenue per recipient
| * 0032474 Validate CSV input and fail with actionable messages
* | b5ab724 Record CP3 review, correct AC8, add review and reflection
* | f85d623 Record CP2 review: verified claims, five rulings
* | a8dc4cd Record CP1 plan review; refine AC6 to skip-and-warn
* | ed6ad9f Define delegated task, acceptance criteria, and checkpoints
|/  
* 93335ad Add campaign_report CLI baseline
```

## Commits, and what each one is for

| Commit | Author | Purpose |
|---|---|---|
| `93335ad` | Human | Baseline program. 198 lines, 5 tests. The thing being delegated against. |
| `ed6ad9f` | Human | Task, AC1-AC10, checkpoints, 10 held-out acceptance tests. Committed **before** the agent was given any instruction, so the timestamp is the evidence that the checkpoints were designed in advance. |
| `a8dc4cd` | Human | CP1 record. Three corrections, five rulings, AC6 tightened after I overrode the agent's plan. |
| `0032474` | **Agent**, reviewed | Part 1: input validation with actionable errors. Committed by me at the CP2 seam, after review. |
| `f85d623` | Human | CP2 record. Four self-reported claims independently verified; five rulings. |
| `50959d0` | **Agent**, reviewed | Part 2: `--top N`, plus the `n/a` fix that landing it safely required. |
| `b5ab724` | Human | CP3 record, code review, reflection. AC8 corrected. |
| `7f6408a` | Merge | `--no-ff`, so the branch topology survives in the history. |
| `9a05ddb` | Human | Consolidates the duplicate golden fixture the isolation caused. |

Two agent commits, five human commits, one merge. The agent's work landed in two
commits because I committed at each reviewed checkpoint rather than letting a
single large diff accumulate and then rewriting history to look tidy afterward.
Both agent commits pass the module's test: each has an honest one-line summary.

## Attribution convention

Every commit containing agent-authored code carries three trailers, and every
commit without it carries none:

```
Assisted-by: Claude Code (claude-sonnet-5), delegated agent, Part 1 of 2
Reviewed-by: Jeff Branyon <jeff@copyrath.com> at Checkpoint 2
Co-Authored-By: Claude <noreply@anthropic.com>
```

`Assisted-by` is the course convention and carries the audit detail: which model,
in what role, and which slice of the task. `Reviewed-by` names the human who
accepted it and the gate where that happened, which is the trailer that actually
assigns ownership. `Co-Authored-By` is the machine-readable git-standard form, so
the attribution is greppable by tooling that does not know about the other two.

The module says consistency is what makes attribution useful for later audit, so
the test is mechanical: `git log --grep="Assisted-by"` returns exactly the commits
containing agent-authored code, and nothing else.

```
$ git log --grep='Assisted-by' --oneline
7f6408a Merge branch 'feature/validation-and-top-n'
50959d0 Add --top N ranking by revenue per recipient
0032474 Validate CSV input and fail with actionable messages

$ git log --grep='Assisted-by' --invert-grep --oneline   # human-only commits
9a05ddb Consolidate duplicate golden output fixture
b5ab724 Record CP3 review, correct AC8, add review and reflection
f85d623 Record CP2 review: verified claims, five rulings
a8dc4cd Record CP1 plan review; refine AC6 to skip-and-warn
ed6ad9f Define delegated task, acceptance criteria, and checkpoints
93335ad Add campaign_report CLI baseline
```

## Verification at the merge commit

```
$ python3 -m pytest tests/ -q
108 passed in 0.40s

$ git diff 93335ad --stat -- tests/test_campaign_report.py   # baseline suite untouched
(no output: the 5 baseline tests were never modified)

$ python3 campaign_report.py data/campaigns.csv | diff - tests/golden/baseline_report.txt
(no output: valid-run output is byte-identical to the baseline)
```
