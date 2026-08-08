"""
Distance sweep + plot for BBM92 (entangled PDC, Koashi-Preskill rate).

Sweeps the single free variable -- distance L -- and plots the SECURE key rate
R vs L for BOTH source placements (source in the middle vs at Alice's side).
Everything else (eta_det, ed, Y0, mu, f, q) is frozen at the MFL 144 km PDC
values in model.py.

No decoy curve here: BBM92 needs none -- the basis-independent source is
intrinsically PNS-resistant (see model.py). The two curves are the same
protocol under the two source geometries.
"""

import os

import numpy as np
import matplotlib.pyplot as plt

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUTFILE = os.path.join(REPO_ROOT, "figures", "bbm92_key_rate.png")

from model import bbm92_key_rate, MU, ED

L_MIN_KM = 0.0
L_MAX_KM = 320.0
L_POINTS = 320


def sweep_bbm92(L_km, placement):
    """Secure key rate at each L for a given source placement (raw, may be <0)."""
    return np.array([bbm92_key_rate(L, placement) for L in L_km])


def cutoff_distance(L_km, R):
    """Distance where R crosses from positive to non-positive (interpolated)."""
    R = np.asarray(R)
    sc = np.where((R[:-1] > 0) & (R[1:] <= 0))[0]
    if len(sc) == 0:
        return None
    i = sc[0]
    return L_km[i] + R[i] / (R[i] - R[i + 1]) * (L_km[i + 1] - L_km[i])


def plot_bbm92(L_km, R_mid, R_ali, outfile=OUTFILE):
    """Plot both placements on a log-y axis; mask R <= 0 so each ends at cutoff."""
    c_mid = cutoff_distance(L_km, R_mid)
    c_ali = cutoff_distance(L_km, R_ali)
    R_mid = np.where(np.asarray(R_mid) > 0, R_mid, np.nan)
    R_ali = np.where(np.asarray(R_ali) > 0, R_ali, np.nan)

    fig, ax = plt.subplots(figsize=(8.5, 5.5))
    ax.semilogy(L_km, R_mid, color="#6a0dad", lw=2,
                label=f"source in the middle  cutoff $\\approx${c_mid:.0f} km")
    ax.semilogy(L_km, R_ali, color="#e67e22", lw=2,
                label=f"source at Alice's side  cutoff $\\approx${c_ali:.0f} km")

    ax.set_xlabel("Distance L (km)")
    ax.set_ylabel("Secure key rate R (per pulse)")
    ax.set_title("BBM92 (entangled PDC, Koashi-Preskill) - secure key rate vs distance\n"
                 f"(MFL 144 km params, $\\mu={MU}$, $e_d={ED}$, no decoy needed)")
    ax.grid(True, which="both", ls=":", alpha=0.5)
    ax.legend(loc="lower left", fontsize=9)
    fig.tight_layout()
    fig.savefig(outfile, dpi=150)
    print(f"saved {outfile}")
    return fig


if __name__ == "__main__":
    L_km = np.linspace(L_MIN_KM, L_MAX_KM, L_POINTS)
    R_mid = sweep_bbm92(L_km, "middle")
    R_ali = sweep_bbm92(L_km, "alice")
    print(f"middle cutoff ~ {cutoff_distance(L_km, R_mid):.1f} km")
    print(f"alice  cutoff ~ {cutoff_distance(L_km, R_ali):.1f} km")
    plot_bbm92(L_km, R_mid, R_ali)
