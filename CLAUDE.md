# QKD Attack–Defense Analysis — Project Context

*Revised Aug 2026 after mentor feedback on draft 1. Scope expanded from two protocols
to three; μ reclassified from frozen constant to optimized output. Both changes are
deliberate and supersede the previous version.*

## What this is
A from-scratch Python simulator for a Lumiere research paper.
Research question: *How do characteristic attacks and matched
defenses change the secret key rate of BB84 and BBM92 across
channel loss, and what determines the kind of defense each needs?*

## Commands

Setup (once): `pip install -r requirements.txt` (only numpy + matplotlib).

Every sweep script is a `__main__` that regenerates a PNG into `figures/` and prints
the cutoff distances. **Scripts rely on `sys.path` inserts relative to their own
location, so `cd` into the script's directory first** (imports like `from keyrate import ...`
are bare, not package-qualified):

```bash
cd src/bb84 && python3 sweep.py     # BB84 Pair-1 3-curve figure + cutoffs
cd src/bbm92 && python3 sweep.py    # BBM92 both-placement figure + cutoffs
cd src   && python3 compare.py      # cross-protocol BB84-vs-BBM92 overlay
```

There is no test runner. **The regression guard is the printed cutoff table** — after any
change to the engine, `cd src/bb84 && python3 sweep.py` must still print (fixed-μ GYS mode):
`ceiling ≈ 141.8`, `decoy ≈ 138.8`, `no-decoy crash ≈ 40.2`, `insecurity (e₁=¼) ≈ 207.7` km.
These are the Milestone-6a assertions; if they move, the refactor broke something.

Module import self-checks (used during development, no output = pass):
```bash
cd src/bb84 && python3 -c "import shared,keyrate,ceiling,no_decoy,decoy,sweep; print('OK')"
```

`refs/` holds the source PDFs and is **git-ignored** (see Equation-provenance rule); read
equations from them with `pdftotext -f <pg> -l <pg> refs/<file>.pdf -`.

## Code architecture

Two protocol engines over one shared infrastructure module. The split is deliberate
(approach A): BB84 and BBM92 share the *device/loss/entropy* layer but **not** the
key-rate combiner — see the Scope table for why (basis-dependent vs basis-independent).

```
src/shared.py         binary_entropy · transmittance (fiber loss) · ALPHA/F_EC/Q_SIFT
  │                   the ONLY cross-protocol code. Both engines import from it.
  ├── src/bb84/       Poisson/WCP engine → GLLP combiner (LMC Eq. 11)
  │     keyrate.py      device model (Y_n,Q_μ,E_μ,Q_1,e_1) + gllp_key_rate combiner ← hub
  │     ceiling.py      infinite-decoy ceiling: TRUE Y_1/e_1 → gllp_key_rate
  │     no_decoy.py     PNS-crash bound (Ω, Eq.12/13) + optimize_no_decoy (μ-scan)
  │     decoy.py        Vacuum+Weak decoy estimators (MQZL 34/35/37) → gllp_key_rate
  │     sweep.py        distance sweep + Pair-1 figure
  └── src/bbm92/      thermal/SPDC engine → Koashi–Preskill combiner (MFL Eq. 11)
        model.py        pair stats · eta_arms(placement) · Q_λ,E_λ · koashi_preskill + bbm92_key_rate
        sweep.py        distance sweep + both-placement figure
src/compare.py        imports both engines, draws the qualitative overlay
```

Key structural facts to know before editing:
- **`gllp_key_rate` (keyrate.py) is the shared BB84 combiner.** ceiling / no_decoy / decoy
  all differ ONLY in *how they pin Q_1 and e_1* (true value / worst-case Ω / MQZL bounds),
  then call the same combiner. Change the security formula in one place.
- **Every rate function returns the RAW signed bound** (may go negative past the cutoff).
  Clamping/masking to `NaN` and locating the zero-crossing (`cutoff_distance`) is the
  sweep layer's job — never clamp inside a rate function; the sign change *is* the result.
- **The single swept variable is distance L.** Everything else is a frozen module-level
  constant (per the Frozen-constants rule) except μ, which is optimized only in
  `no_decoy.optimize_no_decoy`. GYS constants live in `bb84/keyrate.py`; MFL 144 km
  constants live in `bbm92/model.py` — they intentionally differ (see Milestone 6).
- **BBM92 `placement`** (`"middle"` vs `"alice"`) is the source-geometry fork in
  `eta_arms`; `"alice"` mirrors BB84's one-sided loss and is the Milestone-6d primary.

## Scope (current — expanded once, deliberately)

Three protocols. Two are fully computed; the third is partially computed.

| Protocol | Source | Security check | Computed? |
|---|---|---|---|
| BB84 | WCP, Poisson | QBER | Full — ceiling / PNS crash / decoy recovery |
| BBM92 | SPDC, thermal | QBER | Full — Koashi–Preskill rate, no decoy |
| E91 | SPDC, thermal | CHSH value S | **S(L) curve only — no key rate** |

