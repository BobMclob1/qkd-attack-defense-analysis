"""
Distance sweep + plots for the BB84 GLLP engine.

Sweeps the single free variable -- distance L (channel loss) -- and plots the
SECURE key rate R vs L. Everything else (dark counts, detector efficiency,
misalignment, f, q, and -- for the decoy curve -- mu) is frozen at the GYS
values in keyrate.

Milestone 1: the infinite-decoy ceiling curve alone (ceiling.ceiling_key_rate,
Eq. 11). Milestone 2, Pair 1: adds the no-decoy PNS-crash curve
(no_decoy.optimize_no_decoy, Eq. 12/13 with mu re-optimized per distance) and
the insecurity bound (true e_1 = 1/4), so the figure reproduces the three
curves of LMC Fig. 1.
"""

import os

import numpy as np
import matplotlib.pyplot as plt

# Repo root = parent of this file's directory (src/), so figures/ resolves
# correctly no matter which directory the script is run from.
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_OUTFILE = os.path.join(REPO_ROOT, "figures", "bb84_clean_keyrate.png")
PAIR1_OUTFILE = os.path.join(REPO_ROOT, "figures", "bb84_pair1_pns_crash.png")

from keyrate import e_1, eta_overall, MU, P_DARK, E_DETECTOR, F_EC, Q_SIFT
from ceiling import ceiling_key_rate
from no_decoy import optimize_no_decoy
from decoy import decoy_key_rate, NU

# Sweep range for the single swept variable, distance L (km). Extends past the
# ~208 km insecurity bound so that bound is visible on the plot.
L_MIN_KM = 0.0
L_MAX_KM = 220.0
L_POINTS = 440


def sweep_ceiling(L_km):
    """
    Infinite-decoy ceiling secure key rate at each L (LMC Eq. 11, frozen
    mu = MU; true Y1/e1 via ceiling_key_rate).

    Returns a numpy array of R per pulse. Values may be negative past the
    cutoff -- masking for the plot is done separately so this stays raw.
    """
    return np.array([
        ceiling_key_rate(MU, eta_overall(L), P_DARK, E_DETECTOR, f=F_EC, q=Q_SIFT)
        for L in L_km
    ])


def sweep_no_decoy(L_km):
    """
    No-decoy (PNS-crash) secure key rate at each L, with mu RE-OPTIMIZED at
    every distance (LMC Eq. 12, MQZL p.6 "maximize R over mu" -- see
    optimize_no_decoy). Returns a numpy array of the best R per pulse.
    """
    return np.array([
        optimize_no_decoy(eta_overall(L), P_DARK, E_DETECTOR, f=F_EC, q=Q_SIFT)[0]
        for L in L_km
    ])


def sweep_decoy(L_km):
    """
    Vacuum+Weak decoy secure key rate at each L (MQZL Eqs. 34/35/37 -> Eq. 26),
    with frozen signal mu = MU and weak decoy nu = NU. Returns a numpy array of
    R per pulse. This is the real decoy-RECOVERY curve.
    """
    return np.array([
        decoy_key_rate(MU, eta_overall(L), P_DARK, E_DETECTOR, nu=NU, f=F_EC, q=Q_SIFT)
        for L in L_km
    ])


def cutoff_distance(L_km, R):
    """
    Maximum secure distance: the L where R crosses from positive to
    non-positive, linearly interpolated between the straddling samples.
    Returns None if R never crosses.
    """
    R = np.asarray(R)
    sign_change = np.where((R[:-1] > 0) & (R[1:] <= 0))[0]
    if len(sign_change) == 0:
        return None
    i = sign_change[0]
    frac = R[i] / (R[i] - R[i + 1])
    return L_km[i] + frac * (L_km[i + 1] - L_km[i])


