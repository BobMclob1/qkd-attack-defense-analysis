"""
Practical decoy-state defense for BB84 Pair 1: the Vacuum + Weak decoy method.

The real "decoy recovery" curve. Alice interleaves three intensities -- signal
mu, one weak decoy nu, and vacuum (0) -- and from the measured per-intensity
gains/QBERs (Q_mu, E_mu, Q_nu, E_nu, Y0) Bob ESTIMATES the single-photon
lower/upper bounds Y1^L and e1^U WITHOUT assuming the honest-channel values.
Those estimates then feed the shared gllp_key_rate (LMC Eq. 11 = MQZL Eq. 26),
so the decoy curve sits just below the ceiling and far above the no-decoy crash.

Equations coded directly from Ma, Qi, Zhao & Lo (MQZL), "Practical Decoy State
for QKD", quant-ph/0503005v5, Section 3.4 "Vacuum+Weak decoy state" -- the
PRINTED simplified (nu2=0) forms Eqs. 33, 34, 35, 37 (student choice 1(ii):
transcribe the special-case equations, not hand-specialize the general ones).

In this SIMULATION the "measurements" are computed from the device model in
keyrate (q_mu/e_mu at intensities mu and nu, Y0 = p_dark), then fed to the
estimators below -- exactly what a real experiment would measure.
"""

from math import exp

from keyrate import q_mu, e_mu, gllp_key_rate, MU, P_DARK, F_EC, Q_SIFT

# Weak decoy intensity nu. MUST satisfy nu < mu (MQZL Eq. 15).
# PROVISIONAL: fixed at 0.1 for the first pass. MQZL actually OPTIMIZE nu
# (pp.14/19); revisiting this to add per-distance nu optimization (like
# optimize_no_decoy) is a planned refinement -- see memory decoy-nu-fixed-revisit.
NU = 0.1


def y1_lower(Q_mu, Q_nu, Y0, mu, nu):
    """
    Lower bound on the single-photon yield Y1, Vacuum+Weak decoy method.

    MQZL Eq. 34:
        Y1 >= Y1^{L,nu,0}
            = mu/(mu*nu - nu^2)
              * [ Q_nu*e^nu - (nu^2/mu^2)*Q_mu*e^mu - ((mu^2-nu^2)/mu^2)*Y0 ]

    This is the crux of decoy: from only the MEASURED gains Q_mu (signal),
    Q_nu (weak decoy) and Y0 (vacuum), it bounds how much of Bob's detection
    rate must have come from single photons -- WITHOUT trusting the device
    model. Contrast the no-decoy Omega (a crude worst case): here the second
    intensity nu gives an extra equation, so the bound is far tighter and the
    reach climbs back toward the ceiling.

    Terms:
      - Q_nu*e^nu, Q_mu*e^mu : the measured gains with the Poisson e^{intensity}
        factor stripped off (so each becomes sum_i Y_i * intensity^i / i!).
      - the mu/nu prefactor and the (nu^2/mu^2), (mu^2-nu^2)/mu^2 weights come
        from solving the two decoy gain equations for Y1 (MQZL Eqs. 16-21
        specialized to nu2=0, where the vacuum makes the Y0 bound tight).

    Assumes nu < mu (Eq. 15) so the denominator mu*nu - nu^2 = nu(mu-nu) > 0.
    """
    num = (Q_nu * exp(nu)
           - (nu ** 2 / mu ** 2) * Q_mu * exp(mu)
           - ((mu ** 2 - nu ** 2) / mu ** 2) * Y0)
    return (mu / (mu * nu - nu ** 2)) * num


def q1_lower(Y1_L, mu):
    """
    Lower bound on the single-photon GAIN Q1, Vacuum+Weak decoy method.

    MQZL Eq. 35:  Q1^{L,nu,0} = Y1^{L,nu,0} * mu * e^{-mu}

    This is just the Y1 lower bound (Eq. 34) times the Poisson weight that a
    signal pulse holds exactly one photon, mu*e^{-mu} -- identical in form to
    LMC Eq. 10 (Q1 = Y1 * mu * e^{-mu}), now applied to the ESTIMATED Y1^L
    instead of the true Y1. Converts "how often a single photon clicks" into
    "how often a single-photon detection happens per pulse", the quantity the
    key-rate formula's good term actually needs.
    """
    return Y1_L * mu * exp(-mu)


def e1_upper(E_nu, Q_nu, Y0, Y1_L, nu, e0=0.5):
    """
    Upper bound on the single-photon QBER e1, Vacuum+Weak decoy method.

    MQZL Eq. 37:
        e1 <= e1^{U,nu,0} = (E_nu*Q_nu*e^nu - e0*Y0) / (Y1^{L,nu,0} * nu)

    From the weak decoy's error rate E_nu*Q_nu, subtract the errors that the
    vacuum/background contributes (e0*Y0, with e0 = 1/2 the dark-count QBER,
    MQZL Eq. 33), leaving the error attributable to single photons; divide by
    the single-photon weight nu*Y1^L to turn it into a per-single-photon error
    fraction. Using Y1^L (a LOWER bound) in the DENOMINATOR makes e1 an UPPER
    bound -- the conservative direction, as required for security.
    """
    return (E_nu * Q_nu * exp(nu) - e0 * Y0) / (Y1_L * nu)


def decoy_key_rate(mu, eta, p_dark, e_detector, nu=NU, f=F_EC, q=Q_SIFT):
    """
    Secure key rate per pulse for BB84 with Vacuum+Weak decoy states.

    MQZL Eq. 26 (= LMC Eq. 11 with ESTIMATED single-photon bounds):
        R >= q{ -Q_mu f(E_mu) H2(E_mu) + Q1^L [1 - H2(e1^U)] }

    Pipeline:
      1. "Measure" the three intensities from the device model:
         Q_mu, E_mu (signal), Q_nu, E_nu (weak decoy), Y0 = Q_vacuum (Eq. 33).
      2. Estimate the single-photon bounds Y1^L (Eq. 34), Q1^L (Eq. 35),
         e1^U (Eq. 37) -- WITHOUT using the true single-photon values.
      3. Feed Q1^L / e1^U into the shared gllp_key_rate combiner.

    The only difference from ceiling_key_rate is step 2: the ceiling uses the
    true Q1/e1, this uses decoy-estimated bounds. Same security formula.
    """
    Q_mu = q_mu(mu, eta, p_dark)
    E_mu = e_mu(mu, eta, p_dark, e_detector)
    Q_nu = q_mu(nu, eta, p_dark)
    E_nu = e_mu(nu, eta, p_dark, e_detector)
    Y0 = q_mu(0.0, eta, p_dark)        # vacuum gain Q_vacuum = Y0 (MQZL Eq. 33)

    Y1_L = y1_lower(Q_mu, Q_nu, Y0, mu, nu)
    Q1_L = q1_lower(Y1_L, mu)
    e1_U = e1_upper(E_nu, Q_nu, Y0, Y1_L, nu)

    return gllp_key_rate(Q_mu, E_mu, Q1_L, e1_U, f=f, q=q)
