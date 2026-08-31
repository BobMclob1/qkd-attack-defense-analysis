"""
Shared infrastructure for the QKD simulator, used by BOTH protocols
(src/bb84/ and src/bbm92/).

Per the project scope (approach A), BB84 and BBM92 do NOT share a key-rate
combiner -- BB84 uses GLLP (LMC Eq. 11, single-photon isolation) and BBM92
uses Koashi-Preskill (MFL Eq. 11, overall Q/E only). What they DO share is
this QBER-based infrastructure: the binary entropy function, the fiber loss
model, and the frozen error-correction / sifting constants that appear in
both rate formulas.
"""

from math import log2, log10


def binary_entropy(x):
    """
    Binary Shannon entropy H2(x) = -x log2(x) - (1-x) log2(1-x).

    Appears in both LMC Eq. 11 (GLLP) and MFL Eq. 11 (Koashi-Preskill).
    H2(0) = H2(1) = 0 by the limit x*log2(x) -> 0 as x -> 0: a certain
    outcome carries no uncertainty.
    """
    if x <= 0 or x >= 1:
        return 0.0
    return -x * log2(x) - (1 - x) * log2(1 - x)


# --- Frozen constants shared by both protocols ------------------------------
ALPHA_DB_PER_KM = 0.21    # GYS fiber loss coefficient (dB/km), MQZL Table 1.
                          # Was 0.20 (rounded); corrected to the sourced GYS
                          # value. Reach ~ 1/alpha; this shift lands the BB84
                          # Fig.1 validation (insecurity 208 km, decoy 142 km).
F_EC = 1.22               # error-correction inefficiency f(E) >= 1 (both rates)
Q_SIFT = 0.5              # basis-sifting factor q (both rates).
                          # 1/2 = standard BB84 (half the pulses land in a
                          # mismatched basis and are discarded); efficient BB84
                          # would give q ~ 1. Frozen; flip to 1.0 as a twist.


def transmittance(L, alpha=ALPHA_DB_PER_KM):
    """
    Channel transmittance: probability a photon survives L km of fiber.
        eta_channel = 10 ** (-alpha * L / 10)
    The shared fiber loss law. Detector efficiency is applied separately by
    each protocol's model (single-sided in BB84, two-sided in BBM92).
    """
    return 10 ** (-alpha * L / 10)


# --- Milestone 6b: one parameter set fed to BOTH protocols ------------------
from dataclasses import dataclass


@dataclass(frozen=True)
class DeviceParams:
    """
    A named set of PER-DETECTOR device constants for one grid column.

    Milestone 6b removes the draft-1 confound (BB84 ran on GYS, BBM92 on MFL, so
    a cross-protocol overlay mixed two different detectors). The fix, per mentor
    instruction "keep all the same parameters": hold the SET-EQUAL device
    properties in ONE object and feed it to both engines, so a grid COLUMN
    (fixed params, two protocols) is a controlled comparison.

    Fields are exactly the 6b "set equal" list:
      eta_det  detection efficiency per detector (channel loss applied
               separately by each engine: eta_overall in BB84, eta_arms in BBM92)
      e_det    intrinsic misalignment / detector error. Same physical quantity
               under two names: BB84 e_detector (LMC Eq. 8) = BBM92 ed (MFL Eq. 10).
      dark     background / dark-count probability PER SIDE (per party's receiver),
               NOT per individual photodiode -- this is how BOTH sources model it:
               MQZL calls Y0 "the background rate ... includes the detector dark
               count and other background contributions" for Bob's (single)
               threshold detector; MFL define "Y0A and Y0B [as] the background
               count rates at Alice's and Bob's SIDES". So BB84 feeds 'dark'
               directly as Y0 (LMC Eq. 6, n=0) and BBM92 as Y0A = Y0B (MFL Eq. 7).
               The structural difference that makes the SAME per-side 'dark' give
               different noise floors is detection TOPOLOGY, handled inside each
               engine: BB84 single-side floor ~ dark; BBM92 coincidence vacuum
               floor Y0 = Y0A*Y0B ~ dark^2 (MFL Eq. 7 at n=0). (This per-side
               reading supersedes the draft "background per detector, 2 vs 4"
               framing -- neither source gives per-photodiode rates.)

    NOT in here, deliberately:
      alpha, f_EC, q  -- already shared module constants, identical every column.
      mu              -- a different physical quantity per protocol (Poisson
                         photon-mean vs thermal pair-mean); becomes an optimized
                         output in 6c, so it is passed separately, not frozen here.

    Provenance (resolved against the sources, not assumed): both papers define
    background as a PER-SIDE rate -- MQZL for Bob's single threshold detector
    (Y0 = 1.7e-6), MFL for each party's box (Y0A = Y0B = 6.02e-6, vacuum
    coincidence Y0 = Y0A*Y0B). Feeding 'dark' as Bob's Y0 in BB84 and as
    Y0A = Y0B in BBM92 matches that per-side definition exactly, so the two
    engines already consume it consistently for a controlled grid column.
    """
    name: str
    eta_det: float
    e_det: float
    dark: float


