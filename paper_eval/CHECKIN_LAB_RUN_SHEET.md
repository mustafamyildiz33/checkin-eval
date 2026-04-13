# Check-In Paper Evaluation Lab Run Sheet

Use this sheet for the Check-In protocol runs. The recommended mode is
`--proof-lite`: final HTML dashboards, paper figures, Google Sheets CSVs,
compact evidence, and capped 32 KB node logs.

Run Check-In from:

```bash
cd /Users/mustafa/egess/external/checkin-egess-eval
```

## Five Parts

| Part | Batch range | Run command |
| --- | --- | --- |
| 1 | 1-6 | `./run_paper_eval.sh --base-port 9200 --mode all --duration 60 --batches 6 --batch-start 1 --nodes 49,64 --proof-lite` |
| 2 | 7-12 | `./run_paper_eval.sh --base-port 9200 --mode all --duration 60 --batches 6 --batch-start 7 --nodes 49,64 --proof-lite` |
| 3 | 13-18 | `./run_paper_eval.sh --base-port 9200 --mode all --duration 60 --batches 6 --batch-start 13 --nodes 49,64 --proof-lite` |
| 4 | 19-24 | `./run_paper_eval.sh --base-port 9200 --mode all --duration 60 --batches 6 --batch-start 19 --nodes 49,64 --proof-lite` |
| 5 | 25-30 | `./run_paper_eval.sh --base-port 9200 --mode all --duration 60 --batches 6 --batch-start 25 --nodes 49,64 --proof-lite` |

## Checkpoint After Each Part

Run the checkpoint from the EGESS repo:

```bash
cd /Users/mustafa/egess
./.venv/bin/python check_chunk_status.py --root /Users/mustafa/egess/external/checkin-egess-eval --base-port 9200 --batch-start 1 --batches 6 --nodes 49,64
```

Change `--batch-start` to the part you just finished: `1`, `7`, `13`, `19`, or
`25`.

Do not start the next part until the checker says `OK`.

## View HTML

Open the latest Check-In chunk dashboard:

```bash
CHUNK_DIR=$(ls -1dt /Users/mustafa/egess/external/checkin-egess-eval/campaign_reports/all_together_60s_*_p9200* | head -n 1)
open "$CHUNK_DIR/index.html"
```

## Merge And Export

After all five parts finish, merge from the EGESS repo:

```bash
cd /Users/mustafa/egess
./.venv/bin/python merge_paper_reports.py --root checkin=/Users/mustafa/egess/external/checkin-egess-eval/paper_reports --base-port 9200 --nodes 49,64 --duration-sec 60 --expected-batches 30
MERGED_DIR=$(ls -1dt /Users/mustafa/egess/merged_paper_reports/merged_*_p9200* | head -n 1)
open "$MERGED_DIR/index.html"
```

Click `Download Export Bundle` in the merged HTML.

## Stop/Go Checklist

- `48` rows per part.
- Correct batch range.
- `phase1,phase2,phase3,phase4` all present.
- Nodes `49,64` both present.
- No failed, blank, or still-running rows.
- Graph PNG/TSV data exists.
- Google Sheets CSVs exist.
- HTML opens.

Spreadsheet version:

- `paper_eval/run_sheets/checkin_proof_lite_batch_sheet.csv`
