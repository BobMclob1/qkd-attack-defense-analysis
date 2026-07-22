# QKD Attack–Defense Analysis — Project Context

## What this is
A from-scratch Python simulator for a Lumiere research paper.
Research question: *How do characteristic attacks and matched
defenses change the secret key rate of BB84 and BBM92 across
channel loss?*

## Scope (locked — do not expand)
- Computational core: **BB84 + BBM92 only**, sharing one QBER-based
  GLLP key-rate engine.
- Two attack–defense pairs:
  - Pair 1: PNS attack → decoy-state defense (QBER-*invisible*).
  - Pair 2: intercept-resend → QBER-threshold/privacy-amplification
    defense (QBER-*visible*).
- E91: **discussion only, never simulated.**
- Single swept variable: distance / channel loss (L). Everything else
  frozen (mu, dark counts, detector efficiency, misalignment, f).
- Output: secure key rate R vs distance — plot the SECURE rate,
  never apparent throughput.

## Code conventions
- All key-rate equations coded **directly from the source paper**,
  never from memory or reconstruction. Cite the equation number in
  a comment (e.g. `# LMC Eq. 6`).
- Primary engine source: Lo–Ma–Chen (LMC), arXiv:quant-ph/0411004v4,
  PRL 94 230504 (2005) — Eqs 2,3,6,7,8,9,10,11.
- Decoy Y1/e1 estimators: Ma–Qi–Zhao–Lo (MQZL), quant-ph/0503005
  (to be pulled — the "how" to LMC's "why").
- Frozen physical constants live as named module-level constants,
  not magic numbers, so they can be un-frozen as deliberate "twists".

## Build order (Milestones)
1. GLLP engine (clean protocol). ← current
2. BB84 Pair 1: ceiling / PNS crash / decoy recovery.
3. BBM92 Pair 1 (SPDC source — Ma–Fung–Lo).
4. Pair 2 (intercept-resend) both protocols.
5. Interpretation + optional twist (un-freeze dark counts).

## Validation target
LMC Fig 1 (GYS params): decoy reaches ~140 km, GLLP-bound-only ~30 km,
insecurity upper bound 208 km (where e1 = 1/4).

## Citation discipline
"Verified" = citation confirmed real. Separately, every source must be
*read and paraphrased* in my own words for the paper — never quoted,
never summarized from memory.