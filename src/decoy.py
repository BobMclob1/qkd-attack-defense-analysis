"""
Practical decoy-state defense for BB84 Pair 1: the Vacuum + Weak decoy method.

The real "decoy recovery" curve. Alice interleaves three intensities -- signal
mu, one weak decoy nu, and vacuum (0) -- and from the measured per-intensity
gains/QBERs (Q_mu, E_mu, Q_nu, E_nu, Y_0) Bob ESTIMATES the single-photon
lower/upper bounds Y_1^L and e_1^U WITHOUT assuming the honest-channel values.
Those estimates then feed the shared gllp_key_rate (LMC Eq. 11), so the decoy
curve sits just below the ceiling and far above the no-decoy crash.

Source (to be coded directly from the PDF): Ma, Qi, Zhao & Lo (MQZL),
"Practical Decoy State for QKD", quant-ph/0503005v5 -- the Vacuum+Weak
estimators for Y_1^L / e_1^U and the choice of nu.

STATUS: not yet implemented. Next step -- pull the exact MQZL estimator
equations (and their equation numbers) from refs/MQZL_0503005.pdf, then build
one function at a time (yield/error estimators -> decoy key rate).
"""
