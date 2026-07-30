"""
Infinite-decoy CEILING curve for BB84.

This is LMC Eq. 11 fed the TRUE single-photon values Y_1/e_1 from the honest
device model -- i.e. the rate you would get if decoy estimation were perfect
(infinitely many decoy intensities). It is the optimistic upper edge that the
practical decoy curve (decoy.py) approaches from below and that the no-decoy
crash (no_decoy.py) falls far short of.

Not a measurable protocol on its own: it assumes Alice and Bob already KNOW
the exact single-photon statistics, which no real experiment does (see the
e_1 docstring in keyrate.py). It is the reference ceiling only.
"""

from keyrate import q_mu, e_mu, q_1, e_1, gllp_key_rate, F_EC, Q_SIFT


def ceiling_key_rate(mu, eta, p_dark, e_detector, f=F_EC, q=Q_SIFT):
    """
    Secure key rate per pulse at the infinite-decoy ceiling (LMC Eq. 11).

    Assembles the four ingredients from the true device model and hands them
    to the shared gllp_key_rate combiner:
        Q_mu, E_mu  -- overall gain/QBER (Eqs. 2, 3)
        Q_1         -- single-photon gain (Eq. 10)
        e_1         -- TRUE single-photon QBER (Eq. 8 at n=1)

    Because e_1 here is the honest-channel value (not an Eve-safe upper
    bound), this is the ceiling, not a security guarantee against PNS. The
    decoy curve replaces Q_1/e_1 with estimated bounds while calling the very
    same gllp_key_rate.
    """
    Q_mu = q_mu(mu, eta, p_dark)
    E_mu = e_mu(mu, eta, p_dark, e_detector)
    Q_1 = q_1(mu, eta, p_dark)
    e1 = e_1(eta, p_dark, e_detector)
    return gllp_key_rate(Q_mu, E_mu, Q_1, e1, f=f, q=q)
