"""
BB84 device model + GLLP key-rate combiner. This is the BB84 "engine": the
coherent-source Poisson gain model (yields / gains / QBER) and the GLLP
Eq.-11 combiner gllp_key_rate. Protocol-specific curves live in sibling
modules that import from here:
    ceiling.py  -- infinite-decoy ceiling (true Y1/e1 -> gllp_key_rate)
    no_decoy.py -- prior-art GLLP / PNS-crash bound (Eqs. 12, 13)
    decoy.py    -- practical Vacuum+Weak decoy estimators (MQZL)

Cross-protocol infrastructure (binary_entropy, the fiber loss law, and the
shared constants ALPHA/F_EC/Q_SIFT) lives in src/shared.py so BBM92 can reuse
it. Equations coded directly from Lo, Ma & Chen (LMC), "Decoy State Quantum
Key Distribution", arXiv:quant-ph/0411004v4, PRL 94, 230504 (2005).
"""

import os
import sys
# Put src/ on the path so `from shared import ...` resolves when this module is
# run from inside src/bb84/ (shared.py lives one directory up).
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from math import exp, factorial

from shared import binary_entropy, ALPHA_DB_PER_KM, transmittance, F_EC, Q_SIFT, GYS

# --- BB84 device constants ---------------------------------------------------
# Milestone 6b: the SET-EQUAL device knobs (detector efficiency, misalignment,
# per-side background) now come from a DeviceParams object -- the SINGLE source
# of truth shared with BBM92 -- instead of loose per-protocol literals. Default
# is GYS so the LMC Fig. 1 validation / regression numbers are unchanged; a grid
# driver runs this engine on MFL by passing MFL.eta_det/.dark/.e_det into the
# already-parameterized functions below (nothing here is hardwired to GYS but
# these module defaults).
ETA_DET = GYS.eta_det     # Bob's detector efficiency (0.045)
P_DARK = GYS.dark         # per-side background / dark-count probability (1.7e-6)
E_DETECTOR = GYS.e_det    # optical misalignment error per detected photon (0.033)

# mu stays BB84-specific: a Poisson mean PHOTON number (not BBM92's pair mean),
# so it is NOT a shared DeviceParams field. Frozen here for validation; becomes
# an optimized output per distance in Milestone 6c.
MU = 0.5                  # mean photon number per signal pulse (source)


def eta_overall(L, eta_det=ETA_DET, alpha=ALPHA_DB_PER_KM):
    """
    Overall single-photon transmission: channel x detector.

    eta = transmittance(L) * eta_det

    This is the eta that feeds Eq. 6/7 (yield_n, eta_n) and hence the
    whole gain model. Splitting it this way keeps the distance-swept
    channel term (transmittance) separate from the frozen detector term
    (eta_det), so only L moves during a sweep.
    """
    return transmittance(L, alpha) * eta_det

def eta_n(n, eta):
    """
    Transmission efficiency of an n-photon signal.

    LMC Eq. 7:  eta_n = 1 - (1 - eta)^n

    eta is the overall single-photon transmission probability of the
    channel. Each of the n photons independently survives with
    probability eta, so (1 - eta)^n is the chance ALL n are lost;
    eta_n is the complementary chance that at least one arrives.
    """
    return 1 - (1 - eta) ** n


def yield_n(n, eta, p_dark):
    """
    Yield of an n-photon signal: probability Bob registers a detection
    given Alice sent n photons.

    LMC Eq. 6:  Y_n = eta_n + p_dark - eta_n * p_dark  ~=  eta_n + p_dark

    Two independent ways to get a click: (i) a signal photon makes it
    through (prob eta_n), or (ii) a background/dark count fires
    (prob p_dark). The cross term eta_n * p_dark is the chance BOTH
    happen; subtracting it avoids double-counting (inclusion-exclusion).
    LMC drops it as negligible, but we keep it here since it is exact
    and costs nothing.

    For n = 0 this correctly gives Y_0 = p_dark (eta_0 = 0): with no
    photons sent, only the background can fire.
    """
    en = eta_n(n, eta)
    return en + p_dark - en * p_dark


