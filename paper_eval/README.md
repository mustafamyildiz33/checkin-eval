# Paper Evaluation Specs For Check-In

These JSON files define the phase-based paper demo suites that the paper runner
can execute against the transactional check-in protocol with an exact active
demo window of either 60 or 120 seconds.

## Phase layout

- `phase1`: Baseline. No destructive event is injected. This phase measures clean steady-state reachability, throughput, overhead, and per-node load.
- `phase2`: Fire Spread And Bomb. A center ignition spreads outward in hop-based rings, marks a temporary bomb core, then trails recovery behind the front. This is the main spread/accuracy phase.
- `phase3`: Tornado Hazard Sensing. A moving tornado band crosses the grid. The local watch node shows direct hazard detection while the far watch node shows propagation across distance.
- `phase4`: Adversarial Stress. The runner injects false unavailability, noisy or lying sensors, and unstable/flapping behavior. This tests resilience, false positives, false unavailable references, and recovery.

## Durations

Each phase includes:

- a `60s` spec for the exact one-minute runs your teammate requested,
- a `120s` spec for the two-minute comparison run you may want later.

## Runner examples

Dry-run a suite without starting nodes:

```bash
python3 paper_eval_runner.py --spec paper_eval/phase1/phase1_baseline_60s.json --dry-run
```

Run one suite with only the first two repetitions while testing:

```bash
python3 paper_eval_runner.py --spec paper_eval/phase2/phase2_fire_60s.json --max-runs 2
```

Override node counts while testing:

```bash
python3 paper_eval_runner.py --spec paper_eval/phase4/phase4_stress_120s.json --max-runs 1 --node-counts 49
```

Short same-machine smoke test:

```bash
python3 paper_eval_runner.py --spec paper_eval/phase2/phase2_fire_60s.json --max-runs 1 --node-counts 49 --duration-sec 10
```

## Copy-Paste Commands

For the Check-In school-lab run sheet, use:

- `paper_eval/CHECKIN_LAB_RUN_SHEET.md`
- `paper_eval/run_sheets/checkin_proof_lite_batch_sheet.csv`

## Storage Safety

The runner is storage-safe by default for class demos and paper collection:

- Node logs are bounded to `64 KB` per node by default.
- The wrapper checks available disk space before starting and estimates reports, history, evidence, and capped logs.
- `--dry-run` prints the same storage estimate without starting nodes.
- Protocol verbose logging is off by default, so `data.csv` and raw node logs do not balloon.
- Evidence JSON is compact by default so every node keeps the paper metrics without storing huge raw node state.
- Reports, TSV files, and HTML dashboards are still generated normally.

For paper collection with graphs but no node logs, use `--lean-graphs`.
For graphs plus a small proof trail, use `--proof-lite`; it keeps capped
`32 KB` node logs and compact evidence snippets without storing full raw node
state.

After each 6-batch chunk, check that the rows, statuses, figures, and Google
Sheets CSVs are ready before starting the next chunk:

```bash
cd /Users/mustafa/egess
./.venv/bin/python check_chunk_status.py --root /Users/mustafa/egess/external/checkin-egess-eval --base-port 9200 --batch-start 1 --batches 6 --nodes 49,64
```

If you need extra raw node log detail for a short demo, keep it bounded:

```bash
cd /Users/mustafa/egess/external/checkin-egess-eval
EGESS_LOG=1 ./run_paper_eval.sh --mode all --duration 60 --batches 1 --nodes 49 --log-max-kb 128
```

Avoid `--full-logs` unless you intentionally want uncapped raw logs. The wrapper blocks it by default because it can fill a laptop disk.
Avoid `--full-evidence` for paper batches. It is only for short debugging runs because it stores raw node state. Use `--proof-lite` when you want small logs and evidence for paper proof.

Preview storage before a full 30-batch run:

