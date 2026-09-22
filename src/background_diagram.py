"""
Background schematic: the three protocol setups side by side.

Shows, for BB84 / BBM92 / E91: where the source sits, what each party
chooses from, where the bit is committed, and which quantity the security
check monitors. BBM92 additionally shows both source placements.

Full-width (two-column) figure for the CJSJ submission.

    cd src && python3 background_diagram.py
"""

import os
import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, Rectangle

# --- CJSJ typography (matches src/bb84/sweep.py and src/e91/sweep.py) ---
mpl.rcParams["font.family"] = "serif"
mpl.rcParams["font.serif"] = ["Times New Roman", "Nimbus Roman", "DejaVu Serif"]
mpl.rcParams["font.size"] = 8
mpl.rcParams["mathtext.fontset"] = "stix"
mpl.rcParams["pdf.fonttype"] = 42          # Type 42 / TrueType, not Type 3

SRC = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(SRC)
OUTFILE = os.path.join(REPO_ROOT, "figures", "background_setups.pdf")

INK = "#1a1a1a"
BOX = "#eaf0f6"
SRC_WCP = "#c0392b"    # BB84: attenuated laser (weak coherent pulse)
SRC_SPDC = "#6a0dad"   # BBM92 / E91: SPDC entangled-pair source
EDGE = "#555555"

FS_TITLE = 10
FS_LABEL = 8           # CJSJ: 8 pt figure labels
FS_SMALL = 7

BW, BH = 0.90, 0.44    # party box width / height
XA, XB = 0.72, 3.28    # Alice / Bob column centres
XS = 2.00              # source centre


def box(ax, x, y, label):
    ax.add_patch(Rectangle((x - BW / 2, y - BH / 2), BW, BH, facecolor=BOX,
                           edgecolor=EDGE, lw=1.0, zorder=3))
    ax.text(x, y, label, ha="center", va="center",
            fontsize=FS_LABEL, color=INK, zorder=4)


def dot(ax, x, y, s=52, color=SRC_SPDC):
    ax.scatter([x], [y], s=s, color=color, zorder=4, linewidths=0)


def arrow(ax, x0, x1, y):
    ax.add_patch(FancyArrowPatch((x0, y), (x1, y), arrowstyle="-|>",
                                 mutation_scale=8, lw=1.0, color=EDGE,
                                 zorder=2))


def note(ax, y, text, **kw):
    ax.text(2.0, y, text, ha="center", va="center",
            fontsize=kw.pop("fs", FS_SMALL), color=INK, zorder=4, **kw)


def panel(ax, title):
    ax.set_xlim(0, 4.0)
    ax.set_ylim(0, 2.85)
    ax.axis("off")
    ax.set_title(title, fontsize=FS_TITLE, pad=4)


fig, axes = plt.subplots(1, 3, figsize=(7.0, 2.75))

# ---------------------------------------------------------------- BB84
ax = axes[0]
panel(ax, "BB84")
box(ax, XA, 2.30, "Alice")
box(ax, XB, 2.30, "Bob")
dot(ax, XA + 0.62, 2.30, color=SRC_WCP)
arrow(ax, XA + 0.75, XB - 0.52, 2.30)
note(ax, 2.56, "attenuated laser:  one photon per pulse")
ax.text(XA, 1.88, r"prepares $+$ / $\times$", ha="center",
        fontsize=FS_SMALL, color=INK)
ax.text(XB, 1.88, r"measures $+$ / $\times$", ha="center",
        fontsize=FS_SMALL, color=INK)
note(ax, 1.35, "bit is fixed at the source", style="italic")
note(ax, 0.72, "check:  QBER", fs=FS_LABEL, weight="bold")
note(ax, 0.28, "a split photon already\ncarries a determined bit")

# --------------------------------------------------------------- BBM92
ax = axes[1]
panel(ax, "BBM92")
box(ax, XA, 2.30, "Alice")
box(ax, XB, 2.30, "Bob")
dot(ax, XS, 2.30)
arrow(ax, XS - 0.10, XA + 0.52, 2.30)
arrow(ax, XS + 0.10, XB - 0.52, 2.30)
note(ax, 2.56, r"source in the middle:  each arm $L/2$")
ax.text(XA, 1.90, r"$+$ / $\times$", ha="center",
        fontsize=FS_SMALL, color=INK)
ax.text(XB, 1.90, r"$+$ / $\times$", ha="center",
        fontsize=FS_SMALL, color=INK)
# second placement, drawn as a bare geometry line
ax.text(XA - 0.30, 1.45, "A", ha="center", va="center",
        fontsize=FS_SMALL, color=INK)
dot(ax, XA - 0.10, 1.45, s=34)
arrow(ax, XA - 0.02, XB + 0.10, 1.45)
ax.text(XB + 0.30, 1.45, "B", ha="center", va="center",
        fontsize=FS_SMALL, color=INK)
note(ax, 1.14, r"source at Alice:  Bob's arm carries all of $L$")
note(ax, 0.72, "check:  QBER", fs=FS_LABEL, weight="bold")
note(ax, 0.28, "no key exists until\nboth parties measure")

# ----------------------------------------------------------------- E91
ax = axes[2]
panel(ax, "E91")
box(ax, XA, 2.30, "Alice")
box(ax, XB, 2.30, "Bob")
dot(ax, XS, 2.30)
arrow(ax, XS - 0.10, XA + 0.52, 2.30)
arrow(ax, XS + 0.10, XB - 0.52, 2.30)
note(ax, 2.60, "entangled pair source")
ax.text(XA, 1.88, r"$a_1, a_2, a_3$", ha="center",
        fontsize=FS_SMALL, color=INK)
ax.text(XB, 1.88, r"$b_1, b_2, b_3$", ha="center",
        fontsize=FS_SMALL, color=INK)
note(ax, 1.45, r"matched angles $\rightarrow$ key", style="italic")
note(ax, 1.14, r"mismatched angles $\rightarrow$ measure $S$", style="italic")
note(ax, 0.72, "check:  CHSH value $S$", fs=FS_LABEL, weight="bold")
note(ax, 0.28, "certifies entanglement,\nnot the error rate")

fig.tight_layout(w_pad=1.2)
fig.savefig(OUTFILE, bbox_inches="tight")
print(f"saved {OUTFILE}")