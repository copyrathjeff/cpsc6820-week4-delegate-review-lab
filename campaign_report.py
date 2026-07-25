#!/usr/bin/env python3
"""Summarize email campaign performance from a CSV export.

Reads a CSV of campaign sends, computes the standard engagement and revenue
rates for each one, and prints a per-campaign table plus an account-level
summary. Intended for a quick sanity check on a platform export before the
numbers go into a client report.

Usage:
    python campaign_report.py data/campaigns.csv
    python campaign_report.py data/campaigns.csv --sort rpr
"""

from __future__ import annotations

import argparse
import csv
import sys
from dataclasses import dataclass

EXPECTED_COLUMNS = (
    "campaign_id",
    "name",
    "send_date",
    "recipients",
    "opens",
    "clicks",
    "orders",
    "revenue",
)

# The numeric columns and the type each is read as. Order decides which
# problem is reported first when a single row has more than one.
NUMERIC_COLUMNS = (
    ("recipients", int),
    ("opens", int),
    ("clicks", int),
    ("orders", int),
    ("revenue", float),
)


class CampaignReportError(Exception):
    """A problem with the input that the user can act on.

    Raised for bad input only, never for a defect in this module. main()
    turns it into a one-line stderr message and a non-zero exit code. Any
    other exception is a bug and is deliberately left to raise a traceback.
    """


@dataclass
class Campaign:
    """One campaign send, plus the rate metrics derived from it."""

    campaign_id: str
    name: str
    send_date: str
    recipients: int
    opens: int
    clicks: int
    orders: int
    revenue: float

    @property
    def open_rate(self) -> float:
        return self.opens / self.recipients

    @property
    def click_rate(self) -> float:
        return self.clicks / self.recipients

    @property
    def click_to_open_rate(self) -> float:
        return self.clicks / self.opens

    @property
    def conversion_rate(self) -> float:
        return self.orders / self.recipients

    @property
    def revenue_per_recipient(self) -> float:
        return self.revenue / self.recipients

    @property
    def average_order_value(self) -> float:
        return self.revenue / self.orders


SORT_KEYS = {
    "date": lambda c: c.send_date,
    "name": lambda c: c.name.lower(),
    "revenue": lambda c: -c.revenue,
    "rpr": lambda c: -c.revenue_per_recipient,
    "open": lambda c: -c.open_rate,
}


def warn(message: str) -> None:
    """Write a non-fatal warning to stderr.

    Used when a row is dropped. A skipped row has to be announced: a report
    that quietly covers less than the file contains is how a wrong number
    reaches a client deck.
    """
    print(f"Warning: {message}", file=sys.stderr)


def open_csv(path):
    """Open *path* for reading, or raise CampaignReportError explaining why not."""
    try:
        return open(path, newline="", encoding="utf-8")
    except FileNotFoundError:
        raise CampaignReportError(f"CSV file not found: {path!r}") from None
    except IsADirectoryError:
        raise CampaignReportError(
            f"{path!r} is a directory, not a CSV file"
        ) from None
    except PermissionError:
        raise CampaignReportError(
            f"permission denied reading {path!r}"
        ) from None
    except OSError as exc:
        raise CampaignReportError(
            f"could not read {path!r}: {exc.strerror or exc}"
        ) from None


def check_columns(fieldnames, path) -> None:
    """Verify the header carries every expected column."""
    if not fieldnames:
        raise CampaignReportError(f"{path!r} is empty: no header row found")
    present = set(fieldnames)
    missing = [name for name in EXPECTED_COLUMNS if name not in present]
    if missing:
        raise CampaignReportError(
            f"{path!r} is missing required column(s): {', '.join(missing)}. "
            f"Expected: {', '.join(EXPECTED_COLUMNS)}"
        )


def parse_numeric(raw, column, row_number, cast):
    """Read one numeric cell, or raise CampaignReportError naming row and column."""
    try:
        value = cast(raw)
    except (TypeError, ValueError):
        shown = "(empty)" if raw is None else repr(raw)
        raise CampaignReportError(
            f"data row {row_number}: column {column!r} has a non-numeric "
            f"value {shown}"
        ) from None
    if value < 0:
        raise CampaignReportError(
            f"data row {row_number}: column {column!r} is negative "
            f"({value}); expected zero or more"
        )
    return value


