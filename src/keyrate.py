"""
GLLP secret-key-rate engine for BB84 

Equations coded directly from Lo, Ma & Chen (LMC),
"Decoy State Quantum Key Distribution",
arXiv:quant-ph/0411004v4, PRL 94, 230504 (2005).
Equation numbers in comments refer to that paper unless noted otherwise
(the no-decoy mu optimization cites MQZL, quant-ph/0503005).

Milestone 1: clean-protocol engine (Eqs. 2,3,6,7,8,10,11).
Milestone 2 Pair 1: no-decoy GLLP/PNS-crash bound (Eqs. 12,13) + per-distance
mu optimization (optimize_no_decoy). Practical decoy ESTIMATION (MQZL
Y1^L/e1^U estimators) is not implemented yet -- the current "decoy" ceiling
is the infinite-decoy limit (true Y1/e1 via secret_key_rate).
"""

from math import log2, log10, exp, factorial


def binary_entropy(x):
    """
    Binary Shannon entropy H2(x) = -x log2(x) - (1-x) log2(1-x).

    Definition used inside LMC Eq. 11.
    H2(0) = H2(1) = 0 by the limit x*log2(x) -> 0 as x -> 0:
    a certain outcome carries no uncertainty. if equal to 0 or 1, more certain 
    """
    if x <= 0 or x >= 1:
        return 0.0
    return -x * log2(x) - (1 - x) * log2(1 - x)

''' --- Frozen physical constants (GYS experiment, LMC Fig. 1 validation) ---
 Named per project convention so they can be deliberately un-frozen as
 "twists" later. Values are the GYS parameter set LMC validate against.'''
ALPHA_DB_PER_KM = 0.21    # GYS fiber loss coefficient (dB/km), MQZL Table 1.
                          # Was 0.20 (rounded); corrected to the sourced GYS
                          # value. Reach ~ 1/alpha, so this shift lands the
                          # Fig.1 validation: insecurity bound -> 208 km exact,
                          # decoy reach -> 142 km (~140).
ETA_DET = 0.045           # Bob's detector efficiency (dimensionless)
P_DARK = 1.7e-6           # dark-count probability per pulse
E_DETECTOR = 0.033        # optical misalignment error (per detected photon)
MU = 0.5                  # mean photon number per signal pulse (source)
F_EC = 1.22               # error-correction inefficiency f(E) >= 1
Q_SIFT = 0.5              # basis-sifting factor q in LMC Eq. 11.
                          # 1/2 = standard BB84 (half the pulses land in a
                          # mismatched basis and are discarded). LMC's Fig. 1
                          # instead uses q = 1 (efficient BB84), so our curves
                          # sit a factor of 2 lower in R -- but at the SAME
                          # cutoff distances, since q is only a prefactor.
                          # Frozen here; flip to 1.0 as a deliberate twist.


def transmittance(L, alpha=ALPHA_DB_PER_KM):
    """
    Channel transmittance: probability a photon survives L km of fiber.
    Standard model: eta_channel = 10 ** (-alpha * L / 10)
    Detector efficiency is NOT included here — it's multiplied in at the
    gain-model stage (per project decision). This is the single swept
    variable (via L).
    """
    return 10 ** (-alpha * L / 10)


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


