# Age-Stratified Noise Model Refit

Generated 2026-07-06T00:00:00

```
AGE-STRATIFIED NOISE MODEL REFIT
============================================================

<48h (fresh -> aged):
  Total reads in stratum: 2
  Per-family stats:
    heuristic+trolley: n= 1 mean=  422.2 stdev=   0.0 range=[  422.2,   422.2]
    heuristic+trolley-ability: n= 1 mean=  563.8 stdev=   0.0 range=[  563.8,   563.8]

48-72h (fresh -> aged):
  Total reads in stratum: 57
  Per-family stats:
    heuristic+trolley: n=28 mean=  437.8 stdev=   9.3 range=[  423.5,   456.0]
    heuristic+trolley-ability: n=29 mean=  570.9 stdev=  43.2 range=[  470.1,   603.3]
  Pooled residuals: n=57 stdev=31.2 max_abs=100.8

>72h (fresh -> aged):
  Total reads in stratum: 2
  Per-family stats:
    heuristic+trolley: n= 1 mean=  600.0 stdev=   0.0 range=[  600.0,   600.0]
    heuristic+trolley_thick: n= 1 mean=  446.2 stdev=   0.0 range=[  446.2,   446.2]

============================================================

IMPLICATION:
heuristic+trolley:
  Aged (>72h):  mean=  600.0 (n=1)
  Fresh (<48h): mean=  422.2 (n=1)
  Difference:   -177.8pp (fresh is depressed)
```