```bash
cd /Users/mustafa/egess/external/checkin-egess-eval
./run_paper_eval.sh --mode all --duration 60 --batches 30 --nodes 49 --dry-run
./run_paper_eval.sh --mode all --duration 60 --batches 30 --nodes 49 --proof-lite --dry-run
```

To clean old raw run folders before the real experiment:

```bash
cd /Users/mustafa/egess/external/checkin-egess-eval
./clean_eval_outputs.sh runs
```

To clear both raw runs and generated report dashboards:

```bash
cd /Users/mustafa/egess/external/checkin-egess-eval
./clean_eval_outputs.sh all
```

## Demo Order

Use this order during class:

1. Start a quick `4-batch` run with `--open-live`.
2. In a second terminal, tail the live event stream.
3. In a third terminal, tail one or two node logs.
4. When it finishes, open the campaign report.
5. Open the latest scenario suite report.
6. Open the latest single-run deep dive.

### Live Tail Commands

Tail the newest run's event stream:

```bash
cd /Users/mustafa/egess/external/checkin-egess-eval
RUN_DIR=$(ls -1dt runs/* | head -n 1)
tail -f "$RUN_DIR/paper_events.jsonl"
```

Tail the newest run's local and far watch node logs:

```bash
cd /Users/mustafa/egess/external/checkin-egess-eval
RUN_DIR=$(ls -1dt runs/* | head -n 1)
tail -f "$RUN_DIR/node_9024.log" "$RUN_DIR/node_9000.log"
```

Note: node logs are intentionally capped. The event stream is the best live view for the class demo.

Tail the newest run's paper summary files after the run:

```bash
cd /Users/mustafa/egess/external/checkin-egess-eval
RUN_DIR=$(ls -1dt runs/* | head -n 1)
sed -n '1,40p' "$RUN_DIR/paper_summary.tsv"
sed -n '1,40p' "$RUN_DIR/paper_watch_nodes.tsv"
```

### Quick Test: 4 batches, 60 seconds, 49 nodes

Run the quick all-scenarios test:

```bash
cd /Users/mustafa/egess/external/checkin-egess-eval
./run_paper_eval.sh --mode all --duration 60 --batches 4 --nodes 49 --open-live
```

The live campaign dashboard opens immediately and auto-refreshes while the batch is running. For the current single-run browser view, open:

```bash
cd /Users/mustafa/egess/external/checkin-egess-eval
RUN_DIR=$(ls -1dt runs/* | head -n 1)
open "$RUN_DIR/live_run.html"
```

Open the campaign report:

```bash
cd /Users/mustafa/egess/external/checkin-egess-eval
CAMPAIGN_DIR=$(ls -1dt campaign_reports/all_together_60s_* | head -n 1)
open "$CAMPAIGN_DIR/index.html"
```

Open the latest scenario suite report:

```bash
cd /Users/mustafa/egess/external/checkin-egess-eval
REPORT_DIR=$(ls -1dt paper_reports/* | head -n 1)
open "$REPORT_DIR/index.html"
```

Open the latest single-run deep dive:

```bash
cd /Users/mustafa/egess/external/checkin-egess-eval
RUN_DIR=$(ls -1dt runs/* | head -n 1)
open "$RUN_DIR/paper_summary.html"
```

### Quick Test: 4 batches, 60 seconds, 40 nodes

```bash
cd /Users/mustafa/egess/external/checkin-egess-eval
./run_paper_eval.sh --mode all --duration 60 --batches 4 --nodes 40
```

### Quick Test: 4 batches, 60 seconds, 64 nodes

```bash
cd /Users/mustafa/egess/external/checkin-egess-eval
./run_paper_eval.sh --mode all --duration 60 --batches 4 --nodes 64
```

### Quick Test: 4 batches, 60 seconds, 89 nodes

```bash
cd /Users/mustafa/egess/external/checkin-egess-eval
./run_paper_eval.sh --mode all --duration 60 --batches 4 --nodes 89
```

### Full Run: 30 batches, 60 seconds, 49 nodes

