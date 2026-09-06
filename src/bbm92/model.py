"""
BBM92 (entanglement-based BB84) device model + Koashi-Preskill key rate.

Source: Ma, Fung & Lo (MFL), "Quantum key distribution with entangled photon
sources", arXiv:quant-ph/0703122v1. Equations coded directly from that paper.

Why BBM92 gets its OWN rate formula (approach A, not the BB84 GLLP engine):
the entangled PDC source is BASIS-INDEPENDENT, so Koashi-Preskill security
(MFL Eq. 11) bounds the phase error directly from the measured bit error
(delta_p = delta_b = E_lambda) and privacy-amplifies over the WHOLE key --
using only the overall gain/QBER (Q_lambda, E_lambda), with NO single-photon
isolation.

Why this makes BBM92 intrinsically PNS-RESISTANT (the finding to foreground):
The PNS attack works on BB84 because a weak coherent pulse SOMETIMES contains
>1 identical photon that Eve can split off and keep, and Alice cannot tell.
That is a basis-DEPENDENT leak, which is exactly why GLLP must throw away all
multi-photon events and keep only the single-photon term Q1[1-H2(e1)].
A BBM92 entangled pair has no such "extra copy for Eve": security rides on the
correlations of the shared state, which are basis-independent. Multi-photon-
pair emissions do not hand Eve free information the way PNS does -- they only
add NOISE (double clicks -> e0 = 1/2), which shows up in the measured QBER and
is already paid for by the H2(E_lambda) terms. So BBM92 needs no decoy states
to survive PNS: the same overall-Q/E formula that runs it is already secure.
The plot will show this as a single BBM92 curve that does NOT crash the way
BB84-without-decoy does.

Shared infrastructure (binary_entropy, fiber loss law, F_EC/Q_SIFT) is imported
from src/shared.py.
"""

import os
import sys
# Put src/ on the path so `from shared import ...` resolves when run from
# inside src/bbm92/ (shared.py lives one directory up).
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared import binary_entropy, transmittance, ALPHA_DB_PER_KM, F_EC, Q_SIFT, MFL

# --- BBM92 device constants --------------------------------------------------
# Milestone 6b: the SET-EQUAL device knobs (detector efficiency, misalignment,
# per-side background) now come from a DeviceParams object -- the SAME single
# source of truth BB84 uses -- instead of loose literals. Default is MFL so the
# standalone 144 km sweep is unchanged; the grid driver runs this engine on GYS
# by passing GYS.eta_det/.dark/.e_det into the already-parameterized
# bbm92_key_rate below. This is what removes the draft-1 confound (BB84 was on
# GYS, BBM92 on MFL): a grid COLUMN now feeds identical device knobs to both.
ETA_DET = MFL.eta_det   # detection efficiency per box (detector + optics,
                        # channel loss applied separately in eta_arms) = 0.145
ED = MFL.e_det          # intrinsic detector error rate ed (0.015) = BB84 e_detector
Y0_BG = MFL.dark        # per-side background count rate -> Y0A = Y0B = Y0_BG (6.02e-6)

# mu is BBM92-specific: a THERMAL mean photon-PAIR number mu = 2*lam (MFL Eq. 5),
# NOT BB84's Poisson photon mean, so it is NOT a shared DeviceParams field.
#
# WHY 0.053: it is the REALISTIC measured brightness of the actual 144 km
# free-space PDC experiment MFL simulate (their ref [43]). MFL state that in the
# realistic case mu "cannot be set freely" and fix mu = 2*lam = 0.053 (paper
# text, "In the realistic case ... mu = 2*lam = 0.053"). They also find the rate
# is STABLE in mu: the theoretical optimum is mu = O(1), but it beats mu = 0.053
# by only ~1 dB. So 0.053 is a faithful experimental value, not an arbitrary one.
#
# This is the DEFAULT/fixed brightness, kept by two consumers: the standalone
# BBM92 144 km sweep, and E91 (chsh.py). E91 keeps it FIXED rather than optimized
# because E91 has no key rate -- its only mu objective would be min-QBER, and that
# is degenerate: QBER falls monotonically as mu drops until dark-count accidentals
# take over near mu ~ 4e-5, so "optimizing" just parks the source at that
# near-off floor for ~2-4 km of extra S=2 reach. (This is the OPPOSITE direction
# from the rate-optimal mu, which is LARGER because the rate rewards brightness
# with gain; QBER has no such reward.) The cross-protocol GRID OVERRIDES this
# default, optimizing mu per distance per Milestone 6c (BBM92 mu*(0) ~ 0.08-0.12)
# and passing mu into bbm92_key_rate explicitly.
MU = 0.053           # realistic 144 km PDC brightness mu = 2*lam [MFL, ref 43]


