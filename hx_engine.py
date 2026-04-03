import numpy as np
from scipy.optimize import fsolve
 
# ── FLUID PROPERTIES (simplified for common fluids) ──
FLUIDS = {
    "Water": {"cp": 4182, "rho": 998, "mu": 0.001003, "k": 0.598, "Pr": 7.01},
    "Engine Oil": {"cp": 2131, "rho": 876, "mu": 0.0326, "k": 0.138, "Pr": 504},
    "Ethylene Glycol": {"cp": 2415, "rho": 1117, "mu": 0.0157, "k": 0.252, "Pr": 151},
    "Air (1 atm)": {"cp": 1007, "rho": 1.184, "mu": 0.0000185, "k": 0.0262, "Pr": 0.711},
    "Steam (1 atm)": {"cp": 2010, "rho": 0.59, "mu": 0.0000125, "k": 0.0248, "Pr": 1.01},
}
 
def dittus_boelter(Re, Pr, heating=True):
    """Dittus-Boelter correlation for turbulent flow in tubes."""
    n = 0.4 if heating else 0.3
    if Re < 2300:
        return 3.66  # Laminar, constant wall temp
    return 0.023 * Re**0.8 * Pr**n
 
def calc_Re(m_dot, D, mu, A_flow):
    """Reynolds number from mass flow rate."""
    v = m_dot / (FLUIDS["Water"]["rho"] * A_flow)
    return FLUIDS["Water"]["rho"] * v * D / mu
 
def lmtd_method(T_hi, T_ho, T_ci, T_co, flow="counter"):
    """Log Mean Temperature Difference."""
    if flow == "counter":
        dT1 = T_hi - T_co
        dT2 = T_ho - T_ci
    else:  # parallel
        dT1 = T_hi - T_ci
        dT2 = T_ho - T_co
    
    if abs(dT1 - dT2) < 0.01:
        return (dT1 + dT2) / 2
    if dT1 <= 0 or dT2 <= 0:
        return 0.01  # Avoid log of negative
    return (dT1 - dT2) / np.log(dT1 / dT2)
 
def effectiveness_ntu(NTU, Cr, flow="counter"):
    """Calculate effectiveness from NTU and capacity ratio."""
    if Cr == 0:  # One fluid is condensing/evaporating
        return 1 - np.exp(-NTU)
    if flow == "counter":
        if abs(Cr - 1.0) < 0.001:
            return NTU / (1 + NTU)
        return (1 - np.exp(-NTU * (1 - Cr))) / (1 - Cr * np.exp(-NTU * (1 - Cr)))
    else:  # parallel
        return (1 - np.exp(-NTU * (1 + Cr))) / (1 + Cr)
 
