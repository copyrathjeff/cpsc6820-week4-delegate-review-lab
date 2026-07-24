"""Baseline tests for campaign_report.

These cover the happy path only. They exist so there is a suite to run before
and after any change to the module.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import campaign_report as cr  # noqa: E402

FIXTURE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data",
    "campaigns.csv",
)


def test_load_campaigns_reads_every_row():
    campaigns = cr.load_campaigns(FIXTURE)
    assert len(campaigns) == 8
    assert campaigns[0].campaign_id == "c1001"
    assert campaigns[0].recipients == 41250


def test_rate_metrics():
    c = cr.Campaign(
        campaign_id="x",
        name="Test",
        send_date="2026-01-01",
        recipients=1000,
        opens=400,
        clicks=50,
        orders=10,
        revenue=900.0,
    )
    assert c.open_rate == 0.4
    assert c.click_rate == 0.05
    assert c.click_to_open_rate == 0.125
    assert c.conversion_rate == 0.01
    assert c.revenue_per_recipient == 0.9
    assert c.average_order_value == 90.0


def test_totals_rolls_up():
    campaigns = cr.load_campaigns(FIXTURE)
    roll = cr.totals(campaigns)
    assert roll.recipients == sum(c.recipients for c in campaigns)
    assert round(roll.revenue, 2) == 166684.40


def test_build_report_includes_header_and_every_campaign():
    campaigns = cr.load_campaigns(FIXTURE)
    report = cr.build_report(campaigns)
    assert "CAMPAIGN" in report
    for c in campaigns:
        assert c.name[:28] in report


def test_sort_by_revenue_puts_biggest_first():
    campaigns = cr.load_campaigns(FIXTURE)
    report = cr.build_report(campaigns, sort_key="revenue")
    body = report.splitlines()[2]
    assert body.startswith("Last Chance Spring Sale")