def p_pair(n, lam):
    """
    Probability that the PDC source emits an n-photon-PAIR in one pump pulse.

    MFL Eq. 5:  P(n) = (n + 1) * lam^n / (1 + lam)^(n + 2)

    lam = sinh^2(chi) is the PDC parameter; the expected pair number (source
    brightness) is mu = 2*lam.

    KEY CONTRAST with BB84: a coherent source has a POISSON photon-number
    distribution, P(n) = e^-mu mu^n/n!. A PDC source is THERMAL (per mode):
    Eq. 5 is broader and heavier-tailed than Poisson at the same mean, so the
    PDC source actually emits MORE multi-pair events. That would be alarming
    if BBM92 had a PNS weakness -- but it does not (see module docstring), so
    the extra multi-pairs cost only QBER (noise), not security.
    """
    return (n + 1) * lam ** n / (1 + lam) ** (n + 2)


def eta_arms(L, eta_det, placement, alpha=ALPHA_DB_PER_KM):
    """
    Single-photon transmission on Alice's and Bob's arms: returns (etaA, etaB).

    MFL Sec. III.B: etaA, etaB each fold in the channel loss AND the detector
    (+coupling) efficiency for that arm. Detection is a COINCIDENCE, so both a
    photon on Alice's side AND its partner on Bob's side must survive.

    The two placements (both simulated by MFL, this is the modeling fork):
      placement='middle' -- PDC source sits midway, so EACH arm carries L/2 of
          fiber: etaA = etaB = eta_det * transmittance(L/2). Symmetric.
      placement='alice'  -- source is at Alice, her photon is detected locally
          (no fiber): etaA = eta_det; Bob's photon crosses the FULL L:
          etaB = eta_det * transmittance(L). Mirrors BB84's one-sided channel.

    Why 'middle' tolerates more loss: the coincidence needs BOTH arms, and the
    total signal transmittance etaA*etaB = eta_det^2 * 10^(-alpha*L/10) is the
    SAME for both placements. But dark counts compete per ARM: 'middle' keeps
    each arm at only L/2 of loss, so each arm's signal stays well above its
    background longer, pushing the noise-limited cutoff farther out. 'alice'
    lets Bob's arm take the full loss, so his side hits the dark-count floor
    sooner -- but it is the clean apples-to-apples match to the BB84 curves.
    """
    if placement == "middle":
        t = transmittance(L / 2, alpha)
        return eta_det * t, eta_det * t
    elif placement == "alice":
        return eta_det, eta_det * transmittance(L, alpha)
    raise ValueError(f"placement must be 'middle' or 'alice', got {placement!r}")


