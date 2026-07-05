# Age-Stratified Noise Model Refit

Generated 2026-07-05T00:00:00

```
AGE-STRATIFIED NOISE MODEL REFIT
============================================================

<48h (fresh -> aged):
  Total reads in stratum: 59
  Per-family stats:
    heuristic+trolley: n=29 mean=  437.2 stdev=   9.6 range=[  422.2,   456.0]
    heuristic+trolley-ability: n=30 mean=  570.7 stdev=  42.5 range=[  470.1,   603.3]
  Pooled residuals: n=59 stdev=30.8 max_abs=100.6

48-72h (fresh -> aged):
  Total reads in stratum: 1
  Per-family stats:
    heuristic+trolley_thick: n= 1 mean=  446.2 stdev=   0.0 range=[  446.2,   446.2]

>72h (fresh -> aged):
  Total reads in stratum: 1
  Per-family stats:
    heuristic+trolley: n= 1 mean=  600.0 stdev=   0.0 range=[  600.0,   600.0]

============================================================

IMPLICATION:
heuristic+trolley:
  Aged (>72h):  mean=  600.0 (n=1)
  Fresh (<48h): mean=  437.2 (n=29)
  Difference:   -162.8pp (fresh is depressed)
```