def insecurity_distance():
    """
    Distance where the true single-photon error e_1 reaches 1/4 -- LMC's
    absolute insecurity bound (intercept-resend gives 25% QBER, so beyond
    this no protocol, decoy or not, is secure). Found by bisection on e_1.
    """
    lo, hi = 0.0, 400.0
    for _ in range(60):
        mid = (lo + hi) / 2
        if e_1(eta_overall(mid), P_DARK, E_DETECTOR) < 0.25:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def plot_key_rate(L_km, R, cutoff=None, outfile=DEFAULT_OUTFILE):
    """
    Milestone-1 single-curve plot: SECURE key rate vs distance (log-y).
    Points where R <= 0 are masked so the curve ends at the cutoff.
    """
    R = np.asarray(R)
    R_secure = np.where(R > 0, R, np.nan)

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


def plot_pair1(L_km, R_ceiling, R_decoy, R_no_decoy, insecurity, outfile=PAIR1_OUTFILE):
    """
    Milestone-2 Pair-1 plot: the three-curve PNS story -- infinite-decoy
    ceiling, practical Vacuum+Weak decoy RECOVERY, and no-decoy PNS crash --
    plus the insecurity bound, reproducing LMC Fig. 1. Insecure points
    (R <= 0) are masked so each curve ends at its own cutoff.
    """
    # Cutoffs from the RAW (signed) arrays passed in, BEFORE masking -- do not
    # re-run the sweeps (the no-decoy sweep is ~220k rate evals).
    c_ceiling = cutoff_distance(L_km, R_ceiling)
    c_decoy = cutoff_distance(L_km, R_decoy)
    c_nod = cutoff_distance(L_km, R_no_decoy)
    R_ceiling = np.where(np.asarray(R_ceiling) > 0, R_ceiling, np.nan)
    R_decoy = np.where(np.asarray(R_decoy) > 0, R_decoy, np.nan)
    R_no_decoy = np.where(np.asarray(R_no_decoy) > 0, R_no_decoy, np.nan)

    fig, ax = plt.subplots(figsize=(9, 5.5))
    ax.semilogy(L_km, R_ceiling, color="#1f4e79", lw=2, ls="--",
                label=f"GLLP ceiling (infinite decoy, true $Y_1,e_1$)  cutoff $\\approx${c_ceiling:.0f} km")
    ax.semilogy(L_km, R_decoy, color="#2e8b57", lw=2,
                label=f"Vacuum+Weak decoy ($\\nu={NU}$, MQZL)  cutoff $\\approx${c_decoy:.0f} km")
    ax.semilogy(L_km, R_no_decoy, color="#c0392b", lw=2,
                label=f"GLLP no decoy ($\\mu$ re-opt., PNS crash)  cutoff $\\approx${c_nod:.0f} km")
    ax.axvline(insecurity, color="#555555", ls="--", lw=1.2,
               label=f"insecurity bound ($e_1=1/4$) $\\approx${insecurity:.0f} km")

    ax.set_xlabel("Distance L (km)")
    ax.set_ylabel("Secure key rate R (per pulse)")
    ax.set_title("BB84 Pair 1: PNS attack — decoy recovery vs no-decoy crash\n"
                 f"(GYS params, $q={Q_SIFT}$, $f={F_EC}$)")
    ax.grid(True, which="both", ls=":", alpha=0.5)
    ax.legend(loc="lower left", fontsize=9)
    fig.tight_layout()
    fig.savefig(outfile, dpi=150)
    print(f"saved {outfile}")
    return fig


if __name__ == "__main__":
    L_km = np.linspace(L_MIN_KM, L_MAX_KM, L_POINTS)

    R_ceiling = sweep_ceiling(L_km)
    R_decoy = sweep_decoy(L_km)
    R_no_decoy = sweep_no_decoy(L_km)
    insecurity = insecurity_distance()

    print(f"ceiling cutoff ~ {cutoff_distance(L_km, R_ceiling):.1f} km")
    print(f"decoy (Vacuum+Weak) cutoff ~ {cutoff_distance(L_km, R_decoy):.1f} km")
    print(f"no-decoy crash cutoff ~ {cutoff_distance(L_km, R_no_decoy):.1f} km")
    print(f"insecurity bound (e_1=1/4) ~ {insecurity:.1f} km")

    plot_pair1(L_km, R_ceiling, R_decoy, R_no_decoy, insecurity)
