import streamlit as st
import plotly.graph_objects as go
import numpy as np
from hx_engine import FLUIDS, design_shell_tube, effectiveness_ntu
 
st.set_page_config(page_title="Heat Exchanger Designer",
                   page_icon="\U0001f525", layout="wide")
st.title("\U0001f525 Shell-and-Tube Heat Exchanger Design Tool")
st.markdown("**LMTD + \u03B5-NTU methods \u2013 Thermodynamics & "
            "Process Equipment concept**")
st.divider()
 
# ── SIDEBAR ──
st.sidebar.header("\U0001f321\uFE0F Fluid Selection")
hot_fluid = st.sidebar.selectbox("Hot fluid", list(FLUIDS.keys()), index=1)
cold_fluid = st.sidebar.selectbox("Cold fluid", list(FLUIDS.keys()), index=0)
st.sidebar.header("\U0001f321\uFE0F Operating Conditions")
T_hi = st.sidebar.number_input("Hot inlet T (\u00B0C)", 30, 500, 120)
T_ci = st.sidebar.number_input("Cold inlet T (\u00B0C)", 0, 200, 20)
m_dot_h = st.sidebar.slider("Hot mass flow (kg/s)", 0.1, 10.0, 2.0, 0.1)
m_dot_c = st.sidebar.slider("Cold mass flow (kg/s)", 0.1, 10.0, 3.0, 0.1)
Q_target = st.sidebar.slider("Target duty (kW)", 10, 500, 80) * 1000
st.sidebar.header("\U0001f527 Geometry")
D_tube = st.sidebar.select_slider("Tube OD (mm)",
    [10,12,16,19,25,32,38], value=19) / 1000
N_tubes = st.sidebar.slider("Number of tubes", 10, 200, 50)
L = st.sidebar.slider("Tube length (m)", 0.5, 6.0, 2.0, 0.25)
D_shell = st.sidebar.slider("Shell ID (mm)", 100, 800, 300) / 1000
flow = st.sidebar.selectbox("Flow arrangement",
    ["counter", "parallel"], index=0)
 
# ── CALCULATE ──
r = design_shell_tube(hot_fluid, cold_fluid, T_hi, T_ci,
                       m_dot_h, m_dot_c, Q_target,
                       D_tube, D_shell, N_tubes, L, flow)
 
if "error" in r:
    st.error(f"\u274C {r['error']}")
    st.stop()
 
# ── KPIs ──
c1,c2,c3,c4,c5 = st.columns(5)
with c1: st.metric("Q actual", f"{r['Q_actual_kW']:.1f} kW")
with c2: st.metric("LMTD", f"{r['LMTD']:.1f} \u00B0C")
with c3: st.metric("U overall", f"{r['U_overall']:.0f} W/m\u00B2K")
with c4: st.metric("\u03B5 effectiveness", f"{r['eff_ntu']:.1%}")
with c5: st.metric("NTU", f"{r['NTU']:.2f}")
 
st.divider()
col1, col2 = st.columns(2)
 
# ── TEMPERATURE PROFILE ──
with col1:
    st.subheader("\U0001f321\uFE0F Temperature Profile")
    x = [0, 0.25, 0.5, 0.75, 1.0]
    Th = [r["T_hi"]]
    Tc_counter = [r["T_co"]] if flow=="counter" else [r["T_ci"]]
    for frac in [0.25, 0.5, 0.75, 1.0]:
        Th.append(r["T_hi"] - frac*(r["T_hi"]-r["T_ho"]))
        if flow=="counter":
            Tc_counter.append(r["T_co"] - frac*(r["T_co"]-r["T_ci"]))
        else:
            Tc_counter.append(r["T_ci"] + frac*(r["T_co"]-r["T_ci"]))
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=x, y=Th, name=f"Hot ({hot_fluid})",
        line=dict(color="#E74C3C", width=3)))
    fig.add_trace(go.Scatter(x=x, y=Tc_counter,
        name=f"Cold ({cold_fluid})",
        line=dict(color="#3498DB", width=3)))
    fig.update_layout(xaxis_title="Position along HX",
        yaxis_title="Temperature (\u00B0C)", height=350,
        template="plotly_white")
    st.plotly_chart(fig, use_container_width=True)
 
# ── EFFECTIVENESS vs NTU ──
with col2:
    st.subheader("\u03B5-NTU Performance Curve")
    ntu_range = np.linspace(0.01, 6, 100)
    fig2 = go.Figure()
    for cr in [0, 0.25, 0.5, 0.75, 1.0]:
        eff = [effectiveness_ntu(n, cr, flow) for n in ntu_range]
        fig2.add_trace(go.Scatter(x=ntu_range, y=eff,
            name=f"Cr={cr:.2f}", mode="lines"))
    # Mark operating point
    fig2.add_trace(go.Scatter(x=[r["NTU"]], y=[r["eff_ntu"]],
        mode="markers", name="Operating point",
        marker=dict(size=12, color="red", symbol="star")))
    fig2.update_layout(xaxis_title="NTU",
        yaxis_title="Effectiveness \u03B5", height=350,
        template="plotly_white")
    st.plotly_chart(fig2, use_container_width=True)
 
# ── DETAILED RESULTS ──
st.subheader("\U0001f4cb Design Summary")
col3, col4, col5 = st.columns(3)
with col3:
    st.markdown("**Thermal Performance**")
    st.markdown(f"- Q target: {r['Q_target_kW']} kW")
    st.markdown(f"- Q max: {r['Q_max_kW']} kW")
    st.markdown(f"- Q actual: {r['Q_actual_kW']} kW")
    st.markdown(f"- LMTD: {r['LMTD']} \u00B0C")
    st.markdown(f"- T hot out: {r['T_ho']} \u00B0C")
    st.markdown(f"- T cold out: {r['T_co']} \u00B0C")
with col4:
    st.markdown("**Heat Transfer**")
    st.markdown(f"- U overall: {r['U_overall']} W/m\u00B2K")
    st.markdown(f"- h tube: {r['h_tube']} W/m\u00B2K")
    st.markdown(f"- h shell: {r['h_shell']} W/m\u00B2K")
    st.markdown(f"- Re tube: {r['Re_tube']:.0f}")
    st.markdown(f"- Re shell: {r['Re_shell']:.0f}")
    st.markdown(f"- Flow: {'Turbulent' if r['Re_tube']>2300 else 'Laminar'}")
with col5:
    st.markdown("**Geometry & Sizing**")
    st.markdown(f"- A required: {r['A_required_m2']} m\u00B2")
    st.markdown(f"- A available: {r['A_available_m2']} m\u00B2")
    ok_txt = "\u2705" if r['A_available_m2'] >= r['A_required_m2'] else "\u274C"
    st.markdown(f"- Sufficient area: {ok_txt}")
    st.markdown(f"- L required: {r['L_required_m']} m")
    st.markdown(f"- \u0394P tube: {r['dp_tube_Pa']:.0f} Pa")
    st.markdown(f"- \u0394P shell: {r['dp_shell_Pa']:.0f} Pa")
 
st.divider()
st.caption("Heat Exchanger Design Tool | Thermodynamics & Process "
           "Equipment | Built by Oscar Vincent Dbritto | "
           )