"""
Milestone 7: E91 as S(L) -- CHSH value versus distance, S = 2 Bell cutoff located
for both source placements and both parameter sets.

Delivered as an S(L) curve + the S = 2 crossing only -- NO key rate (decided
scope: a device-independent rate is identically zero at these detector
efficiencies, so E91 gives a stated bound, not a rate). mu is FIXED at the
native BBM92 value (no rate to optimize against).

Four curves: {GYS, MFL} x {middle, alice}. Placement matters a lot here -- the
symmetric MIDDLE geometry (each arm L/2) roughly DOUBLES the S = 2 reach versus
the one-sided ALICE geometry (Bob carries the full L), because dark counts
compete per arm and middle halves each arm's loss.

Caveats (stated in the write-up, not on the figure): S = 2 marks loss of
entanglement CERTIFIABILITY, not a key-rate cutoff -- the rate is already zero
well before it. Computed under the FAIR-SAMPLING assumption (coincidence
post-selection = the detection loophole) and the DEPOLARIZING approximation for
the S<->Q map, S = 2*sqrt(2)*(1-2Q) (Acin et al.).
"""

import os
import sys

import numpy as np
import matplotlib.pyplot as plt

_SRC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO_ROOT = os.path.dirname(_SRC)
sys.path.insert(0, os.path.join(_SRC, "bbm92"))
sys.path.insert(0, _SRC)

from chsh import S_of_distance, S_TSIRELSON, chsh_S, qber_bbm92
from shared import GYS, MFL

OUTFILE = os.path.join(REPO_ROOT, "figures", "e91_chsh_S.png")
TABLE_OUTFILE = os.path.join(REPO_ROOT, "figures", "e91_table.png")

L_MAX_KM = 360.0
L_POINTS = 361
L_KM = np.linspace(0.0, L_MAX_KM, L_POINTS)


def s2_crossing(placement, params, lo=0.0, hi=500.0):
    """Distance where S falls through 2 (the Bell cutoff), by bisection."""
    if S_of_distance(lo, placement, params) < 2:
        return None
    for _ in range(60):
        mid = (lo + hi) / 2
        if S_of_distance(mid, placement, params) > 2:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


# Figure: NATIVE MFL only, both placements (colour distinguishes placement).
GRAPH = [("middle", "#6a0dad", "-"), ("alice", "#e67e22", "-")]


def plot_S(outfile=OUTFILE):
    """Plot the two native-MFL S(L) curves, with the S=2 and Tsirelson lines."""
    fig, ax = plt.subplots(figsize=(9.0, 5.8))
    for placement, color, ls in GRAPH:
        S = np.array([S_of_distance(L, placement, MFL) for L in L_KM])
        c_bell = s2_crossing(placement, MFL)
        ax.plot(L_KM, S, color=color, ls=ls, lw=2,
                label=f"source {placement}   Bell $S{{=}}2\\approx${c_bell:.0f} km")
    ax.axhline(2.0, color="#c00000", ls="--", lw=1.3, label="classical bound $S=2$")
    ax.axhline(S_TSIRELSON, color="#888888", ls=":", lw=1,
               label="Tsirelson $2\\sqrt{2}$ (ideal singlet)")
    ax.set_xlabel("Distance L (km)")
    ax.set_ylabel("CHSH value S")
    ax.set_title("E91 as S(L): CHSH value vs distance (native MFL params, fixed $\\mu$)\n"
                 "both source placements; $S=2$ is a Bell cutoff, NOT a key-rate cutoff")
    ax.set_ylim(1.4, 2.95)
    ax.grid(True, ls=":", alpha=0.5)
    ax.legend(loc="lower left", fontsize=8.5)
    fig.tight_layout()
    fig.savefig(outfile, dpi=150)
    print(f"saved {outfile}")
    return fig


def plot_table(outfile=TABLE_OUTFILE):
    """Table: GYS and MFL, S(L=0) and the S=2 Bell cutoff for each placement."""
    col_labels = ["Params", "S(L=0)", "$S{=}2$\n(middle)", "$S{=}2$\n(alice)"]
    cells = []
    for params in (MFL, GYS):
        S0 = chsh_S(qber_bbm92(0.0, "middle", params))   # same at L=0 either placement
        c_mid = s2_crossing("middle", params)
        c_ali = s2_crossing("alice", params)
        cells.append([params.name, f"{S0:.3f}", f"{c_mid:.1f} km", f"{c_ali:.1f} km"])

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
    ax.set_title("E91 CHSH value & S=2 Bell cutoff (native MFL vs GYS hardware)\n"
                 "fair-sampling assumption; depolarizing S<->Q map [Acin et al.]",
                 fontsize=9.5, pad=10)
    fig.tight_layout()
    fig.savefig(outfile, dpi=150, bbox_inches="tight")
    print(f"saved {outfile}")
    return fig


if __name__ == "__main__":
    plot_S()
    plot_table()
    print("\nE91 S=2 Bell cutoffs (km):")
    for params in (MFL, GYS):
        for placement in ("middle", "alice"):
            print(f"  {params.name} @{placement}: {s2_crossing(placement, params):.1f}")
