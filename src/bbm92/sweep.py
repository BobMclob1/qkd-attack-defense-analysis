"""
Distance sweep + plot for BBM92 (entangled PDC, Koashi-Preskill rate).

Sweeps the single free variable -- distance L -- and plots the SECURE key rate
R vs L for BOTH source placements (middle vs Alice) AND both parameter sets
(GYS, MFL). mu, f, q are fixed at the model.py defaults (native BBM92 mu).

No decoy curve here: BBM92 needs none -- the basis-independent source is
intrinsically PNS-resistant (see model.py). Colour encodes the parameter set,
linestyle the source geometry, so the figure shows two independent effects at
once: hardware (GYS vs MFL) and loss geometry (middle reaches ~2x farther than
Alice because dark counts compete per arm and middle halves each arm's loss).
"""

import os
import sys

import numpy as np
import matplotlib.pyplot as plt

_SRC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO_ROOT = os.path.dirname(_SRC)
sys.path.insert(0, _SRC)
OUTFILE = os.path.join(REPO_ROOT, "figures", "bbm92_key_rate.png")

from model import bbm92_key_rate
from shared import GYS, MFL

L_MIN_KM = 0.0
L_MAX_KM = 340.0
L_POINTS = 341


def sweep_bbm92(L_km, placement, params):
    """Secure key rate at each L for a placement + parameter set (raw, may be <0)."""
    return np.array([bbm92_key_rate(L, placement, eta_det=params.eta_det,
                                    ed=params.e_det, y0=params.dark) for L in L_km])


def cutoff_distance(L_km, R):
    """Distance where R crosses from positive to non-positive (interpolated)."""
    R = np.asarray(R)
    sc = np.where((R[:-1] > 0) & (R[1:] <= 0))[0]
    if len(sc) == 0:
        return None
    i = sc[0]
    return L_km[i] + R[i] / (R[i] - R[i + 1]) * (L_km[i + 1] - L_km[i])


# COLOUR encodes the parameter set, LINESTYLE encodes the source placement.
CURVES = [
    (GYS, "middle", "#6a0dad", "-"),
    (GYS, "alice",  "#6a0dad", "--"),
    (MFL, "middle", "#e67e22", "-"),
    (MFL, "alice",  "#e67e22", "--"),
]


def plot_bbm92(L_km, outfile=OUTFILE):
    """Plot all four curves on a log-y axis; mask R <= 0 so each ends at its cutoff."""
    fig, ax = plt.subplots(figsize=(9.0, 5.8))
    for params, placement, color, ls in CURVES:
        R = sweep_bbm92(L_km, placement, params)
        c = cutoff_distance(L_km, R)
        Rmask = np.where(R > 0, R, np.nan)
        ax.semilogy(L_km, Rmask, color=color, ls=ls, lw=2,
                    label=f"{params.name} {placement}  cutoff $\\approx${c:.0f} km")
        print(f"{params.name} @{placement}: cutoff ~ {c:.1f} km")

    ax.set_xlabel("Distance L (km)")
    ax.set_ylabel("Secure key rate R (per pulse)")
    ax.set_title("BBM92 (entangled PDC, Koashi-Preskill) - secure key rate vs distance\n"
                 "colour = parameter set, linestyle = placement (middle solid / alice dashed)")
    ax.grid(True, which="both", ls=":", alpha=0.5)
    ax.legend(loc="lower left", fontsize=8.5)
    fig.tight_layout()
    fig.savefig(outfile, dpi=150)
    print(f"saved {outfile}")
    return fig


if __name__ == "__main__":
    L_km = np.linspace(L_MIN_KM, L_MAX_KM, L_POINTS)
    plot_bbm92(L_km)
