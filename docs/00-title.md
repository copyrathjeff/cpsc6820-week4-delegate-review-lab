<h1 class="title">Delegate &amp; Review Lab</h1>

<p class="subtitle">Assignment 4.1 &middot; Agentic AI &amp; Collaborating with AI on Software Teams</p>

<div class="byline">
<strong>Jeff Branyon</strong> &middot; CPSC 6820, AI-Receptive Software Development &middot; Summer 2026<br>
Dr. Paige Anne Rodeghero &middot; Repository: <code>week4-delegate-review-lab</code>
</div>

**Setup used: agentic, not simulated.** Claude Code (terminal/CLI agent), with a
supervising session on `claude-opus-5` driving a **delegated sub-agent** on
`claude-sonnet-5` as the worker. The sub-agent had file read/write and shell
access and retained its own context across all three checkpoints, so each gate
resumed the same worker rather than briefing a fresh one. Between gates it
planned, edited, and ran its own tests with no human prompt per step.

## Contents

1. **Task Definition, Acceptance Criteria, and Checkpoints.** The task as given,
   AC1 through AC10, the three gates, and why the acceptance tests were kept
   structurally out of the agent's reach.
2. **Checkpoint Records.** What each gate caught, what I corrected, what I got
   wrong, and which agent claims I re-derived rather than believed.
3. **Code Review.** Seven comments, three blocking, one beyond correctness. Every
   reproducible defect claim carries its reproduction.
4. **Reflection.** 598 words.
5. **Version Control Record.** Branch topology, commit structure, and attribution
   convention, generated from the repository.
6. **Appendix: Prompts and Transcript.** Every prompt and every agent response,
   verbatim, including where the agent was wrong and where I was.
7. **CPSC 6820 Literature Component.** The additional graduate requirement, on
   Mozannar et al. (CHI 2024). Included here as a final labeled part rather than a
   separate file, since only one Canvas item was available. It is self-contained and
   can be graded on its own.

## Result in brief

The agent's work landed in two reviewed commits after three gates and one round of
requested changes. 108 tests pass at the merge commit: 5 baseline tests unmodified
since `93335ad`, 92 written by the agent, and 11 acceptance tests of mine. Ten of
those eleven were committed at `ed6ad9f` before the agent received the task and
were hidden from its branch; the eleventh was added at CP3, when AC8 was split in
two. Valid-run output is byte-identical to the pre-change baseline.

The three most useful findings were mine, not the agent's. A latent
`ZeroDivisionError` in my own baseline. An acceptance criterion (AC6) that tested
zero *recipients* and never zero *opens*, three lines from the property that
divides by opens. And AC8, which failed against **correct** code because it
encoded a specification my own CP1 ruling had superseded, in the very same edit
where I amended AC6 for exactly that reason. Section 2 records all three.
