# campaign_report

A small command line tool that summarizes email campaign performance from a
platform CSV export. It prints a per-campaign metrics table and an
account-level rollup.

## Usage

```
python campaign_report.py data/campaigns.csv
python campaign_report.py data/campaigns.csv --sort rpr
python campaign_report.py data/campaigns.csv --top 3
```

Sort keys: `date` (default), `name`, `revenue`, `rpr`, `open`.

`--top N` keeps only the N campaigns with the highest revenue per recipient.
It composes with `--sort`, which still controls the order those N are
displayed in, and the summary covers just the campaigns shown.

## Expected CSV columns

```
campaign_id,name,send_date,recipients,opens,clicks,orders,revenue
```

## Tests

```
python -m pytest tests/ -q
```

## Context

This repository is the subject of the CPSC 6820 Week 4 Delegate & Review Lab.
The `main` branch holds the human-written baseline. Agent-authored work arrives
through feature branches and is merged only after checkpoint review. See
`docs/` for the lab's task definition, checkpoint records, and code review.
