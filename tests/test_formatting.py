"""Zero-denominator rendering and summary wording.

A rate whose denominator is zero is undefined, not zero, so it renders as
"n/a" instead of raising ZeroDivisionError or printing a misleading 0.00.
These cases became reachable through --top, which recomputes the summary over
a selected subset, so a subset can have no opens or no orders even when the
whole file does.
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import campaign_report as cr  # noqa: E402

HEADER = "campaign_id,name,send_date,recipients,opens,clicks,orders,revenue"


def campaign(name="Test", recipients=1000, opens=500, clicks=50, orders=10,
             revenue=900.0, send_date="2026-03-04"):
    return cr.Campaign(
        campaign_id=name.lower().replace(" ", ""),
        name=name,
        send_date=send_date,
        recipients=recipients,
        opens=opens,
        clicks=clicks,
        orders=orders,
        revenue=revenue,
    )


def summary_lines(report):
    lines = report.splitlines()
    return lines[lines.index("") + 1:]


# --- ratio ---------------------------------------------------------------


def test_ratio_divides_normally():
    assert cr.ratio(1, 4) == 0.25


def test_ratio_returns_none_for_a_zero_denominator():
    assert cr.ratio(900.0, 0) is None
    assert cr.ratio(0, 0) is None


def test_ratio_does_not_report_undefined_as_zero():
    """Undefined and zero are different claims and must not be conflated."""
    undefined = cr.ratio(900.0, 0)
    genuinely_zero = cr.ratio(0, 100)
    assert undefined is None
    assert genuinely_zero == 0.0
    assert genuinely_zero is not None


# --- formatters ----------------------------------------------------------


def test_pct_renders_none_as_not_applicable():
    assert cr.pct(None) == "n/a"


def test_money_renders_none_as_not_applicable():
    assert cr.money(None) == "n/a"


def test_formatters_are_unchanged_for_real_values():
    assert cr.pct(0.4) == "40.0%"
    assert cr.money(1234.5) == "$1,234.50"


# --- campaign properties -------------------------------------------------


def test_click_to_open_rate_is_none_with_no_opens():
    assert campaign(opens=0, clicks=0).click_to_open_rate is None


def test_average_order_value_is_none_with_no_orders():
    assert campaign(orders=0, revenue=900.0).average_order_value is None


def test_recipient_rates_are_none_with_no_recipients():
    empty = campaign(recipients=0, opens=0, clicks=0, orders=0, revenue=0.0)
    assert empty.open_rate is None
    assert empty.click_rate is None
    assert empty.conversion_rate is None
    assert empty.revenue_per_recipient is None


def test_defined_rates_still_compute():
    c = campaign(recipients=1000, opens=400, clicks=50, orders=10, revenue=900.0)
    assert c.open_rate == 0.4
    assert c.click_to_open_rate == 0.125
    assert c.average_order_value == 90.0


# --- summary rendering ---------------------------------------------------


def test_summary_renders_ctor_as_na_with_no_opens():
    report = cr.format_summary([campaign(opens=0, clicks=0)])
    assert "CTOR n/a" in report[report.index("Blended"):]


def test_summary_renders_aov_as_na_with_no_orders():
    report = cr.format_summary([campaign(orders=0, revenue=900.0)])
    assert "AOV n/a" in report


def test_summary_with_no_orders_does_not_claim_zero_aov():
    report = cr.format_summary([campaign(orders=0, revenue=900.0)])
    assert "AOV $0.00" not in report


def test_summary_does_not_raise_on_an_all_zero_campaign():
    report = cr.format_summary(
        [campaign(recipients=1000, opens=0, clicks=0, orders=0, revenue=0.0)]
    )
    assert "CTOR n/a" in report
    assert "AOV n/a" in report


# --- per-row rendering ---------------------------------------------------


def test_format_row_renders_na_for_a_zero_recipient_campaign():
    row = cr.format_row(
        campaign(recipients=0, opens=0, clicks=0, orders=0, revenue=0.0)
    )
    assert row.count("n/a") == 4


def test_format_row_keeps_column_alignment_with_na():
    """n/a must sit inside the same fixed-width columns as a real value."""
    normal = cr.format_row(campaign())
    degraded = cr.format_row(
        campaign(recipients=0, opens=0, clicks=0, orders=0, revenue=0.0)
    )
    assert len(normal) == len(degraded)


# --- summary wording -----------------------------------------------------


def test_one_campaign_is_singular():
    assert cr.format_summary([campaign()]).splitlines()[1].startswith(
        "1 campaign  |"
    )


def test_two_campaigns_are_plural():
    line = cr.format_summary([campaign(), campaign("Other")]).splitlines()[1]
    assert line.startswith("2 campaigns  |")


def test_singular_wording_does_not_leak_into_plural_counts():
    for n in (2, 3, 8):
        line = cr.format_summary([campaign() for _ in range(n)]).splitlines()[1]
        assert line.startswith(f"{n} campaigns  |")


# --- end to end: the file that --top used to crash on --------------------


@pytest.fixture
def attribution_lag_csv(tmp_path):
    """Highest-rpr campaign has revenue but no orders, so a top-1 subset
    has a zero AOV denominator even though the whole file does not."""
    path = tmp_path / "no_orders.csv"
    path.write_text(
        "\n".join(
            [
                HEADER,
                "c1,Attribution Lag,2026-03-04,1000,500,50,0,900.00",
                "c2,Normal Send,2026-03-11,1000,500,50,10,100.00",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    return str(path)


def test_whole_file_still_reports_cleanly(attribution_lag_csv, capsys):
    assert cr.main([attribution_lag_csv]) == 0
    out = capsys.readouterr().out
    assert "AOV $100.00" in out
    assert "2 campaigns" in out


def test_top_one_no_longer_crashes(attribution_lag_csv, capsys):
    assert cr.main([attribution_lag_csv, "--top", "1"]) == 0
    captured = capsys.readouterr()
    assert "AOV n/a" in captured.out
    assert "1 campaign  |" in captured.out
    assert captured.err == ""


def test_top_one_still_reports_the_rates_that_are_defined(
    attribution_lag_csv, capsys
):
    """Only the undefined metric degrades; the rest stay real numbers."""
    cr.main([attribution_lag_csv, "--top", "1"])
    out = capsys.readouterr().out
    assert "CTOR 10.0%" in out
    assert "Revenue per recipient $0.90" in out
    assert "$900.00 revenue" in out


def test_file_with_no_engagement_at_all_reports_instead_of_crashing(
    tmp_path, capsys
):
    """The original pre-existing crash: zero opens and zero orders overall."""
    path = tmp_path / "no_engagement.csv"
    path.write_text(
        HEADER + "\nc1,No Engagement,2026-03-04,1000,0,0,0,0.00\n",
        encoding="utf-8",
    )
    assert cr.main([str(path)]) == 0
    out = capsys.readouterr().out
    assert "CTOR n/a" in out
    assert "AOV n/a" in out
    assert "1 campaign  |" in out
