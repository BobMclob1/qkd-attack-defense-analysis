"""
Milestone 6d: the {BB84, BBM92} x {GYS, MFL} parameter grid.

The controlled cross-protocol comparison the draft-1 overlay could not make.
For each of the four configurations, mu is optimized PER DISTANCE (6c) and the
two headline numbers are reported: max secure distance and zero-distance secure
key rate.

Cell choices (per CLAUDE.md 6d):
  - BB84 cell = the Vacuum+Weak DECOY curve, i.e. BB84 in its DEFENDED form.
    That is the fair match to BBM92, which is PNS-secure with no decoy at all.
    (Ceiling is only a reference; no-decoy is the crash, not a protocol to ship.)
  - BBM92 cell = source-at-Alice -- the 6d PRIMARY placement, whose one-sided
    loss geometry matches BB84's. Symmetric (middle) placement is a separate
    secondary result about loss geometry, not part of the controlled grid.
  - mu is optimized for BOTH protocols (6c: "extend to every curve"), so nothing
    is held equal -- mu stops being an assumption. nu (weak decoy) stays fixed
    at its current value; only mu is the optimized output here.

A grid COLUMN (fixed params, two protocols) is the controlled comparison: same
eta_det / e_det / per-side dark fed to both, differing only by protocol
structure (single-side vs coincidence, GLLP vs Koashi-Preskill).
"""

import os
import sys

import numpy as np
import matplotlib.pyplot as plt

SRC = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(SRC)
sys.path.insert(0, os.path.join(SRC, "bb84"))
sys.path.insert(0, os.path.join(SRC, "bbm92"))
sys.path.insert(0, SRC)  # shared

from shared import optimize_mu, GYS, MFL
from keyrate import eta_overall            # BB84
from decoy import decoy_key_rate, NU
from model import bbm92_key_rate           # BBM92

# Distance sweep for locating cutoffs. 320 km covers every cell's reach.
L_MAX_KM = 320.0
L_POINTS = 321
L_KM = np.linspace(0.0, L_MAX_KM, L_POINTS)

# mu scan bounds per protocol. Different scales, different physical quantity:
#   BB84 decoy: optimal mu ~ O(1) and ~distance-independent (LMC p.4). Lower
#     bound kept ABOVE the fixed weak decoy nu=0.1 so the estimator's mu>nu
#     requirement (MQZL Eq. 15) always holds; the true optimum ~0.5 sits well
#     inside, so this guard never binds.
#   BBM92: mu = 2*lam, a mean PAIR number; MFL treat it as freely adjustable.
BB84_MU_MIN, BB84_MU_MAX = 0.12, 0.9
BBM92_MU_MIN, BBM92_MU_MAX = 1e-3, 1.0
MU_NGRID = 300


def bb84_best(L, params):
    """Best BB84 decoy secure rate at L over mu -> (R_best, mu_best)."""
    eta = eta_overall(L, params.eta_det)
    return optimize_mu(
        lambda mu: decoy_key_rate(mu, eta, params.dark, params.e_det, nu=NU),
        BB84_MU_MIN, BB84_MU_MAX, MU_NGRID)


def bbm92_best(L, params):
    """Best BBM92 (source@Alice) secure rate at L over mu -> (R_best, mu_best)."""
    return optimize_mu(
        lambda mu: bbm92_key_rate(L, "alice", mu=mu, eta_det=params.eta_det,
                                  ed=params.e_det, y0=params.dark),
        BBM92_MU_MIN, BBM92_MU_MAX, MU_NGRID)


def cutoff_distance(L_km, R):
    """Distance where R crosses from positive to non-positive (interpolated)."""
    R = np.asarray(R)
    sc = np.where((R[:-1] > 0) & (R[1:] <= 0))[0]
    if len(sc) == 0:
        return None
    i = sc[0]
    return L_km[i] + R[i] / (R[i] - R[i + 1]) * (L_km[i + 1] - L_km[i])


def run_cell(best_fn, params):
    """Sweep a cell with mu optimized per distance -> (R_array, mu_array)."""
    R = np.empty_like(L_KM)
    mu = np.empty_like(L_KM)
    for j, L in enumerate(L_KM):
        R[j], mu[j] = best_fn(L, params)
    return R, mu


OUTFILE = os.path.join(REPO_ROOT, "figures", "grid_bb84_bbm92.png")

# Style: COLOR encodes protocol, LINESTYLE encodes parameter set. So a reader
# compares protocols by colour and reads a controlled COLUMN (same device spec)
# by matching linestyle. Keys are (protocol_name, params_name).
STYLE = {
    ("BB84 decoy",   "GYS"): ("#1f4e79", "-",  "BB84 decoy (GYS)"),
    ("BB84 decoy",   "MFL"): ("#1f4e79", "--", "BB84 decoy (MFL)"),
    ("BBM92 @alice", "GYS"): ("#6a0dad", "-",  "BBM92 no-decoy (GYS)"),
    ("BBM92 @alice", "MFL"): ("#6a0dad", "--", "BBM92 no-decoy (MFL)"),
}


def plot_grid(results, outfile=OUTFILE):
    """
    Controlled grid figure: secure key rate vs distance for all four cells,
    mu optimized per distance. R <= 0 is masked so each curve ends at its cutoff.
    results: dict keyed (protocol_name, params_name) -> (R_array, mu_array, cutoff).
    """
    fig, ax = plt.subplots(figsize=(9.5, 6))
    for key, (color, ls, label) in STYLE.items():
        R, _, c = results[key]
        R_secure = np.where(np.asarray(R) > 0, R, np.nan)
        ctxt = f"  cutoff $\\approx${c:.0f} km" if c is not None else ""
        ax.semilogy(L_KM, R_secure, color=color, ls=ls, lw=2, label=label + ctxt)

    ax.set_xlabel("Distance L (km)")
    ax.set_ylabel("Secure key rate R (per pulse)")
    ax.set_title("Controlled grid: BB84 (decoy) vs BBM92 (no decoy), $\\mu$ optimized\n"
                 "colour = protocol, linestyle = parameter set (GYS solid / MFL dashed)")
    ax.grid(True, which="both", ls=":", alpha=0.5)
    ax.legend(loc="lower left", fontsize=8.5)
    ax.text(0.99, 0.97,
            "Controlled: identical eta_det / e_det / per-side dark fed to both\n"
            "protocols in each column; $\\mu$ optimized per distance for every curve.",
            transform=ax.transAxes, ha="right", va="top", fontsize=7.5,
            color="#555555", style="italic")
    fig.tight_layout()
    fig.savefig(outfile, dpi=150)
    print(f"saved {outfile}")
    return fig


if __name__ == "__main__":
    cells = [
        ("BB84 decoy", GYS, bb84_best),
        ("BB84 decoy", MFL, bb84_best),
        ("BBM92 @alice", GYS, bbm92_best),
        ("BBM92 @alice", MFL, bbm92_best),
    ]

    print("Milestone 6d grid -- mu optimized per distance for every cell\n")
    print(f"{'protocol':13s} {'params':6s} {'R(L=0)':>12s} {'mu*(L=0)':>9s} "
          f"{'max secure dist':>16s}")
    results = {}
    for name, params, best_fn in cells:
        R, mu = run_cell(best_fn, params)
        c = cutoff_distance(L_KM, R)
        results[(name, params.name)] = (R, mu, c)
        cstr = f"{c:.1f} km" if c is not None else "no cutoff"
        print(f"{name:13s} {params.name:6s} {R[0]:12.4e} {mu[0]:9.4f} {cstr:>16s}")

    plot_grid(results)
