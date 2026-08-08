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

from shared import binary_entropy, transmittance, ALPHA_DB_PER_KM, F_EC, Q_SIFT


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
