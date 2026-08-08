# QKD Attack–Defense Analysis — Project Context

## What this is
A from-scratch Python simulator for a Lumiere research paper.
Research question: *How do characteristic attacks and matched
defenses change the secret key rate of BB84 and BBM92 across
channel loss?*

## Scope (locked — do not expand)
- Computational core: **BB84 + BBM92 only**. They share QBER-based
  *infrastructure* (binary entropy, channel/loss model, frozen
  constants, the sweep/plot harness) but use **protocol-specific
  key-rate formulas** — NOT one common combiner:
  - **BB84 → GLLP** (LMC Eq. 11): must isolate the single-photon term
    `Q1[1−H2(e1)]` because the coherent source is basis-*dependent* and
    leaks multi-photon pulses to Eve (the PNS problem).
  - **BBM92 → Koashi–Preskill** (Ma–Fung–Lo Eq. 11): uses only the
    *overall* gain/QBER `Qλ, Eλ` (δb=δp=Eλ), no single-photon
    isolation, because the entangled PDC source is basis-*independent*.
    This is *why* BBM92 is intrinsically PNS-resistant and needs no
    decoy — a key finding to foreground in the write-up and the plot.
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
- Decoy Y1/e1 estimators: Ma–Qi–Zhao–Lo (MQZL), quant-ph/0503005v5
  (the "how" to LMC's "why"). Vacuum+Weak forms: §3.4 Eqs. 33,34,35,37.
- BBM92 / entangled PDC source + Koashi–Preskill rate: Ma–Fung–Lo (MFL),
  quant-ph/0703122v1 — Eqs. 5,6,7,8,9,10,11,12 (+ App. A for e1).
- Frozen physical constants live as named module-level constants,
  not magic numbers, so they can be un-frozen as deliberate "twists".

## Build order (Milestones)
1. GLLP engine (clean protocol). ✅ done
2. BB84 Pair 1: ceiling / PNS crash / decoy recovery. ✅ done
3. BBM92 Pair 1 (entangled PDC source — Ma–Fung–Lo, Koashi–Preskill
   rate; foreground intrinsic PNS-resistance vs BB84). ← current
4. Pair 2 (intercept-resend) both protocols.
5. Interpretation + optional twist (un-freeze dark counts).

## Validation target
LMC Fig 1 (GYS params): decoy reaches ~140 km, GLLP-bound-only ~30 km,
insecurity upper bound 208 km (where e1 = 1/4).

## Citation discipline
"Verified" = citation confirmed real. Separately, every source must be
*read and paraphrased* in my own words for the paper — never quoted,
never summarized from memory.

## Working rules for code assistance

### Decisions are the student's to make
When there's a modeling fork (which formula variant, which approximation,
whether to include a term), do NOT decide and then report it. Surface the
fork FIRST: state both options, the trade-off, and which the paper uses —
then STOP and let me choose. Khadija evaluates whether I own the reasoning,
so I make the scope/modeling calls, not the assistant.

### One function at a time, understanding-checked
Write one function, cite the source equation number in a comment, then ask
me to explain the terms back before moving on. Do not batch-write multiple
functions ahead.

### Frozen constants — freeze, don't delete
mu, p_dark (dark counts), detector efficiency, misalignment (e_detector),
and error-correction inefficiency f are FROZEN, not removed. They live as
named module-level constants with their values documented. p_dark in
particular MUST stay in the model (it sets the noise floor and Y_0, and
un-freezing it is a planned Milestone-5 twist). Never silently drop or
vary a frozen constant — sweeping any second variable is a deliberate,
one-at-a-time twist I request explicitly.

### Plot the SECURE key rate, never apparent throughput
The whole point (esp. for the PNS crash) is that secure rate can hit zero
while bits still flow. Any rate curve is the secure rate unless I say otherwise.

### Equation provenance
Every key-rate/gain equation coded directly from the source PDF in refs/,
with the equation number in a comment. Never from memory. If the exact and
approximate forms both appear in the source, note which is coded and why.