"""Tests for --top N.

--top selects the N campaigns with the highest revenue per recipient, --sort
still decides the order that subset is displayed in, and the summary block
covers exactly the campaigns listed in the table above it.
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import campaign_report as cr  # noqa: E402

FIXTURE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data",
    "campaigns.csv",
)


def make(name, send_date, recipients, revenue):
    """Build a campaign whose revenue per recipient is revenue/recipients."""
    return cr.Campaign(
        campaign_id=name.lower(),
        name=name,
        send_date=send_date,
        recipients=recipients,
        opens=recipients // 2,
        clicks=recipients // 20,
        orders=recipients // 100,
        revenue=revenue,
    )


# Revenue per recipient runs 0.10 to 0.50, deliberately the reverse of both
# date order and alphabetical order, so a subset that is merely "the first N
# in file order" cannot pass these tests by accident.
CAMPAIGNS = [
    make("Alpha", "2026-01-01", 1000, 100.0),    # rpr 0.10
    make("Bravo", "2026-01-02", 1000, 200.0),    # rpr 0.20
    make("Charlie", "2026-01-03", 1000, 300.0),  # rpr 0.30
    make("Delta", "2026-01-04", 1000, 400.0),    # rpr 0.40
    make("Echo", "2026-01-05", 1000, 500.0),     # rpr 0.50
]


def table_rows(report):
    """Return just the campaign rows: everything after the header underline."""
    rows = []
    for line in report.splitlines()[2:]:
        if line == "":
            break
        rows.append(line)
    return rows


def row_names(report):
    """Return the campaign name from each table row, in display order."""
    return [row.split("  ")[0].strip() for row in table_rows(report)]


def summary_lines(report):
    """Return the summary block, which is everything after the blank line."""
    lines = report.splitlines()
    return lines[lines.index("") + 1:]


# --- selection -----------------------------------------------------------


def test_top_limits_the_table_to_n_rows():
    assert len(table_rows(cr.build_report(CAMPAIGNS, top=3))) == 3
    assert len(table_rows(cr.build_report(CAMPAIGNS, top=1))) == 1


def test_top_picks_the_highest_revenue_per_recipient():
    report = cr.build_report(CAMPAIGNS, sort_key="rpr", top=3)
    assert row_names(report) == ["Echo", "Delta", "Charlie"]


def test_top_one_picks_the_single_best_campaign():
    report = cr.build_report(CAMPAIGNS, top=1)
    assert row_names(report) == ["Echo"]


def test_top_excludes_the_worst_campaigns():
    report = cr.build_report(CAMPAIGNS, top=2)
    names = row_names(report)
    assert "Alpha" not in names
    assert "Bravo" not in names
    assert "Charlie" not in names


def test_top_selects_by_rpr_not_by_raw_revenue():
    """A small campaign with a great rate should beat a big weak one."""
    small_and_efficient = make("Efficient", "2026-02-01", 100, 90.0)  # rpr 0.90
    big_and_weak = make("Sprawling", "2026-02-02", 100000, 1000.0)    # rpr 0.01
    report = cr.build_report([big_and_weak, small_and_efficient], top=1)
    assert row_names(report) == ["Efficient"]


def test_top_campaigns_helper_orders_best_first():
    best = cr.top_campaigns(CAMPAIGNS, 5)
    rprs = [c.revenue_per_recipient for c in best]
    assert rprs == sorted(rprs, reverse=True)


# --- composition with --sort ---------------------------------------------


def test_top_composes_with_sort_date():
    """Same three campaigns as --sort rpr, displayed oldest first."""
    report = cr.build_report(CAMPAIGNS, sort_key="date", top=3)
    assert row_names(report) == ["Charlie", "Delta", "Echo"]


def test_top_composes_with_sort_name():
    report = cr.build_report(CAMPAIGNS, sort_key="name", top=3)
    assert row_names(report) == ["Charlie", "Delta", "Echo"]


def test_sort_changes_order_but_not_membership():
    memberships = [
        set(row_names(cr.build_report(CAMPAIGNS, sort_key=key, top=3)))
        for key in sorted(cr.SORT_KEYS)
    ]
    assert all(names == memberships[0] for names in memberships)
    assert memberships[0] == {"Charlie", "Delta", "Echo"}


# --- summary recomputes over the subset ----------------------------------


def test_summary_counts_only_the_selected_campaigns():
    report = cr.build_report(CAMPAIGNS, top=3)
    assert "3 campaigns" in summary_lines(report)[0]


def test_summary_totals_only_the_selected_campaigns():
    report = cr.build_report(CAMPAIGNS, top=3)
    first = summary_lines(report)[0]
    # Charlie + Delta + Echo = 300 + 400 + 500 on 3,000 recipients.
    assert "3,000 recipients" in first
    assert "$1,200.00 revenue" in first
    assert "$1,500.00" not in first


def test_summary_rpr_reflects_the_subset_not_the_whole_file():
    subset = summary_lines(cr.build_report(CAMPAIGNS, top=3))[-1]
    everything = summary_lines(cr.build_report(CAMPAIGNS))[-1]
    assert "Revenue per recipient $0.40" in subset
    assert "Revenue per recipient $0.30" in everything


def test_no_campaign_is_summarized_without_being_listed():
    """The reconciliation guarantee: summary count equals rows printed."""
    for count in range(1, len(CAMPAIGNS) + 1):
        report = cr.build_report(CAMPAIGNS, top=count)
        noun = "campaign" if count == 1 else "campaigns"
        assert summary_lines(report)[0].startswith(f"{count} {noun}")
        assert len(table_rows(report)) == count


# --- boundaries ----------------------------------------------------------


def test_top_larger_than_the_list_returns_everything():
    report = cr.build_report(CAMPAIGNS, top=99)
    assert len(table_rows(report)) == len(CAMPAIGNS)
    assert "5 campaigns" in summary_lines(report)[0]


def test_top_equal_to_the_count_matches_an_untrimmed_report():
    assert cr.build_report(CAMPAIGNS, top=len(CAMPAIGNS)) == cr.build_report(
        CAMPAIGNS
    )


def test_top_none_is_the_default_and_trims_nothing():
    assert cr.build_report(CAMPAIGNS, top=None) == cr.build_report(CAMPAIGNS)


def test_build_report_does_not_mutate_its_input():
    before = list(CAMPAIGNS)
    cr.build_report(CAMPAIGNS, sort_key="revenue", top=2)
    assert CAMPAIGNS == before


# --- selection must not depend on the display constants ------------------


def test_top_selection_ignores_the_rpr_display_lambda(monkeypatch):
    """Flipping the rpr display sort must not change which campaigns win.

    This fails if top_campaigns ever goes back to reading SORT_KEYS["rpr"]:
    an ascending display lambda would silently select the worst campaigns.
    """
    flipped = dict(cr.SORT_KEYS)
    flipped["rpr"] = lambda c: c.revenue_per_recipient  # ascending
    monkeypatch.setattr(cr, "SORT_KEYS", flipped)

    assert [c.name for c in cr.top_campaigns(CAMPAIGNS, 3)] == [
        "Echo",
        "Delta",
        "Charlie",
    ]
    assert row_names(cr.build_report(CAMPAIGNS, top=3)) == [
        "Charlie",
        "Delta",
        "Echo",
    ]


def test_top_selection_survives_removing_rpr_from_sort_keys(monkeypatch):
    """Selection must not even require an "rpr" display key to exist."""
    without_rpr = {k: v for k, v in cr.SORT_KEYS.items() if k != "rpr"}
    monkeypatch.setattr(cr, "SORT_KEYS", without_rpr)
    assert [c.name for c in cr.top_campaigns(CAMPAIGNS, 2)] == ["Echo", "Delta"]


# --- empty and zero selections cannot divide by zero ---------------------


@pytest.mark.parametrize("count", [0, -1, -99])
def test_top_campaigns_rejects_a_count_below_one(count):
    with pytest.raises(ValueError, match="1 or more"):
        cr.top_campaigns(CAMPAIGNS, count)


@pytest.mark.parametrize("count", [0, -1])
def test_build_report_rejects_a_top_below_one(count):
    """Previously ZeroDivisionError: an empty selection reached totals()."""
    with pytest.raises(ValueError, match="1 or more"):
        cr.build_report(CAMPAIGNS, top=count)


def test_build_report_rejects_an_empty_campaign_list():
    with pytest.raises(ValueError, match="zero campaigns"):
        cr.build_report([])


def test_zero_selection_does_not_raise_zerodivisionerror():
    """The guard must be a clear ValueError, not the old crash."""
    for call in (
        lambda: cr.build_report(CAMPAIGNS, top=0),
        lambda: cr.top_campaigns(CAMPAIGNS, 0),
        lambda: cr.build_report([]),
    ):
        with pytest.raises(ValueError):
            call()


# --- argparse rejects bad values (usage error, exit 2) -------------------


@pytest.mark.parametrize("bad", ["0", "-1", "-99"])
def test_top_below_one_is_a_usage_error(bad, capsys):
    with pytest.raises(SystemExit) as excinfo:
        cr.parse_args([FIXTURE, "--top", bad])
    assert excinfo.value.code == 2
    assert "--top" in capsys.readouterr().err


@pytest.mark.parametrize("bad", ["abc", "2.5", ""])
def test_non_integer_top_is_a_usage_error(bad, capsys):
    with pytest.raises(SystemExit) as excinfo:
        cr.parse_args([FIXTURE, "--top", bad])
    assert excinfo.value.code == 2
    assert "--top" in capsys.readouterr().err


def test_positive_int_accepts_one_and_above():
    assert cr.positive_int("1") == 1
    assert cr.positive_int("25") == 25


def test_top_defaults_to_none():
    assert cr.parse_args([FIXTURE]).top is None
    assert cr.parse_args([FIXTURE, "--top", "3"]).top == 3


# --- end to end through main() -------------------------------------------


def test_cli_top_prints_three_rows_and_a_matching_summary(capsys):
    assert cr.main([FIXTURE, "--top", "3"]) == 0
    out = capsys.readouterr().out
    assert len(table_rows(out)) == 3
    assert "3 campaigns" in summary_lines(out)[0]


def test_cli_top_selects_the_three_best_by_rpr(capsys):
    cr.main([FIXTURE, "--top", "3"])
    names = row_names(capsys.readouterr().out)
    assert set(names) == {
        "Last Chance Spring Sale",
        "Bundle + Save 20%",
        "Mothers Day Gift Guide",
    }


def test_cli_top_with_sort_reorders_the_same_three(capsys):
    cr.main([FIXTURE, "--top", "3", "--sort", "rpr"])
    # rpr: 0.85458, 0.76138, 0.67660 respectively.
    assert row_names(capsys.readouterr().out) == [
        "Last Chance Spring Sale",
        "Bundle + Save 20%",
        "Mothers Day Gift Guide",
    ]


def test_cli_top_is_silent_on_stderr(capsys):
    cr.main([FIXTURE, "--top", "2"])
    assert capsys.readouterr().err == ""


# --- composition with Part 1 validation ----------------------------------


def test_top_composes_with_a_skipped_zero_recipient_row(tmp_path, capsys):
    header = "campaign_id,name,send_date,recipients,opens,clicks,orders,revenue"
    path = tmp_path / "mixed.csv"
    path.write_text(
        "\n".join(
            [
                header,
                "c1,Good One,2026-03-04,1000,500,50,10,900.00",
                "c2,Dead Segment,2026-03-11,0,0,0,0,0.00",
                "c3,Good Two,2026-03-18,1000,500,50,10,100.00",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    assert cr.main([str(path), "--top", "1"]) == 0
    captured = capsys.readouterr()
    assert row_names(captured.out) == ["Good One"]
    assert summary_lines(captured.out)[0].startswith("1 campaign  |")
    assert "Dead Segment" in captured.err


def test_top_still_reports_bad_input_before_trimming(tmp_path, capsys):
    header = "campaign_id,name,send_date,recipients,opens,clicks,orders,revenue"
    path = tmp_path / "bad.csv"
    path.write_text(
        header + "\nc1,A,2026-03-04,1000,500,oops,10,900.00\n", encoding="utf-8"
    )
    assert cr.main([str(path), "--top", "1"]) == 1
    assert "Error: " in capsys.readouterr().err