N_MAX = 50   # Poisson-sum truncation; for mu = O(1), terms past ~10 are ~1e-15


def q_mu(mu, eta, p_dark, n_max=N_MAX):
    """
    Overall gain of the signal state: probability Bob registers a
    detection per pulse Alice sends (averaged over the Poisson photon
    number distribution).

    LMC Eq. 2:  Q_mu = sum_n  Y_n * e^{-mu} * mu^n / n!
                     = Y_0 e^-mu + Y_1 e^-mu mu + Y_2 e^-mu mu^2/2 + ...

    Alice's phase-randomized coherent state has a Poisson photon-number
    distribution: p_n = e^-mu mu^n / n! is the probability the pulse
    holds n photons (mu = mean photon number). Each such pulse is
    detected with probability Y_n (Eq. 6), so the gain is the
    Poisson-weighted average of the yields.

    The true sum is infinite; we truncate at n_max. For mu = O(1) the
    Poisson weight decays super-exponentially, so the tail is negligible.
    """
    total = 0.0
    for n in range(n_max + 1):
        p_n = exp(-mu) * mu ** n / factorial(n)
        total += yield_n(n, eta, p_dark) * p_n
    return total


def error_n(n, eta, p_dark, e_detector):
    """
    QBER of an n-photon signal: fraction of detections from n-photon
    pulses that land in the wrong bit value.

    LMC Eq. 8:  e_n = (e_detector * eta_n + (1/2) * p_dark) / Y_n

    Two error sources, divided by the total yield Y_n to turn a rate of
    *wrong* clicks into a *fraction* of all clicks:
      - e_detector * eta_n : detected signal photons that are
        misidentified (optical misalignment, etc.). e_detector is the
        per-photon misalignment error, a frozen constant independent of
        n (GYS value ~0.033, i.e. 3.3%).
      - (1/2) * p_dark : background clicks. A dark count is random, so it
        lands on the wrong bit exactly half the time -> factor 1/2.

    For n = 0 this gives e_0 = ( (1/2) p_dark ) / p_dark = 1/2, matching
    LMC's statement that the vacuum QBER is 50% (a pure coin flip).
    """
    en = eta_n(n, eta)
    return (e_detector * en + 0.5 * p_dark) / yield_n(n, eta, p_dark)



def e_mu(mu, eta, p_dark, e_detector, n_max=N_MAX):
    """
    Overall QBER of the signal state: fraction of ALL of Bob's
    detections (across every photon number) that are erroneous.

    LMC Eq. 3:  Q_mu * E_mu = sum_n  Y_n * e^{-mu} (mu^n/n!) * e_n
      =>        E_mu = ( sum_n  p_n * Y_n * e_n ) / Q_mu

    Each photon-number class contributes error events at rate
    p_n * Y_n * e_n (how often n photons occur, times how often they
    click, times how often that click is wrong). Summing gives the total
    error rate; dividing by the total gain Q_mu turns it into a fraction
    -- the same rate-to-fraction division as in Eq. 8, now at the level
    of the whole signal rather than a single photon number.
    """
    error_events = 0.0
    for n in range(n_max + 1):
        p_n = exp(-mu) * mu ** n / factorial(n)
        error_events += p_n * yield_n(n, eta, p_dark) * error_n(n, eta, p_dark, e_detector)
    return error_events / q_mu(mu, eta, p_dark, n_max)