Run the full all-scenarios paper batch:

```bash
cd /Users/mustafa/egess/external/checkin-egess-eval
./run_paper_eval.sh --mode all --duration 60 --batches 30 --nodes 49 --open-live
```

Open the campaign report:

```bash
cd /Users/mustafa/egess/external/checkin-egess-eval
CAMPAIGN_DIR=$(ls -1dt campaign_reports/all_together_60s_* | head -n 1)
open "$CAMPAIGN_DIR/index.html"
```

Open the latest scenario suite report:

```bash
cd /Users/mustafa/egess/external/checkin-egess-eval
REPORT_DIR=$(ls -1dt paper_reports/* | head -n 1)
open "$REPORT_DIR/index.html"
```

Open the latest single-run deep dive:

```bash
cd /Users/mustafa/egess/external/checkin-egess-eval
RUN_DIR=$(ls -1dt runs/* | head -n 1)
open "$RUN_DIR/paper_summary.html"
```

### Full Run: 30 batches, 60 seconds, 40 nodes

```bash
cd /Users/mustafa/egess/external/checkin-egess-eval
./run_paper_eval.sh --mode all --duration 60 --batches 30 --nodes 40
```

### Full Run: 30 batches, 60 seconds, 64 nodes

```bash
cd /Users/mustafa/egess/external/checkin-egess-eval
./run_paper_eval.sh --mode all --duration 60 --batches 30 --nodes 64
```

### Full Run: 30 batches, 60 seconds, 89 nodes

```bash
cd /Users/mustafa/egess/external/checkin-egess-eval
./run_paper_eval.sh --mode all --duration 60 --batches 30 --nodes 89
```

## Output

Each real run writes:

- `runs/<timestamp>/paper_events.jsonl`
- `runs/<timestamp>/paper_manifest.json`
- `runs/<timestamp>/paper_evidence.json`
- `runs/<timestamp>/paper_summary.tsv`
- `runs/<timestamp>/paper_watch_nodes.tsv`
- `runs/<timestamp>/paper_summary.md`

Each suite also writes a combined report bundle into
`paper_reports/<suite_id>_<timestamp>/`.

## Cross-Protocol Merge

After Check-In and EGESS finish on their own computers, copy both
`paper_reports/` folders onto one machine and run the EGESS-side merger:

```bash
python3 /Users/mustafa/egess/cross_protocol_summary.py \
  --egess-root /path/to/egess/paper_reports \
  --checkin-root /path/to/checkin/paper_reports
```

## Statistical Analysis

After both teams finish collecting data, run the statistics post-processor from
the EGESS repo. It generates confidence intervals, percentiles, graph-ready TSVs,
paired t-tests, and mean-with-95%-CI PNG figures:

```bash
cd /Users/mustafa/egess
/Users/mustafa/egess/.venv/bin/python paper_eval_statistics.py \
  --egess-root /Users/mustafa/egess/paper_reports \
  --checkin-root /Users/mustafa/egess/external/checkin-egess-eval/paper_reports
```

Open the statistics dashboard:

```bash
cd /Users/mustafa/egess
STATS_DIR=$(ls -1dt statistics_reports/* | head -n 1)
open "$STATS_DIR/index.html"
```

The output includes:

- `metric_statistics.tsv`: sample mean, sample standard deviation, standard error, 95% confidence interval, and p50/p90/p95/p99.
- `overhead_percentiles.tsv`: overhead-focused percentiles for run-level and watched-node bytes/MB.
- `paired_t_tests.tsv`: paired EGESS vs Check-In comparisons matched by scenario, node count, run index, and seed.
- `boxplot_data.tsv`: median, quartiles, whiskers, and outlier counts.
- `cdf_points.tsv`: CDF-ready values for detection latency, throughput counters, and overhead.
- `histogram_bins.tsv`: histogram-ready distribution bins.
- `figure_exports/`: paper-ready PNG figures and their supporting TSVs.
