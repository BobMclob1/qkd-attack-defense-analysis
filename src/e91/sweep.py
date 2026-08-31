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

from chsh import S_of_distance, S_TSIRELSON
from shared import GYS, MFL

OUTFILE = os.path.join(REPO_ROOT, "figures", "e91_chsh_S.png")

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


# COLOUR encodes the parameter set, LINESTYLE encodes the source placement:
# middle (symmetric, each arm L/2 -- the canonical entanglement geometry) vs
# alice (one-sided, Bob carries full L -- matches the BB84 grid geometry).
CURVES = [
    (GYS, "middle", "#6a0dad", "-"),
    (GYS, "alice",  "#6a0dad", "--"),
    (MFL, "middle", "#e67e22", "-"),
    (MFL, "alice",  "#e67e22", "--"),
]


if __name__ == "__main__":
    fig, ax = plt.subplots(figsize=(9.5, 6))

    for params, placement, color, ls in CURVES:
        S = np.array([S_of_distance(L, placement, params) for L in L_KM])
        c_bell = s2_crossing(placement, params)
        ax.plot(L_KM, S, color=color, ls=ls, lw=2,
                label=f"{params.name} {placement}   Bell $S{{=}}2\\approx${c_bell:.0f} km")
        print(f"{params.name} @{placement}: Bell S=2 cutoff {c_bell:.1f} km")

    ax.axhline(2.0, color="#c00000", ls="--", lw=1.3, label="classical bound $S=2$")
    ax.axhline(S_TSIRELSON, color="#888888", ls=":", lw=1,
               label="Tsirelson $2\\sqrt{2}$ (ideal singlet)")

    ax.set_xlabel("Distance L (km)")
    ax.set_ylabel("CHSH value S")
    ax.set_title("E91 as S(L): CHSH value vs distance (fixed $\\mu$)\n"
                 "colour = parameter set, linestyle = placement (middle solid / alice dashed)")
    ax.set_ylim(1.4, 2.95)
    ax.grid(True, ls=":", alpha=0.5)
    ax.legend(loc="lower left", fontsize=8.5)
    fig.tight_layout()
    fig.savefig(OUTFILE, dpi=150)
    print(f"saved {OUTFILE}")
