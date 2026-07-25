# Reflection

**Where the checkpoints were, and what they caught.** Three gates: plan approval
before any code, a mid-implementation stop after the validation layer, and a full
diff review before merge. Each caught something. None caught what I designed it to
catch.

CP1 caught decisions rather than errors. Nothing in the plan was broken. The gate
surfaced two choices I disagreed with: a blanket `except Exception` proposed so
"no code path can ever leak a raw traceback," which would satisfy my requirement
while destroying its purpose; and a hard failure on a zero-recipient row where I
wanted skip-and-warn. Both would have been costlier to argue once load-bearing in a
300-line diff. The module's claim that a five-line plan beats a
500-line diff held, but not as I assumed: I expected mistakes and got judgment.

CP2's honest verdict is that it confirmed rather than detected. All four checkable
claims in its self-report survived independent re-derivation. I could not have
known that without checking, and the fourth was the one it had most incentive to
get wrong, since it assigned a bug to me rather than itself.

CP3 earned its place. The agent disclosed that `--top` widened the reachability of
a pre-existing zero-denominator crash: the same CSV gave a clean report without the
flag, a traceback with it. That reversed my CP2 ruling that the bug was out of
scope. The line of code was old, but which inputs reached it was new, and that made
it this change's problem.

**Failure modes.** Test gaming: none. The baseline suite was never touched, and
when one of its own tests failed it reported the failure as its wrong expectation
rather than the code, noting unprompted that a sloppier fix would have "fixed" the
code to match. Scope creep: one instance, mild and self-disclosed, a golden output
file outside its approved plan. Confident wrong turns: none, because it asked
instead, surfacing five ambiguities at CP1 including one I planted.

The uncomfortable finding is that the failure modes I was policing showed up in me.
The `ZeroDivisionError` was in my baseline. My AC6 tested zero recipients and never
zero opens, three lines from the property that divides by opens. And AC8 failed
against correct code because it encoded a specification my own CP1 ruling had
superseded, in the same edit where I amended AC6 for that reason. I built a process
to catch the agent's drift and it caught mine.

**How reviewing it felt different.** Cleaner and more dangerous. The diff arrived
better organized than a colleague's first draft and better documented than my own
baseline, the polish-exceeding-correctness signature the module warns about. The
subtler hazard was the candid self-report: a thorough-sounding list of an author's
own defects invites you to treat it as complete, and the one blocking bug it
missed, a public function unguarded where the CLI was guarded, I found only by
looking past that list. Reviewing a classmate, I would also be managing a person.
Here the entire cost was cognitive, which sounds like an advantage and mostly means
nothing slows you down at the moment you should be slowing down.

**Would I trust this on a real team?** Yes, under three conditions. Verification the
agent cannot reach, since hiding my acceptance tests is why AC8 surfaced at all.
Gates at points of no return rather than at intervals, because the mid-run gate
mostly confirmed while the pre-merge gate caught the regression. And whoever merges
owns it, because "the AI wrote it" survives no incident review. One cost I failed
to price: concealing the tests made the agent rebuild a guard I had.
