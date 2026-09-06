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
import grid  # Milestone-6d grid: BBM92 key-rate reach at OPTIMIZED mu, for comparison

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


def bbm92_key_reach(placement, params):
    """
    BBM92 mu-OPTIMIZED key-rate reach (km) for the same placement/params, pulled
    from the Milestone-6d grid so it matches grid_table exactly (NOT the fixed-mu
    native sweep). This is the quantity the E91 S=2 Bell cutoff is compared to.
    """
    best = lambda L, p: grid.bbm92_best(L, p, placement)
    R, _ = grid.run_cell(best, params)
    return grid.cutoff_distance(grid.L_KM, R)


def plot_table(outfile=TABLE_OUTFILE):
    """
    Comparison table, one row per (params x placement): the E91 S=2 Bell cutoff
    against the BBM92 key-rate reach at the MATCHING placement. The two are
    DIFFERENT quantities and sit at DIFFERENT mu policies (see footnote):
      - S=2 Bell cutoff: fixed native mu=2*lam=0.053 (E91 has no key rate, so no
        rate to optimize mu against; and the crossing lies past the key cutoff,
        where a rate-optimal mu would be meaningless).
      - BBM92 key reach: grid, mu optimized per distance.
    The GAP is the finding -- certifying entanglement (S=2 <-> QBER 14.6%) is a
    WEAKER condition than distilling key (QBER ~10%), so the Bell violation
    outlives the key.
    """
    col_labels = ["Params", "Placement", "S(L=0)",
                  "$S{=}2$ Bell\ncutoff (km)", "BBM92 key-rate\nreach (km)", "gap\n(km)"]
    cells = []
    for params in (MFL, GYS):
        S0 = chsh_S(qber_bbm92(0.0, "middle", params))   # same at L=0 either placement
        for placement in ("middle", "alice"):
            bell = s2_crossing(placement, params)         # fixed native mu = 0.053
            key = bbm92_key_reach(placement, params)      # grid, mu optimized per L
            cells.append([params.name, placement, f"{S0:.3f}",
                          f"{bell:.1f}", f"{key:.1f}", f"+{bell - key:.1f}"])

    fig, ax = plt.subplots(figsize=(9.5, 2.7))
    ax.axis("off")
    tbl = ax.table(cellText=cells, colLabels=col_labels, loc="center", cellLoc="center")
    tbl.auto_set_font_size(False)
    tbl.set_fontsize(10)
    tbl.scale(1.0, 2.2)
    tbl.auto_set_column_width(col=list(range(len(col_labels))))
    # Tint the two compared quantities differently so they don't read as one:
    # Bell cutoff (E91) light purple, key reach (BBM92) light blue.
    for (r, c), cell in tbl.get_celld().items():
        if r == 0:
            cell.set_facecolor("#6a0dad"); cell.set_text_props(color="white", weight="bold")
        elif c == 0:
            cell.set_text_props(weight="bold")
        elif c == 3:
            cell.set_facecolor("#efe6f7")        # S=2 Bell cutoff (E91 quantity)
        elif c == 4:
            cell.set_facecolor("#eaf0f6")        # BBM92 key-rate reach (different quantity)
    ax.set_title("E91 $S{=}2$ Bell cutoff vs BBM92 key-rate reach (matched placement)",
                 fontsize=9.5, pad=10)
    fig.text(0.5, 0.02,
             "$S{=}2$ Bell cutoff computed at the fixed native brightness "
             "$\\mu{=}2\\lambda{=}0.053$; BBM92 key-rate reach from the grid at $\\mu$ "
             "optimized per distance.\nE91 has no key rate, so its $\\mu$ is not optimized. "
             "Gap: entanglement certification holds to QBER 14.6% ($S{=}2$); key "
             "distillation fails near QBER 10%.\n"
             "Fair-sampling assumption; depolarizing $S{\\leftrightarrow}Q$ map [Acin et al.].",
             ha="center", va="bottom", fontsize=7.5, style="italic")
    fig.subplots_adjust(bottom=0.28)
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
