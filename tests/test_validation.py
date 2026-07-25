"""Input validation and error handling tests.

Every bad input should produce a clear message on stderr and a non-zero exit
code, never a raw traceback. The one exception is a row reporting zero
recipients: that row is skipped with a warning and the run still succeeds.
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import campaign_report as cr  # noqa: E402

HEADER = "campaign_id,name,send_date,recipients,opens,clicks,orders,revenue"
GOOD_ROW = "c1001,Spring Refresh,2026-03-04,41250,18974,1732,214,18690.40"
SECOND_ROW = "c1002,Bestsellers,2026-03-11,39880,15154,1196,148,12986.00"


def write_csv(tmp_path, *lines, name="campaigns.csv"):
    """Write *lines* as a CSV file and return its path as a string."""
    path = tmp_path / name
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return str(path)


# --- 1. missing or unreadable path ---------------------------------------


def test_missing_file_names_the_path(tmp_path):
    missing = str(tmp_path / "nope.csv")
    with pytest.raises(cr.CampaignReportError) as excinfo:
        cr.load_campaigns(missing)
    message = str(excinfo.value)
    assert "not found" in message
    assert "nope.csv" in message


def test_directory_instead_of_file_is_reported(tmp_path):
    directory = tmp_path / "a_directory"
    directory.mkdir()
    with pytest.raises(cr.CampaignReportError) as excinfo:
        cr.load_campaigns(str(directory))
    assert "directory" in str(excinfo.value)


@pytest.mark.skipif(
    getattr(os, "geteuid", lambda: 1)() == 0,
    reason="root ignores file permissions",
)
def test_unreadable_file_is_reported(tmp_path):
    path = write_csv(tmp_path, HEADER, GOOD_ROW)
    os.chmod(path, 0o000)
    try:
        with pytest.raises(cr.CampaignReportError) as excinfo:
            cr.load_campaigns(path)
        assert "permission denied" in str(excinfo.value).lower()
    finally:
        os.chmod(path, 0o644)


# --- 2. missing required columns -----------------------------------------


def test_missing_column_is_named(tmp_path):
    path = write_csv(
        tmp_path,
        "campaign_id,name,send_date,recipients,opens,clicks,orders",
        "c1001,Spring Refresh,2026-03-04,41250,18974,1732,214",
    )
    with pytest.raises(cr.CampaignReportError) as excinfo:
        cr.load_campaigns(path)
    message = str(excinfo.value)
    assert "missing required column" in message
    assert "revenue" in message


def test_every_missing_column_is_listed(tmp_path):
    path = write_csv(
        tmp_path,
        "campaign_id,name,send_date,recipients,opens,clicks",
        "c1001,Spring Refresh,2026-03-04,41250,18974,1732",
    )
    message = str(
        pytest.raises(cr.CampaignReportError, cr.load_campaigns, path).value
    )
    assert "orders" in message
    assert "revenue" in message


def test_extra_columns_are_allowed(tmp_path):
    path = write_csv(
        tmp_path,
        HEADER + ",unsubscribes",
        GOOD_ROW + ",12",
    )
    campaigns = cr.load_campaigns(path)
    assert len(campaigns) == 1


def test_byte_order_mark_does_not_hide_the_first_column(tmp_path):
    """A BOM-prefixed export is common and must not read as a missing column."""
    path = tmp_path / "bom.csv"
    path.write_text("\n".join([HEADER, GOOD_ROW]) + "\n", encoding="utf-8-sig")
    assert path.read_bytes().startswith(b"\xef\xbb\xbf")
    campaigns = cr.load_campaigns(str(path))
    assert len(campaigns) == 1
    assert campaigns[0].campaign_id == "c1001"


# --- 3. non-numeric values in numeric columns ----------------------------


def test_non_numeric_value_names_row_and_column(tmp_path):
    path = write_csv(
        tmp_path,
        HEADER,
        GOOD_ROW,
        "c1002,Bestsellers,2026-03-11,39880,15154,N/A,148,12986.00",
    )
    with pytest.raises(cr.CampaignReportError) as excinfo:
        cr.load_campaigns(path)
    message = str(excinfo.value)
    assert "data row 2" in message
    assert "clicks" in message
    assert "N/A" in message


def test_empty_numeric_cell_names_row_and_column(tmp_path):
    path = write_csv(
        tmp_path,
        HEADER,
        "c1001,Spring Refresh,2026-03-04,41250,18974,1732,214,",
    )
    with pytest.raises(cr.CampaignReportError) as excinfo:
        cr.load_campaigns(path)
    message = str(excinfo.value)
    assert "data row 1" in message
    assert "revenue" in message


def test_short_row_names_the_missing_column(tmp_path):
    path = write_csv(
        tmp_path,
        HEADER,
        "c1001,Spring Refresh,2026-03-04,41250",
    )
    with pytest.raises(cr.CampaignReportError) as excinfo:
        cr.load_campaigns(path)
    message = str(excinfo.value)
    assert "data row 1" in message
    assert "opens" in message


def test_decimal_in_an_integer_column_says_whole_number_not_non_numeric(
    tmp_path,
):
    """41250.5 is a number, so the message must not claim otherwise."""
    path = write_csv(
        tmp_path,
        HEADER,
        "c1001,Spring Refresh,2026-03-04,41250.5,18974,1732,214,18690.40",
    )
    with pytest.raises(cr.CampaignReportError) as excinfo:
        cr.load_campaigns(path)
    message = str(excinfo.value)
    assert "recipients" in message
    assert "whole number" in message
    assert "41250.5" in message
    assert "non-numeric" not in message


# --- 4. negative numbers -------------------------------------------------


def test_negative_revenue_names_row_and_column(tmp_path):
    path = write_csv(
        tmp_path,
        HEADER,
        GOOD_ROW,
        "c1002,Bestsellers,2026-03-11,39880,15154,1196,148,-12986.00",
    )
    with pytest.raises(cr.CampaignReportError) as excinfo:
        cr.load_campaigns(path)
    message = str(excinfo.value)
    assert "data row 2" in message
    assert "revenue" in message
    assert "negative" in message


def test_negative_recipients_names_row_and_column(tmp_path):
    path = write_csv(
        tmp_path,
        HEADER,
        "c1001,Spring Refresh,2026-03-04,-41250,18974,1732,214,18690.40",
    )
    with pytest.raises(cr.CampaignReportError) as excinfo:
        cr.load_campaigns(path)
    message = str(excinfo.value)
    assert "data row 1" in message
    assert "recipients" in message
    assert "negative" in message


def test_zero_is_not_treated_as_negative(tmp_path):
    path = write_csv(
        tmp_path,
        HEADER,
        "c1001,Spring Refresh,2026-03-04,41250,0,0,0,0.00",
    )
    campaigns = cr.load_campaigns(path)
    assert campaigns[0].revenue == 0.0


# --- 5. zero recipients: skip, warn, keep going --------------------------


def test_zero_recipient_row_is_skipped_not_fatal(tmp_path, capsys):
    path = write_csv(
        tmp_path,
        HEADER,
        GOOD_ROW,
        "c1002,Dead Segment,2026-03-11,0,0,0,0,0.00",
        SECOND_ROW,
    )
    campaigns = cr.load_campaigns(path)
    assert [c.campaign_id for c in campaigns] == ["c1001", "c1002"]
    assert len(campaigns) == 2
    assert "Dead Segment" not in [c.name for c in campaigns]


def test_zero_recipient_skip_warns_on_stderr_naming_the_campaign(
    tmp_path, capsys
):
    path = write_csv(
        tmp_path,
        HEADER,
        GOOD_ROW,
        "c9999,Dead Segment,2026-03-11,0,0,0,0,0.00",
    )
    cr.load_campaigns(path)
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "Warning" in captured.err
    assert "c9999" in captured.err
    assert "Dead Segment" in captured.err
    assert "data row 2" in captured.err
    assert "0 recipients" in captured.err


def test_run_with_a_skipped_row_still_exits_zero(tmp_path, capsys):
    path = write_csv(
        tmp_path,
        HEADER,
        GOOD_ROW,
        "c9999,Dead Segment,2026-03-11,0,0,0,0,0.00",
    )
    assert cr.main([path]) == 0
    captured = capsys.readouterr()
    assert "CAMPAIGN" in captured.out
    assert "Dead Segment" not in captured.out
    assert "Warning" in captured.err


def test_every_row_skipped_is_an_error(tmp_path):
    path = write_csv(
        tmp_path,
        HEADER,
        "c1001,Dead One,2026-03-04,0,0,0,0,0.00",
        "c1002,Dead Two,2026-03-11,0,0,0,0,0.00",
    )
    with pytest.raises(cr.CampaignReportError) as excinfo:
        cr.load_campaigns(path)
    message = str(excinfo.value)
    assert "no usable campaigns" in message
    assert "2" in message


# --- 6. empty CSV --------------------------------------------------------


def test_header_only_csv_is_an_error(tmp_path):
    path = write_csv(tmp_path, HEADER)
    with pytest.raises(cr.CampaignReportError) as excinfo:
        cr.load_campaigns(path)
    assert "no data rows" in str(excinfo.value)


def test_completely_empty_file_is_an_error(tmp_path):
    path = tmp_path / "empty.csv"
    path.write_text("", encoding="utf-8")
    with pytest.raises(cr.CampaignReportError) as excinfo:
        cr.load_campaigns(str(path))
    assert "empty" in str(excinfo.value)


# --- exit codes and stderr contract --------------------------------------


BAD_INPUTS = [
    ("missing file", None),
    ("header only", [HEADER]),
    ("missing column", ["campaign_id,name,send_date,recipients,opens,clicks,orders",
                        "c1001,A,2026-03-04,41250,18974,1732,214"]),
    ("non-numeric", [HEADER,
                     "c1001,A,2026-03-04,41250,18974,oops,214,18690.40"]),
    ("negative", [HEADER,
                  "c1001,A,2026-03-04,41250,18974,1732,214,-18690.40"]),
    ("all rows skipped", [HEADER, "c1001,A,2026-03-04,0,0,0,0,0.00"]),
]


@pytest.mark.parametrize(
    "label,lines", BAD_INPUTS, ids=[case[0] for case in BAD_INPUTS]
)
def test_bad_input_exits_nonzero_with_a_clean_message(
    tmp_path, capsys, label, lines
):
    if lines is None:
        path = str(tmp_path / "does_not_exist.csv")
    else:
        path = write_csv(tmp_path, *lines)

    exit_code = cr.main([path])
    captured = capsys.readouterr()

    assert exit_code == 1, f"{label} should exit non-zero"
    assert captured.out == "", f"{label} should print no report"
    assert captured.err.startswith("Error: ") or "Error: " in captured.err
    assert "Traceback" not in captured.err
    assert len(captured.err.strip().splitlines()) <= 2


def test_unexpected_errors_are_not_swallowed(tmp_path, monkeypatch):
    """A defect in the tool must still raise, not become a polite exit 1."""
    path = write_csv(tmp_path, HEADER, GOOD_ROW)

    def boom(*args, **kwargs):
        raise RuntimeError("simulated defect")

    monkeypatch.setattr(cr, "build_report", boom)
    with pytest.raises(RuntimeError, match="simulated defect"):
        cr.main([path])


# --- a valid run is untouched --------------------------------------------


FIXTURE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data",
    "campaigns.csv",
)


def test_valid_run_is_silent_on_stderr_and_exits_zero(capsys):
    assert cr.main([FIXTURE]) == 0
    captured = capsys.readouterr()
    assert captured.err == ""
    assert "CAMPAIGN" in captured.out


def test_valid_run_output_is_byte_for_byte_unchanged(capsys):
    """Guards the 'do not change the output of a valid run' constraint."""
    cr.main([FIXTURE])
    produced = capsys.readouterr().out
    expected_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "expected_report.txt"
    )
    with open(expected_path, encoding="utf-8") as handle:
        assert produced == handle.read()
