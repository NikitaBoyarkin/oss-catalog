---
title: Reading an A/B test like a decision, not a p-value
date: 2026-10-13
description: How to turn an experiment readout into a ship / extend / stop decision.
topics:
  - Experimentation
tags:
  - experimentation
---

An experiment readout is not a number to report — it is a decision to make. The job is to turn a
metric delta into one of three verbs: **ship**, **extend**, or **stop**.

## Start with the guardrails

Check the things that can invalidate the result before you look at the treatment effect:

```python
from statsmodels.stats.proportion import proportions_ztest

control = (120, 5000)   # conversions, users
variant = (150, 5000)

stat, p = proportions_ztest(
    count=[control[0], variant[0]],
    nobs=[control[1], variant[1]],
    alternative="two-sided",
)
```

- **Sample ratio mismatch** — if the observed split is far from planned, stop; the result is unreadable.
- **Power** — was the test sized to detect the effect you care about?
- **Guardrail metrics** — did anything get worse while the primary metric moved?

## Then read the effect in context

A significant lift is a starting point, not a verdict. Ask whether the effect is large enough to
matter once you account for the cost of shipping, and whether it holds across segments or is
carried by one of them.

## Next steps

Wire the same checks into a script you can re-run, so every readout is graded the same way.
