<div class="page-break"></div>

# AI Use Disclosure

Placed here per the assignment's instruction to disclose any AI use beyond the
documented activities at the end of the report.

The lab itself is AI-assisted by design and documented throughout. The delegated agent
(`claude-sonnet-5`, run through Claude Code) authored the validation layer, the
`--top N` feature, and 92 of the 108 tests. That work is attributed per commit with
`Assisted-by` trailers, recoverable with `git log --grep='^Assisted-by:'`, and its
prompts and responses are reproduced in the appendix.

Beyond that, disclosure is owed on the written analysis. A supervising Claude Code
session (`claude-opus-5`) drafted the prose in this report, including the checkpoint
records, the code review comments, the reflection, the task definition, and the
literature summary, and it ran the verification commands whose output is quoted
throughout. That goes further than the grammar polishing the assignment permits for
those sections, so it is stated plainly here rather than described as editing.

The decisions in the lab were mine. The base program and the checkpoint design. The
CP1 ruling on zero-recipient rows, where I overrode both the agent's proposed hard
failure and the supervising session's recommendation, recorded in commit `a8dc4cd`
before any agent code existed. The reversal of my own CP2 scope ruling once `--top`
changed the facts at CP3. The six changes required before merge. And the editorial
calls on length, register, and what shipped.

Every factual claim in this report was verified by execution against the repository,
and the commands and outputs are included so that each one is checkable rather than
taken on trust.