def load_campaigns(path):
    """Read the CSV at *path* and return a list of Campaign records.

    Raises CampaignReportError, with the offending data row and column named
    where that applies, for an unreadable file, a missing column, a
    non-numeric or negative value, or a file with no usable campaigns. Rows
    reporting zero recipients are skipped with a warning on stderr rather
    than failing the run, since no rate metric can be computed for them.
    """
    campaigns = []
    rows_seen = 0
    skipped = 0
    with open_csv(path) as handle:
        reader = csv.DictReader(handle)
        check_columns(reader.fieldnames, path)
        for row_number, row in enumerate(reader, start=1):
            rows_seen += 1
            values = {
                column: parse_numeric(row[column], column, row_number, cast)
                for column, cast in NUMERIC_COLUMNS
            }
            if values["recipients"] == 0:
                skipped += 1
                warn(
                    f"data row {row_number}: skipping campaign "
                    f"{row['campaign_id']!r} ({row['name']}) because it has "
                    f"0 recipients, so no rate metric can be computed for it."
                )
                continue
            campaigns.append(
                Campaign(
                    campaign_id=row["campaign_id"],
                    name=row["name"],
                    send_date=row["send_date"],
                    **values,
                )
            )
    if not campaigns:
        if rows_seen == 0:
            raise CampaignReportError(
                f"{path!r} has no data rows: only a header was found"
            )
        raise CampaignReportError(
            f"{path!r} has no usable campaigns: all {skipped} data row(s) "
            f"were skipped for having 0 recipients"
        )
    return campaigns


def totals(campaigns):
    """Roll a list of campaigns up into one account-level Campaign record."""
    return Campaign(
        campaign_id="ALL",
        name="All campaigns",
        send_date="",
        recipients=sum(c.recipients for c in campaigns),
        opens=sum(c.opens for c in campaigns),
        clicks=sum(c.clicks for c in campaigns),
        orders=sum(c.orders for c in campaigns),
        revenue=sum(c.revenue for c in campaigns),
    )


def pct(value: float) -> str:
    """Format a 0-1 ratio as a percentage string."""
    return f"{value * 100:.1f}%"


def money(value: float) -> str:
    """Format a dollar amount with a thousands separator."""
    return f"${value:,.2f}"


def format_row(campaign) -> str:
    """Render one campaign as a fixed-width table row."""
    return (
        f"{campaign.name[:28]:<28} "
        f"{campaign.send_date:<11} "
        f"{campaign.recipients:>9,} "
        f"{pct(campaign.open_rate):>7} "
        f"{pct(campaign.click_rate):>7} "
        f"{pct(campaign.conversion_rate):>7} "
        f"{money(campaign.revenue):>12} "
        f"{money(campaign.revenue_per_recipient):>8}"
    )


def format_header() -> str:
    """Render the table header and its underline."""
    header = (
        f"{'CAMPAIGN':<28} {'SENT':<11} {'RECIPIENTS':>9} "
        f"{'OPEN':>7} {'CLICK':>7} {'CVR':>7} {'REVENUE':>12} {'RPR':>8}"
    )
    return f"{header}\n{'-' * len(header)}"


def format_summary(campaigns) -> str:
    """Render the account-level summary block."""
    roll = totals(campaigns)
    lines = [
        "",
        f"{len(campaigns)} campaigns  |  {roll.recipients:,} recipients  |  "
        f"{money(roll.revenue)} revenue",
        f"Blended open {pct(roll.open_rate)}  |  "
        f"click {pct(roll.click_rate)}  |  "
        f"CTOR {pct(roll.click_to_open_rate)}  |  "
        f"CVR {pct(roll.conversion_rate)}",
        f"Revenue per recipient {money(roll.revenue_per_recipient)}  |  "
        f"AOV {money(roll.average_order_value)}",
    ]
    return "\n".join(lines)


def build_report(campaigns, sort_key="date") -> str:
    """Build the full report string for *campaigns* in the requested order."""
    ordered = sorted(campaigns, key=SORT_KEYS[sort_key])
    lines = [format_header()]
    lines.extend(format_row(c) for c in ordered)
    lines.append(format_summary(campaigns))
    return "\n".join(lines)


def parse_args(argv=None):
    """Define and parse the command line interface."""
    parser = argparse.ArgumentParser(
        description="Summarize email campaign performance from a CSV export."
    )
    parser.add_argument("csv_path", help="path to the campaign CSV export")
    parser.add_argument(
        "--sort",
        choices=sorted(SORT_KEYS),
        default="date",
        help="column to order the table by (default: date)",
    )
    return parser.parse_args(argv)


def main(argv=None) -> int:
    """Entry point. Returns a process exit code.

    Only CampaignReportError is caught. Any other exception is a defect in
    this tool, and a traceback is the honest thing to show for it.
    """
    args = parse_args(argv)
    try:
        campaigns = load_campaigns(args.csv_path)
    except CampaignReportError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    print(build_report(campaigns, args.sort))
    return 0


if __name__ == "__main__":
    sys.exit(main())
