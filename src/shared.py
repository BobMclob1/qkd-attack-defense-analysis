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

from math import log2


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
