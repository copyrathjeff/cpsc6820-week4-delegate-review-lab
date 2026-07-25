"""Acceptance tests for the Week 4 delegated task (AC1-AC10).

Written by the human supervisor BEFORE the agent received the task, and
committed to `main` only. The agent's branch was cut from the earlier baseline
commit, so these files were never in its working tree: it could neither read
them nor edit them. They are applied at Checkpoint 3.

Every test drives the CLI as a subprocess. That is deliberate. Test gaming is a
named failure mode, and an agent can always satisfy an internal unit test by
changing the internals the test asserts against. It cannot satisfy an
observable-behavior test without the behavior actually being correct.
"""

import ast
import os
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(REPO, "campaign_report.py")
FIXTURE = os.path.join(REPO, "data", "campaigns.csv")
GOLDEN = os.path.join(REPO, "tests", "golden", "baseline_report.txt")

HEADER = "campaign_id,name,send_date,recipients,opens,clicks,orders,revenue"
GOOD_ROW = "c1,Alpha,2026-01-01,1000,400,50,10,900.00"


def run_cli(*args):
    """Run the CLI and return (exit_code, stdout, stderr)."""
    proc = subprocess.run(
        [sys.executable, SCRIPT, *args],
        capture_output=True,
        text=True,
        cwd=REPO,
    )
    return proc.returncode, proc.stdout, proc.stderr


def write_csv(tmp_path, *lines):
    """Write a CSV with the standard header plus *lines*; return its path."""
    path = tmp_path / "input.csv"
    path.write_text("\n".join([HEADER, *lines]) + "\n", encoding="utf-8")
    return str(path)


def campaign_rows(stdout):
    """Extract just the campaign table body from a report."""
    lines = stdout.splitlines()
    start = next(i for i, ln in enumerate(lines) if set(ln.strip()) == {"-"}) + 1
    body = []
    for line in lines[start:]:
        if not line.strip():
            break
        body.append(line)
    return body


def assert_clean_failure(code, stderr):
    """A failure must be non-zero, explained on stderr, and not a traceback."""
    assert code != 0, "expected a non-zero exit code"
    assert stderr.strip(), "expected an explanation on stderr"
    assert "Traceback" not in stderr, f"leaked a traceback:\n{stderr}"


# --- AC1 -------------------------------------------------------------------


def test_ac1_valid_run_is_byte_identical_to_golden():
    code, out, err = run_cli(FIXTURE)
    assert code == 0, err
    with open(GOLDEN, encoding="utf-8") as handle:
        assert out == handle.read()


# --- AC2-AC7: error handling ----------------------------------------------


def test_ac2_missing_file_names_the_path():
    code, _, err = run_cli("data/does_not_exist.csv")
    assert_clean_failure(code, err)
    assert "does_not_exist.csv" in err


def test_ac3_missing_required_column_is_named(tmp_path):
    path = tmp_path / "no_revenue.csv"
    path.write_text(
        "campaign_id,name,send_date,recipients,opens,clicks,orders\n"
        "c1,Alpha,2026-01-01,1000,400,50,10\n",
        encoding="utf-8",
    )
    code, _, err = run_cli(str(path))
    assert_clean_failure(code, err)
    assert "revenue" in err


def test_ac4_non_numeric_value_names_row_and_column(tmp_path):
    """Test case 1. A generic 'bad CSV' message fails this on specificity."""
    path = write_csv(
        tmp_path,
        GOOD_ROW,
        "c2,Beta,2026-01-08,forty-thousand,400,50,10,900.00",
    )
    code, _, err = run_cli(path)
    assert_clean_failure(code, err)
    assert "recipients" in err, f"should name the column:\n{err}"
    assert "2" in err, f"should name the offending row:\n{err}"


def test_ac5_negative_value_is_rejected(tmp_path):
    path = write_csv(tmp_path, "c1,Alpha,2026-01-01,1000,400,50,10,-900.00")
    code, _, err = run_cli(path)
    assert_clean_failure(code, err)
    assert "revenue" in err


