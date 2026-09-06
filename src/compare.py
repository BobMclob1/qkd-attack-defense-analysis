"""
Cross-protocol comparison plot: BB84 (GLLP) vs BBM92 (Koashi-Preskill).

The point of the figure is the PNS-RESISTANCE story:
  - BB84 WITHOUT decoy CRASHES (~40 km) -- the coherent source's multi-photon
    pulses leak to Eve via photon-number splitting.
  - BB84 needs DECOY states to recover (~140 km).
  - BBM92 needs NO decoy at all and still reaches far (~170-290 km): the
    entangled PDC source is basis-independent, so Koashi-Preskill security
    (overall Q/E only) is already immune to PNS.

Caveat (drawn on the plot): BB84 uses GYS device constants and BBM92 uses the
144 km PDC-experiment constants (MFL Table I) -- different detectors, so this
is a QUALITATIVE comparison of protocol behavior, not a controlled overlay.
"""

import os
import sys

import numpy as np
import matplotlib.pyplot as plt

SRC = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(SRC)
sys.path.insert(0, os.path.join(SRC, "bbm92"))
sys.path.insert(0, os.path.join(SRC, "bb84"))
sys.path.insert(0, SRC)  # shared

from keyrate import eta_overall, MU, P_DARK, E_DETECTOR, F_EC, Q_SIFT  # BB84
from ceiling import ceiling_key_rate
from no_decoy import optimize_no_decoy
from decoy import decoy_key_rate
from model import bbm92_key_rate  # BBM92

OUTFILE = os.path.join(REPO_ROOT, "figures", "compare_bb84_bbm92.png")
L_MAX_KM = 300.0
L_POINTS = 300


def _cutoff(L_km, R):
    R = np.asarray(R)
    sc = np.where((R[:-1] > 0) & (R[1:] <= 0))[0]
    if len(sc) == 0:
        return None
    i = sc[0]
    return L_km[i] + R[i] / (R[i] - R[i + 1]) * (L_km[i + 1] - L_km[i])


def _mask(R):
    R = np.asarray(R)
    return np.where(R > 0, R, np.nan)


if __name__ == "__main__":
    L = np.linspace(0.0, L_MAX_KM, L_POINTS)

    # BB84 curves (GYS params)
    bb84_ceiling = np.array([ceiling_key_rate(MU, eta_overall(x), P_DARK, E_DETECTOR) for x in L])
    bb84_decoy = np.array([decoy_key_rate(MU, eta_overall(x), P_DARK, E_DETECTOR) for x in L])
    bb84_nodecoy = np.array([optimize_no_decoy(eta_overall(x), P_DARK, E_DETECTOR)[0] for x in L])
    # BBM92 curves (144 km PDC params), no decoy needed
    bbm92_mid = np.array([bbm92_key_rate(x, "middle") for x in L])
    bbm92_ali = np.array([bbm92_key_rate(x, "alice") for x in L])

    curves = [
        ("BB84 infinite-decoy limit", bb84_ceiling, "#1f4e79", "--"),
        ("BB84 + decoy (Vacuum+Weak)", bb84_decoy, "#2e8b57", "-"),
        ("BB84 NO decoy (PNS crash)", bb84_nodecoy, "#c0392b", "-"),
        ("BBM92 (no decoy required) - source middle", bbm92_mid, "#6a0dad", "-"),
        ("BBM92 (no decoy required) - source at Alice", bbm92_ali, "#e67e22", "-"),
    ]

    fig, ax = plt.subplots(figsize=(9.5, 6))
    for label, R, color, ls in curves:
        c = _cutoff(L, R)
        ctxt = f"  cutoff $\\approx${c:.0f} km" if c else ""
        ax.semilogy(L, _mask(R), color=color, ls=ls, lw=2, label=label + ctxt)

    ax.set_xlabel("Distance L (km)")
    ax.set_ylabel("Secure key rate R (bits per pulse)")
    ax.set_title("PNS resistance: BB84 (needs decoy) vs BBM92 (intrinsically immune)")
    ax.grid(True, which="both", ls=":", alpha=0.5)
    ax.legend(loc="lower left", fontsize=8.5)
    fig.tight_layout()
    fig.savefig(OUTFILE, dpi=150)
    print(f"saved {OUTFILE}")

    for label, R, _, _ in curves:
        c = _cutoff(L, R)
        print(f"  {label:44s} cutoff ~ {c:.1f} km" if c else f"  {label}: no cutoff")