def yield_n(n, etaA, etaB, Y0A, Y0B):
    """
    Yield of an n-photon-pair: probability of a COINCIDENCE detection (both
    Alice and Bob click) given the PDC source emitted exactly n pairs.

    MFL Eq. 7:
        Yn = [1 - (1 - Y0A)(1 - etaA)^n] * [1 - (1 - Y0B)(1 - etaB)^n]
             |---------- Alice clicks ----------| |--------- Bob clicks ---------|

    Each bracket is 1 - P(that detector stays dark). A detector stays dark only
    if BOTH no dark count fires (factor 1 - Y0) AND all n of that arm's photons
    are lost (factor (1 - eta)^n). So it clicks if a dark count fires OR at
    least one photon arrives. The two arms are assumed independent, so the
    coincidence probability is the product.

    n = 0 (vacuum) gives Yn = [1-(1-Y0A)][1-(1-Y0B)] = Y0A * Y0B = Y0, the
    vacuum yield: a coincidence from pure dark counts on both sides.
    """
    click_A = 1 - (1 - Y0A) * (1 - etaA) ** n
    click_B = 1 - (1 - Y0B) * (1 - etaB) ** n
    return click_A * click_B


def q_lambda(lam, etaA, etaB, Y0A, Y0B):
    """
    Overall gain Q_lambda: probability of a coincidence detection per PUMP
    PULSE (averaged over the thermal pair-number distribution P(n), Eq. 5).

    MFL Eq. 9 -- the CLOSED FORM of the sum Q_lambda = sum_n Yn * P(n):
        Q_lambda = 1
                 - (1 - Y0A) / (1 + etaA*lam)^2
                 - (1 - Y0B) / (1 + etaB*lam)^2
                 + (1 - Y0A)(1 - Y0B) / (1 + etaA*lam + etaB*lam - etaA*etaB*lam)^2

    Provenance: MFL derive and PRINT this closed form and state they use it in
    the simulation, so we code it verbatim (exact, no Poisson-style truncation)
    rather than the numerical sum. The truncated sum sum_n Yn*P(n) is kept only
    as an independent validation cross-check (see the sanity test).

    Structure mirrors the coincidence (Eq. 7): the two single-arm subtraction
    terms are the "only Alice missed / only Bob missed" corrections, and the
    final add-back term is inclusion-exclusion for "both missed" -- the thermal
    analogue of Q_mu for BB84, but two-sided.
    """
    a = (1 - Y0A) / (1 + etaA * lam) ** 2
    b = (1 - Y0B) / (1 + etaB * lam) ** 2
    c = (1 - Y0A) * (1 - Y0B) / (1 + etaA * lam + etaB * lam - etaA * etaB * lam) ** 2
    return 1 - a - b + c


# e0 = 1/2 is the error rate of a background (dark-count) coincidence: it is
# uncorrelated with Alice's bit, so it is wrong exactly half the time (MFL,
# App. A). A double click is also assigned a random bit -> e0 = 1/2 as well.
E0 = 0.5


def e_lambda(lam, etaA, etaB, Y0A, Y0B, ed, Q_lam=None, e0=E0):
    """
    Overall QBER E_lambda: fraction of coincidence detections that carry the
    wrong bit, averaged over the thermal distribution.

    MFL Eq. 10 (given in the E_lambda * Q_lambda form):
        E_lambda * Q_lambda = e0 * Q_lambda
            - 2(e0 - ed) * etaA*etaB*lam*(1+lam)
              / [ (1+etaA*lam)(1+etaB*lam)(1+etaA*lam+etaB*lam-etaA*etaB*lam) ]

    so E_lambda = (that RHS) / Q_lambda.

    Reading it: e0*Q_lambda is the "everything is a coin flip" baseline (if
    every coincidence were random noise, QBER would be e0 = 1/2). The
    subtracted term is the CORRELATION the true entangled signal restores:
    genuine single-pair coincidences agree except for the intrinsic
    misalignment ed, so they pull the error rate down from e0 toward ed. The
    (e0 - ed) factor is exactly "how much better than a coin flip" a real
    signal detection is; it is weighted by the signal coincidence rate
    (the etaA*etaB*lam... factor). As distance grows, that signal factor
    shrinks, less is subtracted, and E_lambda climbs back up toward e0 = 1/2
    -- the noise-dominated regime that kills the key.

    ed is the intrinsic detector/misalignment error (the BBM92 analogue of
    BB84's e_detector). Q_lam may be passed in to avoid recomputing Eq. 9.
    """
    if Q_lam is None:
        Q_lam = q_lambda(lam, etaA, etaB, Y0A, Y0B)
    denom = ((1 + etaA * lam) * (1 + etaB * lam)
             * (1 + etaA * lam + etaB * lam - etaA * etaB * lam))
    signal_term = 2 * (e0 - ed) * etaA * etaB * lam * (1 + lam) / denom
    return (e0 * Q_lam - signal_term) / Q_lam