def test_ac6_zero_recipients_is_skipped_with_a_warning(tmp_path):
    """AC6, as refined by the supervisor's decision at Checkpoint 1.

    The original wording accepted either a hard failure or a safe render. At CP1
    I chose skip-and-continue over the agent's proposed hard failure, on the
    condition that the skip is announced: a report that quietly describes fewer
    campaigns than the file contains is how a wrong number reaches a client
    deck. Tightened here before the agent wrote any code, and without the agent
    ever seeing this file.
    """
    path = write_csv(tmp_path, GOOD_ROW, "c2,Beta,2026-01-08,0,0,0,0,0.00")
    code, out, err = run_cli(path)
    assert "ZeroDivisionError" not in err
    assert "Traceback" not in err
    assert code == 0, f"the run should still succeed:\n{err}"
    assert "Alpha" in out, "the valid campaign should still be reported"
    body = "\n".join(campaign_rows(out))
    assert "Beta" not in body, "the 0-recipient row must be left out of the table"
    assert err.strip(), "the skip must be announced on stderr, not silent"
    assert "Beta" in err or "c2" in err, f"the warning should name the row:\n{err}"


def test_ac7_header_only_csv_says_no_campaigns(tmp_path):
    path = write_csv(tmp_path)
    code, _, err = run_cli(path)
    assert_clean_failure(code, err)


# --- AC8-AC9: --top N ------------------------------------------------------


TOP_3_BY_RPR = ("Last Chance Spring Sale", "Bundle + Save 20%", "Mothers Day Gift Guide")
TOP_3_IN_DATE_ORDER = ["Bundle + Save 20%", "Last Chance Spring Sale", "Mothers Day Gift Guide"]


def test_ac8_top_3_selects_by_revenue_per_recipient():
    """Test case 2, corrected at CP3. THE ORIGINAL VERSION OF THIS TEST WAS WRONG.

    As first written it demanded the three rows appear in descending RPR order.
    That contradicted my own CP1 ruling that --top selects while --sort orders,
    recorded in commit a8dc4cd, before any --top code existed. The agent
    implemented the ruling; this test still encoded the superseded spec, so it
    failed against correct code. I amended AC6 for exactly this reason in that
    same commit and did not notice AC8 needed the same treatment.

    Corrected to assert what the ruling actually requires: the right three
    campaigns get selected by RPR, then displayed in --sort order (date by
    default). Ranking by raw revenue would still select a different third
    campaign, so the selection assertion keeps its teeth.
    """
    code, out, err = run_cli(FIXTURE, "--top", "3")
    assert code == 0, err
    rows = campaign_rows(out)
    assert len(rows) == 3, f"expected exactly 3 rows, got {len(rows)}:\n{out}"

    names = [r.split("  ")[0].strip() for r in rows]
    assert set(names) == set(TOP_3_BY_RPR), f"wrong campaigns selected: {names}"
    assert names == TOP_3_IN_DATE_ORDER, f"default order should be by date: {names}"


def test_ac8b_top_composes_with_sort_rpr():
    """The descending-RPR order the original AC8 demanded is reachable, via --sort."""
    code, out, err = run_cli(FIXTURE, "--top", "3", "--sort", "rpr")
    assert code == 0, err
    names = [r.split("  ")[0].strip() for r in campaign_rows(out)]
    assert names == list(TOP_3_BY_RPR), f"expected descending RPR order: {names}"


def test_ac9_invalid_top_values_are_rejected():
    for bad in ("0", "-1"):
        code, _, err = run_cli(FIXTURE, "--top", bad)
        assert code != 0, f"--top {bad} should be rejected"
        assert "Traceback" not in err


# --- AC10 ------------------------------------------------------------------


def test_ac10_standard_library_only():
    with open(SCRIPT, encoding="utf-8") as handle:
        tree = ast.parse(handle.read())
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(a.name.split(".")[0] for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            imported.add(node.module.split(".")[0])
    outside = imported - sys.stdlib_module_names
    assert not outside, f"non-stdlib imports: {sorted(outside)}"
