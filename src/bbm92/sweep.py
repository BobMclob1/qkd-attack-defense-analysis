"""
Distance sweep + plot + table for BBM92 (entangled PDC, Koashi-Preskill rate).

Sweeps distance L. The FIGURE shows only the native MFL parameters (both source
placements, middle vs Alice). The TABLE additionally reports the GYS parameter
set, so the hardware effect is available numerically without cluttering the
plot. mu, f, q are fixed at the model.py defaults (native BBM92 mu).

No decoy curve: BBM92 needs none -- the basis-independent source is intrinsically
PNS-resistant (see model.py). Middle geometry reaches ~2x farther than Alice
because dark counts compete per arm and middle halves each arm's loss.
"""

import os
import sys

import numpy as np
import matplotlib.pyplot as plt

_SRC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO_ROOT = os.path.dirname(_SRC)
sys.path.insert(0, _SRC)
OUTFILE = os.path.join(REPO_ROOT, "figures", "bbm92_key_rate.png")
TABLE_OUTFILE = os.path.join(REPO_ROOT, "figures", "bbm92_table.png")

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


# Figure: NATIVE MFL only, both placements (colour distinguishes placement).
GRAPH = [("middle", "#6a0dad", "-"), ("alice", "#e67e22", "-")]


def plot_bbm92(L_km, outfile=OUTFILE):
    """Plot the two native-MFL curves on a log-y axis; mask R <= 0 at the cutoff."""
    fig, ax = plt.subplots(figsize=(8.5, 5.5))
    for placement, color, ls in GRAPH:
        R = sweep_bbm92(L_km, placement, MFL)
        c = cutoff_distance(L_km, R)
        Rmask = np.where(R > 0, R, np.nan)
        ax.semilogy(L_km, Rmask, color=color, ls=ls, lw=2,
                    label=f"source {placement}  cutoff $\\approx${c:.0f} km")
    ax.set_xlabel("Distance L (km)")
    ax.set_ylabel("Secure key rate R (per pulse)")
    ax.set_title("BBM92 (entangled PDC, Koashi-Preskill) - secure key rate vs distance\n"
                 "native MFL params, no decoy needed (both source placements)")
    ax.grid(True, which="both", ls=":", alpha=0.5)
    ax.legend(loc="lower left", fontsize=9)
    fig.tight_layout()
    fig.savefig(outfile, dpi=150)
    print(f"saved {outfile}")
    return fig


def plot_table(L_km, outfile=TABLE_OUTFILE):
    """Table: GYS and MFL, R(L=0) and the cutoff for each placement."""
    col_labels = ["Params", "R(L=0)", "cutoff\n(middle)", "cutoff\n(alice)"]
    cells = []
    for params in (MFL, GYS):
        R0 = bbm92_key_rate(0.0, "middle", eta_det=params.eta_det,
                            ed=params.e_det, y0=params.dark)   # same at L=0 either placement
        c_mid = cutoff_distance(L_km, sweep_bbm92(L_km, "middle", params))
        c_ali = cutoff_distance(L_km, sweep_bbm92(L_km, "alice", params))
        cells.append([params.name, f"{R0:.2e}", f"{c_mid:.1f} km", f"{c_ali:.1f} km"])

    fig, ax = plt.subplots(figsize=(7.5, 1.7))
    ax.axis("off")
    tbl = ax.table(cellText=cells, colLabels=col_labels, loc="center", cellLoc="center")
    tbl.auto_set_font_size(False)
    tbl.set_fontsize(10)
    tbl.scale(1.0, 2.2)
    for (r, c), cell in tbl.get_celld().items():
        if r == 0:
            cell.set_facecolor("#6a0dad"); cell.set_text_props(color="white", weight="bold")
        elif c == 0:
            cell.set_text_props(weight="bold")
    ax.set_title("BBM92 secure key rate & reach (native MFL vs GYS hardware)",
                 fontsize=10, pad=10)
    fig.tight_layout()
    fig.savefig(outfile, dpi=150, bbox_inches="tight")
    print(f"saved {outfile}")
    return fig


if __name__ == "__main__":
    L_km = np.linspace(L_MIN_KM, L_MAX_KM, L_POINTS)
    plot_bbm92(L_km)
    plot_table(L_km)
    print("\nBBM92 cutoffs (km):")
    for params in (MFL, GYS):
        for placement in ("middle", "alice"):
            c = cutoff_distance(L_km, sweep_bbm92(L_km, placement, params))
            print(f"  {params.name} @{placement}: {c:.1f}")
