"""
No-decoy defense for BB84 Pair 1: the prior-art GLLP bound (the PNS crash).

Reproduces LMC's "GLLP without decoy" curve (Eqs. 12, 13), with Alice's mean
photon number mu re-optimized per distance (the "how" cited to MQZL p.6).
This is the curve that collapses from the ~142 km ceiling to ~40 km once
photon-number splitting is accounted for without decoy states.

Provenance / convention: Eq. 12 is printed in LMC with NEITHER the sifting
prefactor q NOR the error-correction inefficiency f (both implicitly 1). We
DEVIATE from the printed form on purpose (student's choice): we apply the SAME
frozen q and f as the ceiling (gllp_key_rate), i.e.
    q*Q_mu{ -f*H2(E_mu) + Omega[...] },
so the crash curve and the ceiling share one convention. That makes the
vertical gap between them PURE PHYSICS (Omega and the blown-up single-photon
error E_mu/Omega), not a q/f artifact -- the whole point of putting both on
one plot. The distance crash (~142 km -> ~40 km) is driven by Omega, not q or
f, so it is the same either way.
"""

from math import exp, log10

from keyrate import q_mu, e_mu, binary_entropy, N_MAX, F_EC, Q_SIFT


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
    directly comparable on one plot to the ceiling (Eq. 11):
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
    as the ceiling.
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
    the ceiling/decoy curve, where mu = O(1) ~ 0.5 is ~distance-independent
    (LMC p.4). That is exactly why the no-decoy curve gets its own per-point
    mu while the ceiling keeps the frozen MU.

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