# The two experimental parameter sets that form the grid ROWS. Values are the
# existing frozen constants, now named as a set rather than per-protocol globals.
GYS = DeviceParams("GYS", eta_det=0.045, e_det=0.033, dark=1.7e-6)
# LMC/GYS: Lo-Ma-Chen quant-ph/0411004 Fig. 1 + Gobby-Yuan-Shields (refs/0412171).
MFL = DeviceParams("MFL", eta_det=0.145, e_det=0.015, dark=6.02e-6)
# MFL 144 km entangled-PDC experiment, Ma-Fung-Lo quant-ph/0703122 Table I.


# --- Milestone 6c: mu as an optimized OUTPUT --------------------------------
def optimize_mu(rate_of_mu, mu_min, mu_max, n_grid=500):
    """
    Maximize a secure key rate over the source intensity mu, returning
    (R_best, mu_best) -- the best rate and the mu that achieves it.

    Milestone 6c: mu stops being a frozen assumption and becomes an optimized
    OUTPUT. This is the actual answer to the mentor's "keep the same parameters"
    -- once mu is optimized per protocol per distance there is nothing to hold
    equal, because mu is no longer an assumption. (A fixed-mu path stays for the
    LMC/MQZL validation figures; this optimizer is for the cross-protocol grid.)

    HOW (sourced): MQZL p.6, section "Choose optimal mu", prescribes picking mu
    "by maximizing the key generation rate". There is NO closed form, so we scan
    a grid and take the argmax -- the same principle already used inside
    optimize_no_decoy, factored out here so BB84 (ceiling, decoy) and BBM92 all
    share ONE optimizer instead of four copies of the scan.

    rate_of_mu : callable mu -> R. The caller binds everything else (eta/arms,
                 dark, e_det, placement, ...) into this one-argument closure, so
                 this helper is protocol-agnostic -- it only knows "vary mu, read
                 R". Protocol-specific mu MEANING (BB84 photon mean vs BBM92 pair
                 mean) lives entirely in the closure, never here.
    mu_min, mu_max : scan bounds. Left to the caller because the optimum sits at
                 different scales per curve (no-decoy ~1e-2, decoy ~O(1)).
    n_grid : number of LOG-spaced samples. Log spacing resolves both a small-mu
             and an O(1) optimum without a punishingly fine linear grid.

    Returns the RAW best R (may be <= 0 past a cutoff, same convention as the
    rate functions); the sweep/grid layer locates the zero-crossing.
    """
    R_best = float("-inf")
    mu_best = mu_min
    lo, hi = log10(mu_min), log10(mu_max)
    for i in range(n_grid + 1):
        mu = 10 ** (lo + (hi - lo) * i / n_grid)
        R = rate_of_mu(mu)
        if R > R_best:
            R_best, mu_best = R, mu
    return R_best, mu_best
