"""
Distance sweep + plot for the clean BB84 GLLP engine (Milestone 1).

Sweeps the single free variable -- distance L (channel loss) -- and plots
the SECURE key rate R vs L from secret_key_rate() in keyrate.py. Everything
else (mu, dark counts, detector efficiency, misalignment, f, q) is frozen at
the GYS values defined in keyrate.

This is the CLEAN-protocol curve: no eavesdropper, true single-photon
Y_1/e_1 fed straight into LMC Eq. 11. It is the optimistic ceiling, and its
cutoff (~149 km) should sit near LMC Fig. 1's decoy curve (~140 km).
"""

import os

import numpy as np
import matplotlib.pyplot as plt

# Repo root = parent of this file's directory (src/), so figures/ resolves
# correctly no matter which directory the script is run from.
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_OUTFILE = os.path.join(REPO_ROOT, "figures", "bb84_clean_keyrate.png")

from keyrate import (
    secret_key_rate, eta_overall,
    MU, P_DARK, E_DETECTOR, F_EC, Q_SIFT,
)

# Sweep range for the single swept variable, distance L (km).
L_MIN_KM = 0.0
L_MAX_KM = 200.0
L_POINTS = 400


def sweep_key_rate(L_km):
    """
    Secure key rate R at each distance in L_km (an array of km values).

    Returns a numpy array of R per pulse (LMC Eq. 11). Values may be
    negative past the cutoff -- masking for the plot is done separately so
    this stays the raw engine output.
    """
    return np.array([
        secret_key_rate(MU, eta_overall(L), P_DARK, E_DETECTOR, f=F_EC, q=Q_SIFT)
        for L in L_km
    ])


def cutoff_distance(L_km, R):
    """
    Maximum secure distance: the L where R crosses from positive to
    non-positive. Linearly interpolated between the two straddling sample
    points. Returns None if R never crosses (all positive or all negative).
    """
    R = np.asarray(R)
    sign_change = np.where((R[:-1] > 0) & (R[1:] <= 0))[0]
    if len(sign_change) == 0:
        return None
    i = sign_change[0]
    # linear interpolation of the zero crossing between L[i] and L[i+1]
    frac = R[i] / (R[i] - R[i + 1])
    return L_km[i] + frac * (L_km[i + 1] - L_km[i])


def plot_key_rate(L_km, R, cutoff=None, outfile=DEFAULT_OUTFILE):
    """
    Plot the SECURE key rate vs distance on a log-y axis and save to outfile.

    Points where R <= 0 are masked (no secure key -> no line), so the curve
    ends naturally at the cutoff distance rather than being floored to zero.
    """
    R = np.asarray(R)
    R_secure = np.where(R > 0, R, np.nan)   # mask insecure region

    fig, ax = plt.subplots(figsize=(8, 5))
    ax.semilogy(L_km, R_secure, color="#1f4e79", lw=2,
                label="BB84 clean GLLP (true $Y_1, e_1$)")

    if cutoff is not None:
        ax.axvline(cutoff, color="#c00000", ls="--", lw=1,
                   label=f"cutoff $\\approx$ {cutoff:.0f} km")

    ax.set_xlabel("Distance L (km)")
    ax.set_ylabel("Secure key rate R (per pulse)")
    ax.set_title("BB84 clean GLLP engine — secure key rate vs distance\n"
                 f"(GYS params, $\\mu={MU}$, $q={Q_SIFT}$)")
    ax.grid(True, which="both", ls=":", alpha=0.5)
    ax.legend()
    fig.tight_layout()
    fig.savefig(outfile, dpi=150)
    print(f"saved {outfile}")
    return fig


if __name__ == "__main__":
    L_km = np.linspace(L_MIN_KM, L_MAX_KM, L_POINTS)
    R = sweep_key_rate(L_km)
    cutoff = cutoff_distance(L_km, R)
    print(f"max secure distance ~ {cutoff:.1f} km" if cutoff else "no cutoff found")
    plot_key_rate(L_km, R, cutoff)
