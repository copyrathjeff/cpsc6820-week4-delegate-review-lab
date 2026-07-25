# Reflection

**Where the checkpoints were, and what they caught.** Three gates. Plan approval
before any code. A stop after the validation layer. A full diff review before
merge. Each caught something. None caught what I built it to catch.

CP1 caught decisions, not errors. It wanted a blanket `except Exception` in `main()`
so no path could "leak a raw traceback." That meets my requirement and defeats its
point, since every real bug becomes a polite exit 1. It also planned to
fail the whole run on a zero-recipient row, where I wanted a skip and a warning.
Both would have been harder to argue about once buried in a 300-line diff. So a
five-line plan really does beat a 500-line diff, but not for the reason I expected.
I looked for mistakes and found judgment calls.

CP2 confirmed rather than detected. The agent made four checkable claims and all
four held up when I ran them myself. I could not have known that otherwise. And the
fourth was the claim it had the most reason to fudge. It blamed a bug on me
instead of itself.

CP3 earned its place. The agent told me its new `--top` flag made an old crash
reachable. Same CSV file: clean report without the flag, traceback with it. That
reversed my CP2 ruling that the bug was out of scope. The line was old, but which
files reached it was new.

**Failure modes.** Test gaming: none. It never touched the baseline tests. One of
its own tests failed and it told me the test was wrong, not the code, noting unasked
that a lazier fix would have edited the code to match. Scope creep: one small case,
a golden output file outside its plan, which it flagged itself. Confident
wrong turns: none. It asked instead, raising five gaps in my spec at CP1, including
one I planted.

Here is what I did not expect. The failures I was watching for showed up in me.
The `ZeroDivisionError` was in my own baseline. My AC6 tested zero recipients but
never zero opens, though `click_to_open_rate` divides by opens three lines away. And
AC8 failed against correct code, because it still held a spec my own CP1 ruling had
replaced. I edited AC6 for that reason in the same commit and never re-read the
other nine. I built this to catch the agent drifting. It caught me.

**How reviewing it felt different.** Cleaner, and more dangerous. The diff was
better organized than a classmate's first draft and better documented than my
baseline. That is the polish-beats-correctness problem the module warns about. But
the bigger trap was how honest it was about its own bugs. A list that thorough makes
you assume it is complete. It missed one: a public function left unguarded while the
CLI was guarded. I only found that by looking past its list. Reviewing a classmate,
I would also be managing how they feel. Here there was nothing to manage. That
sounds like a win. Mostly it means nothing slows you down when you should.

**Would I trust this on a real team?** Yes, with three conditions. Keep some tests
where the agent cannot reach them, since that is the only reason AC8 turned up. Put
the gates at points of no return, not on a timer, because the pre-merge gate caught
the real problem and the mid-run gate did not. And whoever merges owns it, because
"the AI wrote it" will not survive an incident review. One cost I missed: the agent
rebuilt a guard I had, because it could not see mine.