def secret_key_rate(mu, eta, p_dark, e_detector, f=F_EC, q=Q_SIFT):
    """
    Secure key rate per pulse for the clean BB84 protocol (no eavesdropper).

    LMC Eq. 11:
        S >= q { -Q_mu * f(E_mu) * H2(E_mu)  +  Q_1 * [1 - H2(e_1)] }

    This is the engine endpoint: given the frozen device params and the
    overall transmission eta (which is the single distance-swept quantity),
    it assembles the four ingredients built above and combines them.

      good term:  Q_1 * [1 - H2(e_1)]   -- secure bits distilled from the
                  single-photon pulses (the only unconditionally secure
                  ones). How many arrive (Q_1, Eq. 10) times the fraction
                  that survives privacy amplification, 1 - H2(e_1).

      cost term:  -Q_mu * f * H2(E_mu)  -- bits spent on error correction
                  over ALL detected pulses (Q_mu, Eq. 2). H2(E_mu) is the
                  Shannon cost of reconciling a channel at QBER E_mu; f >= 1
                  inflates it for real (inefficient) codes.

    Provenance note: LMC write the correction term as f(E_mu), a FUNCTION of
    the QBER. We freeze f to the constant F_EC = 1.22 (the standard GYS /
    Cascade value, as used by MQZL), per project convention -- so f is passed
    as a scalar here, not evaluated at E_mu.

    Returns the RAW bound, which can go NEGATIVE once the cost term overtakes
    the good term. A negative value means no secure key is extractable (the
    protocol is insecure at that distance); the sign change marks the maximum
    secure distance. Clamping to max(0, .) is left to the caller so the sweep
    layer can locate that crossing.
    """
    Q_mu = q_mu(mu, eta, p_dark)
    E_mu = e_mu(mu, eta, p_dark, e_detector)
    Q_1 = q_1(mu, eta, p_dark)
    e1 = e_1(eta, p_dark, e_detector)

    cost = Q_mu * f * binary_entropy(E_mu)
    good = Q_1 * (1 - binary_entropy(e1))
    return q * (good - cost)


# --- Pair 1, no-decoy defense: prior-art GLLP bound (the PNS crash) ---------
# These reproduce LMC's "GLLP without decoy" curve. Provenance / convention:
# Eq. 12 is printed in LMC with NEITHER the sifting prefactor q NOR the
# error-correction inefficiency f (both implicitly 1). We DEVIATE from the
# printed form on purpose (student's choice): we apply the SAME frozen q and
# f as secret_key_rate (Eq. 11), i.e. q*Q_mu{ -f*H2(E_mu) + Omega[...] }, so
# the crash curve and the decoy curve share one convention. That makes the
# vertical gap between them PURE PHYSICS (Omega and the blown-up single-
# photon error E_mu/Omega), not a q/f artifact -- which is the whole point
# of putting both on one plot. The distance crash (~142 km -> ~40 km) is
# driven by Omega, not q or f, so it is the same either way.

def omega(mu, eta, p_dark, n_max=N_MAX):
    """
    Untagged fraction Omega: the pessimistic fraction of Bob's detections
    treated as originating from single-photon signals when NO decoy states
    are used.

    LMC Eq. 13:  1 - Omega = p_multi / Q_mu   =>   Omega = 1 - p_multi / Q_mu

    p_multi is the probability Alice emits a multi-photon (n >= 2) signal.
    For a Poisson source it is the complement of the vacuum and single-photon
    weights:
        p_multi = 1 - P(0) - P(1) = 1 - e^{-mu} - mu*e^{-mu}
                = 1 - e^{-mu}(1 + mu)

    WORST CASE (this is the whole point of the no-decoy bound): assume every
    multi-photon pulse Alice ever emitted reached Bob AND is fully known to
    Eve via photon-number splitting. Those detections are "tagged" (insecure).
    Only the leftover, Q_mu - p_multi, may be counted as secure single-photon
    detections -- so Omega is a pessimistic LOWER bound on the true single-
    photon fraction. Decoy states later replace it with a measured, far
    tighter value; that replacement is what recovers the distance.

    Note Omega needs only Q_mu and p_multi, both computable by the honest
    parties without any ability to distinguish Eve -- which is exactly why
    this is the best they can do without decoy states.
    """
    p_multi = 1 - exp(-mu) * (1 + mu)
    return 1 - p_multi / q_mu(mu, eta, p_dark, n_max)


