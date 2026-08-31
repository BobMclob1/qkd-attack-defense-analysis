"""
E91 (Ekert 1991) as S(L): the CHSH value versus distance.

Milestone 7. Reuses the BBM92 device layer UNCHANGED to obtain the QBER
E_lambda(L), then maps it to the CHSH value S under the depolarizing-channel
approximation (Option 1, the student's chosen modeling fork).

Sources (both in refs/, verified -- not coded from memory):
  - Ekert, PRL 67, 661 (1991) [refs/91_Ekert.pdf]: the CHSH test quantity S
    (his Eq. 3) and the ideal singlet value S = 2*sqrt(2) (his Eq. 4).
  - Acin, Brunner, Gisin, Massar, Pironio, Scarani, PRL 98, 230501 (2007),
    quant-ph/0702152v2 [refs/0702152v2.pdf]: CHSH polynomial (their Eq. 1) and
    the depolarizing relation S = 2*sqrt(2)*(1 - 2*Q), stated in their "Key rate"
    paragraph / Fig. 1 for |Phi+> sent through a depolarizing channel.

MODELING CAVEATS (decided -- must be stated wherever S(L) appears):
  - DEPOLARIZING APPROXIMATION (Option 1). Acin et al. stress "there is no a
    priori relation between S and Q"; S = 2sqrt2(1-2Q) holds ONLY for a
    depolarizing channel. Our E_lambda folds in DARK COUNTS, which are not
    depolarizing, so feeding E_lambda through this map is an APPROXIMATION, not
    an identity. (Option 2 -- visibility from the coincidence statistics -- was
    the alternative; not taken.)
  - S = 2 is NOT a key-rate cutoff. It is where the CHSH violation (i.e. the
    certifiability of entanglement) ends; the secret-key rate may already be zero
    well before it. Any figure/table must label S = 2 as a DIFFERENT quantity
    from the BB84/BBM92 key-rate cutoffs.
  - FAIR SAMPLING. The BBM92/E91 device model post-selects on coincidences --
    exactly the detection loophole. S(L) here is computed under the fair-sampling
    assumption and must be labelled as such.
"""

import os
import sys
# Reach the BBM92 device layer (sibling dir) and shared/ (one up), so the E91
# module can reuse them UNCHANGED, per Milestone 7.
_SRC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_SRC, "bbm92"))
sys.path.insert(0, _SRC)

from math import sqrt

from model import eta_arms, q_lambda, e_lambda, MU as MU_BBM92   # BBM92 layer

# Ideal singlet / Tsirelson value: the CHSH value with no channel degradation.
# Ekert Eq. 4 (S = 2*sqrt(2)); equivalently Acin's map at Q = 0.
S_TSIRELSON = 2 * sqrt(2)


def chsh_S(Q):
    """
    CHSH value S from the QBER Q under the depolarizing-channel model.

    Acin et al. (quant-ph/0702152v2), depolarizing relation:
        S = 2*sqrt(2) * (1 - 2*Q)

    Q is the quantum bit error rate (Acin: Q = prob(a0 != b1)); here it is the
    BBM92 overall QBER E_lambda. At Q = 0 the state is the ideal singlet and
    S = 2*sqrt(2) ~ 2.828 (Tsirelson / Ekert Eq. 4). S falls linearly in Q and
    reaches the classical bound S = 2 at Q = (1 - 1/sqrt(2))/2 ~ 14.6%, beyond
    which the CHSH inequality is no longer violated (entanglement no longer
    certifiable). Note S can go below 2 -- and even negative -- for large Q; that
    is fine here, the S = 2 crossing is what matters and the sweep locates it.

    Returns the RAW S (not clamped), same convention as the rate functions.
    """
    return 2 * sqrt(2) * (1 - 2 * Q)


def qber_bbm92(L, placement, params, mu=MU_BBM92):
    """
    BBM92 overall QBER E_lambda(L) -- the BBM92 device layer reused UNCHANGED.

    Just re-assembles MFL Eqs. 7/9/10 the same way bbm92_key_rate does, but
    returns E_lambda instead of the key rate:
        eta_arms (placement) -> q_lambda (Eq. 9) -> e_lambda (Eq. 10).
    lam = mu/2; Y0A = Y0B = params.dark (per-side background). This is the E(L)
    that feeds the CHSH map. mu is FIXED at the native BBM92 value here: E91 has
    NO key rate to maximize (decided scope), so there is nothing to optimize mu
    against -- it is a source-brightness setting, not an optimized output.
    """
    lam = mu / 2
    etaA, etaB = eta_arms(L, params.eta_det, placement)
    Q = q_lambda(lam, etaA, etaB, params.dark, params.dark)
    return e_lambda(lam, etaA, etaB, params.dark, params.dark, params.e_det, Q_lam=Q)


def S_of_distance(L, placement, params, mu=MU_BBM92):
    """
    CHSH value S at distance L: BBM92 QBER E_lambda(L) pushed through the
    depolarizing map chsh_S. The one endpoint that ties Milestone 7 together.
    """
    return chsh_S(qber_bbm92(L, placement, params, mu))