def design_shell_tube(hot_fluid, cold_fluid, T_hi, T_ci,
                       m_dot_h, m_dot_c, Q_target,
                       D_tube=0.019, D_shell=0.3,
                       N_tubes=50, L=2.0, flow="counter"):
    """
    Design a shell-and-tube heat exchanger.
    Returns dict with all design parameters and results.
    """
    hp = FLUIDS[hot_fluid]
    cp_ = FLUIDS[cold_fluid]
    
    # Heat capacity rates
    C_h = m_dot_h * hp["cp"]  # W/K
    C_c = m_dot_c * cp_["cp"]
    C_min = min(C_h, C_c)
    C_max = max(C_h, C_c)
    Cr = C_min / C_max if C_max > 0 else 0
    
    # Outlet temperatures from energy balance
    T_ho = T_hi - Q_target / C_h
    T_co = T_ci + Q_target / C_c
    
    # Check thermodynamic feasibility
    Q_max = C_min * (T_hi - T_ci)
    if Q_target > Q_max:
        return {"error": f"Q_target ({Q_target/1000:.1f} kW) exceeds Q_max ({Q_max/1000:.1f} kW)"}
    
    effectiveness = Q_target / Q_max if Q_max > 0 else 0
    
    # LMTD
    lmtd = lmtd_method(T_hi, T_ho, T_ci, T_co, flow)
    
    # Tube-side heat transfer (cold fluid inside tubes)
    A_tube_flow = np.pi * (D_tube/2)**2
    v_tube = m_dot_c / (cp_["rho"] * N_tubes * A_tube_flow)
    Re_tube = cp_["rho"] * v_tube * D_tube / cp_["mu"]
    Nu_tube = dittus_boelter(Re_tube, cp_["Pr"], heating=True)
    h_tube = Nu_tube * cp_["k"] / D_tube
    
    # Shell-side (hot fluid)
    D_shell_equiv = D_shell - N_tubes * D_tube  # simplified
    A_shell = np.pi * (D_shell/2)**2 - N_tubes * np.pi * (D_tube/2)**2
    v_shell = m_dot_h / (hp["rho"] * A_shell) if A_shell > 0 else 1
    Re_shell = hp["rho"] * v_shell * D_shell_equiv / hp["mu"] if D_shell_equiv > 0 else 1000
    Nu_shell = dittus_boelter(abs(Re_shell), hp["Pr"], heating=False)
    h_shell = Nu_shell * hp["k"] / D_shell_equiv if D_shell_equiv > 0 else 500
    
    # Overall heat transfer coefficient
    k_wall = 50  # W/(m*K) for carbon steel
    t_wall = 0.002  # 2mm wall thickness
    U = 1 / (1/h_tube + t_wall/k_wall + 1/h_shell)
    
    # Required area and length
    A_required = Q_target / (U * lmtd) if lmtd > 0 else 999
    A_per_tube = np.pi * D_tube * L
    A_available = N_tubes * A_per_tube
    L_required = A_required / (N_tubes * np.pi * D_tube) if N_tubes > 0 else 999
    
    # NTU
    NTU = U * A_available / C_min if C_min > 0 else 0
    eff_calc = effectiveness_ntu(NTU, Cr, flow)
    Q_actual = eff_calc * C_min * (T_hi - T_ci)
    
    # Pressure drops (simplified Darcy-Weisbach)
    f_tube = 0.316 / Re_tube**0.25 if Re_tube > 0 else 0.05
    dp_tube = f_tube * (L / D_tube) * 0.5 * cp_["rho"] * v_tube**2
    f_shell = 0.316 / abs(Re_shell)**0.25 if Re_shell > 0 else 0.05
    dp_shell = f_shell * (L / D_shell_equiv) * 0.5 * hp["rho"] * v_shell**2 if D_shell_equiv > 0 else 0
    
    return {
        "hot_fluid": hot_fluid, "cold_fluid": cold_fluid,
        "T_hi": T_hi, "T_ho": round(T_ho, 1),
        "T_ci": T_ci, "T_co": round(T_co, 1),
        "Q_target_kW": round(Q_target/1000, 2),
        "Q_max_kW": round(Q_max/1000, 2),
        "Q_actual_kW": round(Q_actual/1000, 2),
        "effectiveness": round(effectiveness, 3),
        "eff_ntu": round(eff_calc, 3),
        "LMTD": round(lmtd, 2),
        "U_overall": round(U, 1),
        "h_tube": round(h_tube, 1), "h_shell": round(h_shell, 1),
        "Re_tube": round(Re_tube, 0), "Re_shell": round(abs(Re_shell), 0),
        "A_required_m2": round(A_required, 3),
        "A_available_m2": round(A_available, 3),
        "L_required_m": round(L_required, 2),
        "N_tubes": N_tubes, "D_tube_mm": D_tube*1000,
        "D_shell_mm": D_shell*1000, "L_m": L,
        "NTU": round(NTU, 2), "Cr": round(Cr, 3),
        "dp_tube_Pa": round(dp_tube, 0),
        "dp_shell_Pa": round(abs(dp_shell), 0),
        "flow_type": flow,
        "v_tube_m_s": round(v_tube, 2),
        "v_shell_m_s": round(abs(v_shell), 2),
    }
 
if __name__ == "__main__":
    r = design_shell_tube("Engine Oil", "Water",
                           T_hi=120, T_ci=20, m_dot_h=2.0,
                           m_dot_c=3.0, Q_target=80000)
    for k, v in r.items():
        print(f"  {k}: {v}")