def key_rate_no_decoy(mu, eta, p_dark, e_detector, f=F_EC, q=Q_SIFT, n_max=N_MAX):
    """
    Secure key rate per pulse for BB84 WITHOUT decoy states, uses the prior-art
    GLLP bound, i.e. the PNS-crash curve.

    LMC Eq. 12 (as printed):
        S >= Q_mu { -H2(E_mu) + Omega [ 1 - H2(E_mu / Omega) ] }

    Coded here in the q/f-consistent form (project choice (b)) so it is
    directly comparable on one plot to secret_key_rate (Eq. 11):
        S >= q * Q_mu { -f * H2(E_mu) + Omega [ 1 - H2(E_mu / Omega) ] }

    Both substitutions are pessimistic, forced because without decoy the
    honest parties can measure only the aggregates Q_mu and E_mu:
      - single-photon FRACTION Q_1/Q_mu  ->  Omega (Eq. 13), worst-case
        untagged fraction;
      - single-photon ERROR e_1  ->  E_mu / Omega, i.e. ALL observed error
        dumped onto the untagged single-photon slice. Since Omega < 1 this
        inflates the error; as L grows Omega shrinks and E_mu/Omega races
        upward, H2(.) -> 1, the gain term vanishes, and R crashes (~40 km vs
        the ~142 km ceiling).

    Numerical guard: E_mu/Omega is an artificially inflated error that can
    exceed 1/2. Our binary_entropy is symmetric about 1/2 (H2(0.75)=H2(0.25)),
    so feeding it a value >1/2 would let 1-H2 spuriously RECOVER to a positive
    gain -- physically wrong (an error >= 1/2 carries no extractable key). We
    therefore cap the argument at 1/2, where H2 peaks: for e1_bound >= 1/2 the
    gain term is exactly 0 and R is (correctly) non-positive. This only bites
    past the cutoff where R is already negative, so it does not move the ~40 km
    crash point; it just keeps the curve physical there.

    Returns the RAW bound (may be negative past the cutoff), same convention
    as secret_key_rate.
    """
    Q_mu = q_mu(mu, eta, p_dark, n_max)
    E_mu = e_mu(mu, eta, p_dark, e_detector, n_max)
    Om = omega(mu, eta, p_dark, n_max)

    e1_bound = min(E_mu / Om, 0.5)          # cap: error >= 1/2 -> no key
    good = Om * (1 - binary_entropy(e1_bound))
    cost = f * binary_entropy(E_mu)
    return q * Q_mu * (good - cost)


def optimize_no_decoy(eta, p_dark, e_detector, f=F_EC, q=Q_SIFT,
                      mu_min=1e-4, mu_max=0.9, n_grid=500):
    """
    Best no-decoy (prior-art GLLP) secure key rate at a given channel, found
    by optimizing over Alice's mean photon number mu.

    HOW (cited to MQZL): MQZL p.6, section "Choose optimal mu", prescribes
    picking mu "by maximizing the key generation rate". There is NO closed
    form for the optimum, so we implement that principle directly: scan mu
    and return the value that maximizes key_rate_no_decoy (LMC Eq. 12). The
    mu-scan is our own numerical maximization, NOT a transcribed equation.

    WHY mu is re-optimized per distance (cited to LMC): LMC p.3 states that
    without decoy, mu = O(eta). As eta shrinks with distance the optimal mu
    shrinks with it, so no single frozen mu serves all distances -- unlike
    the decoy curve, where mu = O(1) ~ 0.5 is ~distance-independent (LMC p.4).
    That is exactly why the no-decoy curve gets its own per-point mu while
    the decoy curve keeps the frozen MU.

    The grid is LOG-spaced because the optimum sits at small mu (~1e-2) where
    a linear grid would be too coarse. Returns (R_best, mu_best).
    """
    R_best = float("-inf")
    mu_best = mu_min
    log_lo, log_hi = log10(mu_min), log10(mu_max)
    for i in range(n_grid + 1):
        mu = 10 ** (log_lo + (log_hi - log_lo) * i / n_grid)
        R = key_rate_no_decoy(mu, eta, p_dark, e_detector, f=f, q=q)
        if R > R_best:
            R_best, mu_best = R, mu
    return R_best, mu_best