def e_1(eta, p_dark, e_detector):
    """
    QBER of the single-photon signals: the error rate among detections
    that came from pulses containing exactly one photon.

    This is LMC Eq. 8 evaluated at n = 1:
        e_1 = (e_detector * eta_1 + (1/2) * p_dark) / Y_1

    Note there is NO mu here: the single-photon error rate depends only on
    the channel + detector (eta, p_dark, e_detector), not on the source
    intensity. Changing mu changes HOW OFTEN a pulse holds one photon, not
    how error-prone that one photon is once it arrives.

    IMPORTANT -- what this value is, and what it is NOT:
    e_1 is NOT something Alice and Bob can measure in a real experiment.
    They only ever observe aggregate detector statistics which is the overall
    gain Q_mu (Eq. 2) and overall QBER E_mu (Eq. 3). A click never comes
    labelled with the photon number of the pulse that caused it, so the
    single-photon contribution cannot be isolated by direct measurement.

    What we compute here is the *true* e_1 predicted by the honest channel
    model (no eavesdropper). That is legitimate ONLY for the
    CLEAN engine, where we trust the device model and ask "what rate would
    the physics give?" -- it is the optimistic ceiling. In the real
    security analysis e_1 must instead be an *upper bound*:
      - GLLP-only (no decoy): assume the worst case Eve could arrange
        -> pessimistic bound, the ~40 km crash curve.
      - Decoy states (Milestone 2, MQZL): vary mu to get several
        (Q_mu, E_mu) equations and tightly *estimate* Y_1 and e_1
        -> the ~142 km curve.
    Same symbol, three different ways of pinning it down.
    """
    return error_n(1, eta, p_dark, e_detector)


def q_1(mu, eta, p_dark):
    """
    Gain of the single-photon signal: probability that Alice sent
    exactly one photon AND Bob detected it, per pulse.

    LMC Eq. 10:  Q_1 = Y_1 * mu * e^{-mu}

    This is just the n = 1 term of the Q_mu sum (Eq. 2): the Poisson
    weight p_1 = mu * e^{-mu} that a pulse holds exactly one photon,
    times the yield Y_1 that such a pulse clicks. Single-photon pulses
    are the ONLY ones unconditionally secure (Eve cannot split them),
    so Q_1 is the part of the raw key that can survive privacy
    amplification -- the numerator of the "good" term in Eq. 11.
    """
    p_1 = mu * exp(-mu)
    return yield_n(1, eta, p_dark) * p_1


def gllp_key_rate(Q_mu, E_mu, Q_1, e1, f=F_EC, q=Q_SIFT):
    """
    GLLP secure key rate per pulse -- the shared Eq. 11 combiner.

    LMC Eq. 11:
        S >= q { -Q_mu * f(E_mu) * H2(E_mu)  +  Q_1 * [1 - H2(e_1)] }

    This takes the four already-computed ingredients and combines them; it
    does NOT know or care HOW Q_1 and e_1 were obtained. That is the whole
    point of factoring it out: the ceiling curve feeds it the TRUE single-
    photon values, while the decoy curve feeds it MQZL-ESTIMATED lower/upper
    bounds (Q_1^L, e_1^U) -- same security formula, different estimates.

      good term:  Q_1 * [1 - H2(e_1)]   -- secure bits distilled from the
                  single-photon pulses (the only unconditionally secure
                  ones): how many arrive (Q_1) times the fraction that
                  survives privacy amplification, 1 - H2(e_1).

      cost term:  -Q_mu * f * H2(E_mu)  -- bits spent on error correction
                  over ALL detected pulses (Q_mu). H2(E_mu) is the Shannon
                  cost of reconciling a channel at QBER E_mu; f >= 1 inflates
                  it for real (inefficient) codes.

    Provenance note: LMC write the correction term as f(E_mu), a FUNCTION of
    the QBER. We freeze f to the constant F_EC = 1.22 (the standard GYS /
    Cascade value, as used by MQZL), so f is passed as a scalar here, not
    evaluated at E_mu.

    Returns the RAW bound, which can go NEGATIVE once the cost term overtakes
    the good term. A negative value means no secure key is extractable; the
    sign change marks the maximum secure distance. Clamping to max(0, .) is
    left to the caller so the sweep layer can locate that crossing.
    """
    cost = Q_mu * f * binary_entropy(E_mu)
    good = Q_1 * (1 - binary_entropy(e1))
    return q * (good - cost)
