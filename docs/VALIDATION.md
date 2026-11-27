# Validation (simulation only)

Ground truth: the 3D line simulator's own cycle times (`assets/sim10_ground_truth.json`). The
simulator makes ST5 Sleeve Attach about 2.1x slower than every other station.

| Run | Constraint found | Confidence | Pearson r vs truth | Bottleneck / rest (measured vs true) | Mean station error* | Worst station* |
|---|---|---|---|---|---|---|
| Full 340 s, 1080p | ST5 (truth ST5) | high | 0.97 | 2.31x vs 2.15x | 8% | 20% |
| 150 s clip, 960 px (sample) | ST5 (truth ST5) | high | 0.96 | 2.27x vs 2.15x | 9% | 23% |

\* After removing one global offset. Visit time includes about a second of hand-off, so absolute
times read roughly 1.1-1.3x high. The line-level pace ratio to the SMV sheet absorbs this.

What this shows: on footage with known answers, the pipeline finds the right constraint at high
confidence, recovers the shape of the cycle-time profile (r about 0.96-0.97), and the +1 operator
prescription it derives matches the factory sheet's own "proposed" layout.

What this does NOT show: accuracy on a real factory floor, with real bundles, real occlusion, real
cameras. The last two lines of the report say so. Do not claim real-line validation until you have
footage and a stopwatch time study from a real line to compare against.

Weak spots seen: the detector misses some pale/white fabric, so downstream completion counts are
under-counted and absolute throughput is not trustworthy. Cycle-time *ratios between stations* are.
Spearman rank on short clips is low because the non-bottleneck stations are nearly tied (3.6-4.4 s).