BB84 and BBM92 share QBER-based *infrastructure* (binary entropy, channel/loss model,
frozen constants, the sweep/plot harness) but use **protocol-specific key-rate formulas**
— NOT one common combiner:

- **BB84 → GLLP** (LMC Eq. 11): must isolate the single-photon term `Q1[1−H2(e1)]`
  because the coherent source is basis-*dependent* and leaks multi-photon pulses to Eve
  (the PNS problem).
- **BBM92 → Koashi–Preskill** (Ma–Fung–Lo Eq. 11): uses only the *overall* gain/QBER
  `Qλ, Eλ` (δb=δp=Eλ), no single-photon isolation, because the entangled PDC source is
  basis-*independent*. This is *why* BBM92 is intrinsically PNS-resistant and needs no
  decoy — a key finding to foreground in the write-up and the plot.
- **E91** reuses the BBM92 device layer unchanged. The only new object is S as a function
  of distance. See §"Why E91 gets no key rate" — that is a decided question, not open.

Two attack–defense pairs:
- Pair 1: PNS attack → decoy-state defense (QBER-*invisible*).
- Pair 2: intercept-resend → QBER-threshold/privacy-amplification defense (QBER-*visible*).

Swept variable: distance / channel loss (L). See §"Frozen constants" for what is held
fixed and what is now optimized.

Output: secure key rate R vs distance — plot the SECURE rate, never apparent throughput.

## Code conventions
- All key-rate equations coded **directly from the source paper**, never from memory or
  reconstruction. Cite the equation number in a comment (e.g. `# LMC Eq. 6`).
- Primary engine source: Lo–Ma–Chen (LMC), arXiv:quant-ph/0411004v4, PRL 94 230504 (2005)
  — Eqs 2,3,6,7,8,9,10,11.
- Decoy Y1/e1 estimators: Ma–Qi–Zhao–Lo (MQZL), quant-ph/0503005v5 (the "how" to LMC's
  "why"). Vacuum+Weak forms: §3.4 Eqs. 33,34,35,37.
- BBM92 / entangled PDC source + Koashi–Preskill rate: Ma–Fung–Lo (MFL),
  quant-ph/0703122v1 — Eqs. 5,6,7,8,9,10,11,12 (+ App. A for e1).
- E91 / CHSH: sources **not yet verified**. See Milestone 7 — blocked until pulled.
- Frozen physical constants live as named module-level constants, not magic numbers, so
  they can be un-frozen as deliberate "twists".

## Build order (Milestones)
1. GLLP engine (clean protocol). ✅ done
2. BB84 Pair 1: ceiling / PNS crash / decoy recovery. ✅ done
3. BBM92 Pair 1 (entangled PDC source — MFL, Koashi–Preskill rate; foreground intrinsic
   PNS-resistance vs BB84). ✅ done
4. Pair 2 (intercept-resend) both protocols.
5. Interpretation + optional twist (un-freeze dark counts).
6. **Parameter control — the 2×2 grid.** ← current, blocks everything downstream
7. **E91 as S(L).** Gated on Milestone 6 confirmation + source verification.

---

## Milestone 6 — Parameter control (do first)

The draft-1 cross-protocol comparison is confounded: BB84 on GYS (η=0.045, e_d=0.033,
Y₀=1.7e-6), BBM92 on MFL (η=0.145, e_d=0.015, bg=6.02e-6). Mentor instruction: "keep all
the same parameters, if not justify why."

### 6a. Regression guard — write these assertions BEFORE touching anything
In fixed-μ GYS mode these must not move: BB84 ceiling ≈ 141.8 km, decoy ≈ 138.8 km,
undefended ≈ 40.2 km, e₁ = ¼ bound ≈ 207.7 km.

### 6b. Shared vs protocol-specific parameters
Set equal — same physical device property:
`alpha`, `eta_det`, `e_d`/`e_detector`, background/dark count **per detector**, `f_EC`.

Do **not** set equal; document why in a comment:
- **Detection topology.** BB84 one-sided; BBM92 requires a coincidence. Gain scales as η
  for BB84, roughly η_A·η_B for BBM92. Structural, not a parameter.
- **Detector count.** 2 vs 4. Background enters per detector, so totals differ even at
  equal per-detector rate.
- **μ.** BB84's μ is a Poisson mean *photon* number; BBM92's μ = 2λ is a mean *pair*
  number under thermal statistics. Different physical quantities — setting them equal is
  meaningless.

### 6c. μ becomes an optimized output
Optimize μ per protocol, per distance, maximizing secure rate. Already done for the
undefended BB84 curve; extend to every curve.

This **supersedes** the previous frozen-μ rule for cross-protocol runs, and is the actual
answer to "keep the same parameters" — μ stops being an assumption, so there is nothing to
hold equal. Keep a fixed-μ mode available for the LMC/MQZL validation figures.

### 6d. Run the grid
`{BB84, BBM92} × {GYS, MFL}` = four configurations. Report max secure distance and
zero-distance rate as a table. BBM92 uses **source-at-Alice** for all grid runs — now the
primary configuration, matching BB84's one-sided loss geometry. Symmetric placement stays
a separate secondary result about loss geometry only.