def koashi_preskill_key_rate(Q_lam, E_lam, f=F_EC, q=Q_SIFT):
    """
    Secure key rate per pulse for BBM92 -- the Koashi-Preskill combiner.

    MFL Eq. 11 (with delta_b = delta_p = E_lam from Eq. 12):
        R >= q * Q_lam * [ 1 - f(E_lam)*H2(E_lam) - H2(E_lam) ]

    Compare BB84's GLLP combiner gllp_key_rate:
        GLLP:            R = q{ Q1[1-H2(e1)] - Q_mu f H2(E_mu) }
        Koashi-Preskill: R = q  Q_lam[ 1 - f H2(E_lam) - H2(E_lam) ]

    The two H2 terms:
      - f * H2(E_lam)  -- ERROR CORRECTION cost (bit error delta_b = E_lam),
        inflated by the code inefficiency f.
      - H2(E_lam)      -- PRIVACY AMPLIFICATION cost (phase error delta_p).

    THE KEY POINT (why BBM92 is PNS-resistant, coded right here): there is NO
    single-photon isolation -- no Q1, no e1. The rate uses only the OVERALL
    gain Q_lam and OVERALL QBER E_lam. This is legal because the entangled PDC
    source is BASIS-INDEPENDENT, so Koashi-Preskill can set the phase error
    delta_p equal to the measured bit error delta_b = E_lam (Eq. 12, from the
    X/Z measurement symmetry). Privacy amplification then runs over the WHOLE
    sifted key at rate H2(E_lam). Multi-photon-pair events are not thrown away
    (as GLLP must); they are already paid for inside E_lam. That is exactly
    why BBM92 needs no decoy states to survive PNS.

    Consequence: R hits 0 when 1 - (1+f)H2(E_lam) = 0, i.e. H2(E_lam)=1/(1+f).
    With f=1.22 that is E_lam ~ 9.9%; at the Shannon limit f=1 it is the
    famous ~11% entanglement-QKD error threshold.

    Returns the RAW bound (may be negative past the cutoff), same convention
    as the BB84 rates.
    """
    h = binary_entropy(E_lam)
    return q * Q_lam * (1 - f * h - h)


def bbm92_key_rate(L, placement, mu=MU, eta_det=ETA_DET, ed=ED, y0=Y0_BG,
                   f=F_EC, q=Q_SIFT, alpha=ALPHA_DB_PER_KM):
    """
    BBM92 secure key rate per pulse at distance L (km) for a source placement.

    The endpoint that ties the model together, one distance at a time:
        eta_arms (placement) -> Q_lambda (Eq. 9), E_lambda (Eq. 10)
        -> koashi_preskill_key_rate (Eq. 11).

    lam = mu/2; Y0A = Y0B = y0 (per-detector background, MFL Table I).
    placement is 'middle' (source midway, each arm L/2) or 'alice' (source at
    Alice, Bob's arm carries the full L). Returns the RAW bound (may be < 0
    past the cutoff), same convention as the BB84 rates.
    """
    lam = mu / 2
    etaA, etaB = eta_arms(L, eta_det, placement, alpha)
    Q = q_lambda(lam, etaA, etaB, y0, y0)
    E = e_lambda(lam, etaA, etaB, y0, y0, ed, Q_lam=Q)
    return koashi_preskill_key_rate(Q, E, f=f, q=q)
