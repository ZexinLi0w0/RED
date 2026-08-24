# Reproducible experiment runner

`run_matrix.py` executes every method/seed in an isolated directory. Each run
contains:

- `manifest.json`: device, power mode, git commit/status, config SHA-256, seed,
  command, offered-task hash, timestamps, and final status;
- `stdout.log`: complete controller/handler output;
- `task_statistics.pkl`: original offered-node outcomes, even when execution
  nodes were merged;
- `end2end_time.txt` and `summary.json`: machine-readable headline metrics.

Always inspect the matrix before occupying a device:

```bash
python3 experiments/run_matrix.py \
  --device agx \
  --power-mode MAXN \
  --handler-config handler-config.json \
  --task-dir TaskConfigs/simo/new_scenarios \
  --output-root taskdata/reruns/agx \
  --profiles tight,loose \
  --seeds 101,202,303,404,505 \
  --dry-run
```

Remove `--dry-run` to execute. A run directory is never overwritten. Passing
`--resume` skips only runs whose manifest already says `complete`; failed or
partial directories require investigation and a new run identity.

For EDF-only calibration, use calibration profile names/config files and only
the `baseline` method. Do not include or inspect the proposed method until the
selected Tight/Loose configurations have been committed and hashed.