**Expected:** at GYS parameters BBM92's reach falls *below* BB84-with-decoy, because
coincidence detection costs roughly (0.045/0.145)² ≈ 10× in gain while the dark-count floor
is unchanged. If BBM92 still wins at matched parameters, stop and investigate — likely a bug
in arm transmittance or background-per-detector handling. Either outcome is fine for the
paper; the thesis is "BBM92 needs no decoy patch," not "BBM92 reaches farther."

---

## Milestone 7 — E91 as S(L)

Reuse the BBM92 device layer unchanged. It already yields E(L). Map E to the CHSH value S,
plot S vs distance, report the S = 2 crossing.

**Blocked until sources are verified.** Do not code an S–QBER relation from memory.
Candidates to pull into `refs/`: Ekert PRL **67**, 661 (1991); Acín *et al.* PRL **98**,
230501 (2007); Pironio *et al.* NJP **11**, 045021 (2009). All three unverified.

**Modeling fork — surface, do not decide.** The clean QBER→CHSH map assumes a depolarizing
channel. Dark counts are not depolarizing; they degrade visibility by a different mechanism.
Options: (1) adopt the depolarizing approximation and state it, or (2) model visibility
directly from the coincidence statistics already in the BBM92 gain model. Present both with
costs. Do not pick one.

**Reporting caveat:** S = 2 is *not* a key-rate cutoff — it is where entanglement stops being
certifiable, and the rate may already be zero well before it. Any table or figure comparing
the E91 Bell cutoff to BB84/BBM92 key-rate cutoffs must label them as different quantities.

### Why E91 gets no key rate (decided — do not reopen)
A device-independent rate is only valid with the detection loophole closed. Loophole-free
CHSH requires detector efficiency around 83% for maximally entangled states, or roughly 67%
with the Eberhard non-maximal construction — **verify both against Garg–Mermin (1987) and
Eberhard (1993) before either number appears anywhere.** Both parameter sets here are 4.5%
and 14.5%, so a loophole-free DI rate is identically zero at every distance. The function
would return a flat line at zero. Delivered as a stated bound instead.

**Consistency requirement:** the BBM92/E91 device model post-selects on coincidences — which
is precisely the detection loophole Jogenfors *et al.* (2015) exploit. Any E91 output must be
labelled as computed under the fair-sampling assumption. Do not silently assume it away.

---

## Validation target
LMC Fig 1 (GYS params): decoy reaches ~140 km, GLLP-bound-only ~30 km, insecurity upper
bound 208 km (where e1 = 1/4). Reproduce in fixed-μ mode.

## Citation discipline
"Verified" = citation confirmed real. Separately, every source must be *read and paraphrased*
in my own words for the paper — never quoted, never summarized from memory.

## Working rules for code assistance

### Do not write paper prose
Not abstracts, not sections, not captions, not "here's a sentence you could use." I am
submitting to Regeneron STS, whose attestation bars AI from drafting the paper. Permitted:
code, comments, docstrings, numeric tables, figure *code*, terse factual summaries of what a
run produced. Nothing that lands in the .tex as authored text.

### Decisions are the student's to make
When there's a modeling fork (which formula variant, which approximation, whether to include
a term), do NOT decide and then report it. Surface the fork FIRST: state both options, the
trade-off, and which the paper uses — then STOP and let me choose. Khadija evaluates whether
I own the reasoning, so I make the scope/modeling calls, not the assistant.

### One function at a time, understanding-checked
Write one function, cite the source equation number in a comment, then ask me to explain the
terms back before moving on. Do not batch-write multiple functions ahead.

### Frozen constants — freeze, don't delete
`p_dark` (dark counts), detector efficiency, misalignment (`e_detector`), and
error-correction inefficiency `f` are FROZEN, not removed. They live as named module-level
constants with values documented. `p_dark` in particular MUST stay in the model (it sets the
noise floor and Y_0, and un-freezing it is a planned Milestone-5 twist). Never silently drop
or vary a frozen constant — sweeping any second variable is a deliberate, one-at-a-time twist
I request explicitly.

**`mu` is no longer in this list.** As of Milestone 6 it is an optimized output for
cross-protocol runs. A fixed-μ mode is retained for validation only.

### No new physics without a source
If a relation is needed and not in `refs/`, the task is blocked, not improvised.

### Plot the SECURE key rate, never apparent throughput
The whole point (esp. for the PNS crash) is that secure rate can hit zero while bits still
flow. Any rate curve is the secure rate unless I say otherwise.

### Equation provenance
Every key-rate/gain equation coded directly from the source PDF in `refs/`, with the equation
number in a comment. Never from memory. If the exact and approximate forms both appear in the
source, note which is coded and why.

### Order of work
1. Regression assertions (6a)
2. Shared-parameter refactor (6b)
3. μ optimization (6c)
4. 2×2 grid + table (6d)
5. **Report numbers, stop, wait for confirmation**
6. Pull and verify E91 sources
7. Surface the depolarizing fork
8. S(L) implementation

Do not start step 6 before step 5 is confirmed. Every number in the paper moves at step 4.
