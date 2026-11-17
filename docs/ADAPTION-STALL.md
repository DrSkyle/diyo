# Adaption stall — 2026-11-17

Three adaptation runs are `running` with **0 rows processed**. This is written to be sent to
Adaption support with the IDs, because retrying has already cost credits.

| Dataset | ID | Rows | Started (UTC) | Progress | Credits charged |
|---|---|---|---|---|---|
| `diyo-behaviour-r3` | `f1919c42-6c0b-4cc4-a341-675c96dc1203` | 5,820 | 12:06 | **0 / 5,820 (0%)** | 59 |
| `nepali_local_advice_qa` | `fab32651-c11b-4e7a-8f85-8fa0a7211e34` | 3,932 | 13:12 | **0 / 3,932 (0%)** | 43 |
| `diyo-dense-health-v1` | `da584a8a-f8af-4d3e-98e3-adeadfb6657d` | 200 | ~14:14 | `progress: null` | 20 |

Observed at 14:56 UTC, i.e. 2h50m, 1h44m and ~40m after each started.

## What the platform reported and what happened

- `datasets.adapt(..., estimate=True)` quoted **83 minutes** for the 5,820-row run and **60
  minutes** for the 3,932-row run.
- Both were accepted, credits were consumed at launch, and both have sat at `processed_rows: 0`
  since. `error_data` is `null` on all three.
- The 200-row run has no `progress` object at all.
- Training on the same account is unaffected: three AutoScientist runs completed during this
  window (win rates 0.9343, 0.8513, 0.8257). So this is specific to adaptation, not the account
  being frozen.

## Concurrent load on the account at the time

Two datasets named `nepali_safety_refusals` (240 rows each) were also `running`. They are not
ours. If adaptation runs are serialised per account, they may be at the head of the queue and
stuck.

## Why it matters

The adaptation step is the only lever left on data quality: our completions grade at the 2nd
percentile (5.22 vs a 9.38 reference) under Adaption's own evaluation, and training more rows
without it made the model measurably worse (25/32 → 22/32 → 23/32 as rows grew 2,256 → 5,820 →
7,586). We cannot proceed without either the adapt completing or a refund of the 122 credits
consumed by the three runs.

## Reproduction

```python
import time
from adaption import Adaption
c = Adaption()
ds = c.datasets.get("f1919c42-6c0b-4cc4-a341-675c96dc1203")
while True:
    st = c.datasets.get_status(ds.dataset_id)
    print(st.status, st.progress)   # running {'percent': 0, 'processed_rows': 0, ...}
    time.sleep(60)
```
