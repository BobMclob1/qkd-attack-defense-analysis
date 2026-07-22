"""
GLLP secret-key-rate engine for BB84 / BBM92.

Equations coded directly from Lo, Ma & Chen (LMC),
"Decoy State Quantum Key Distribution",
arXiv:quant-ph/0411004v4, PRL 94, 230504 (2005).
Equation numbers in comments refer to that paper.

Milestone 1: clean-protocol engine (no eavesdropper, no decoy estimation yet).
"""

from math import log2


def binary_entropy(x):
    """
    Binary Shannon entropy H2(x) = -x log2(x) - (1-x) log2(1-x).

    Definition used inside LMC Eq. 11.
    H2(0) = H2(1) = 0 by the limit x*log2(x) -> 0 as x -> 0:
    a certain outcome carries no uncertainty. if equal to 0 or 1, more certain 
    """
    if x <= 0 or x >= 1:
        return 0.0
    return -x * log2(x) - (1 - x) * log2(1 - x)