"""Streamlit GUI for the capstone two-chiplet packet simulator.

Run from the repository root:
    python -m pip install streamlit
    python -m streamlit run capstone_dashboard_enhanced.py --server.port 8080

This UI uses the existing simulate() and analyze() functions. It builds
minimal input objects with the attributes those functions expect, so it can
run independently of the unfinished graph/traffic/router generators.
"""

from dataclasses import dataclass
from types import SimpleNamespace

import json
import math

import pandas as pd
import streamlit as st

from software_model.simulation.simulation_engine import simulate
from software_model.simulation.performance_analyzer import analyze


@dataclass
class TestVertex:
    chiplet_id: int


@dataclass
class TestLink:
    bandwidth: float
    total_latency: float
    energy_per_bit: float | None


@dataclass
class TestEdge:
    source: TestVertex
    destination: TestVertex
    link: TestLink


@dataclass
class TestPacket:
    generation_time: float
    source: int
    destination: int
    packet_size: int


class DirectRouting:
    """Minimal direct routing table for the current two-chiplet scope."""

    def get_route(self, source: int, destination: int) -> list[int] | None:
        if (source, destination) in ((0, 1), (1, 0)):
            return [source, destination]
        return None


def build_inputs(rows: pd.DataFrame, bandwidth: float, latency: float,
                 energy_per_bit: float | None):
    """Adapt editable GUI rows to the engine's input contract."""
    v0, v1 = TestVertex(0), TestVertex(1)
    link = TestLink(bandwidth, latency, energy_per_bit)
    graph = SimpleNamespace(vertices=[v0, v1], edges=[TestEdge(v0, v1, link)])
    traffic = SimpleNamespace(events=[
        TestPacket(
            generation_time=float(row["Generation cycle"]),
            source=int(row["Source"]),
            destination=int(row["Destination"]),
            packet_size=int(row["Size (bytes)"]),
        )
        for _, row in rows.iterrows()
    ])
    return graph, traffic, DirectRouting()


def example_packets() -> pd.DataFrame:
    return pd.DataFrame([
        {"Generation cycle": 0.0, "Source": 0, "Destination": 1, "Size (bytes)": 100},
        {"Generation cycle": 0.0, "Source": 0, "Destination": 1, "Size (bytes)": 100},
        {"Generation cycle": 0.0, "Source": 1, "Destination": 0, "Size (bytes)": 100},
        {"Generation cycle": 150.0, "Source": 0, "Destination": 1, "Size (bytes)": 200},
    ])


st.set_page_config(page_title="Chiplet Interconnect Simulator", page_icon="🔬", layout="wide")
st.markdown("""<style>
.block-container {padding-top: 1.5rem; max-width: 1400px;}
[data-testid="stMetric"] {background: rgba(120,140,170,.09); border: 1px solid rgba(120,140,170,.18); border-radius: 12px; padding: 16px;}
h1 {letter-spacing: -0.035em;}
</style>""", unsafe_allow_html=True)
st.title("Chiplet Interconnect Simulator")
st.caption("Two-chiplet full-duplex link · Simulation Engine + Performance Analyzer")

with st.sidebar:
    st.header("Link configuration")
    link_kind = st.selectbox("Link type (label)", ["Electrical", "Optical", "Hybrid"])
    st.caption("Link type is a label. The numerical parameters below determine the simulation behavior.")
    bandwidth = st.number_input("Bandwidth (GB/s)", min_value=0.001, value=1.0, step=0.5)
    link_latency = st.number_input("Additional link latency (ns)", min_value=0.0, value=5.0, step=1.0)
    energy_known = st.checkbox("Energy per bit is known", value=True)
    energy_per_bit = (st.number_input("Energy per bit (pJ/bit)", min_value=0.0,
                                      value=2.0, step=0.5)
                      if energy_known else None)
    st.header("Simulation configuration")
    clock_period = st.number_input("Clock period (ns/cycle)", min_value=0.001, value=1.0)
    duration = st.number_input("Measurement duration (ns)", min_value=0.001, value=500.0, step=50.0)

st.subheader("1 · Configure packets")
st.write("Edit the packet rows or add more. Valid directions are 0 → 1 and 1 → 0.")
if "packet_rows" not in st.session_state:
    st.session_state.packet_rows = example_packets()

edited = st.data_editor(
    st.session_state.packet_rows,
    num_rows="dynamic",
    hide_index=True,
    use_container_width=True,
    column_config={
        "Generation cycle": st.column_config.NumberColumn(min_value=0, step=1, required=True),
        "Source": st.column_config.SelectboxColumn(options=[0, 1], required=True),
        "Destination": st.column_config.SelectboxColumn(options=[0, 1], required=True),
        "Size (bytes)": st.column_config.NumberColumn(min_value=1, step=1, required=True),
    },
    key="packet_editor",
)

if st.button("Run simulation", type="primary"):
    try:
        if edited.isnull().any().any():
            raise ValueError("Complete all cells before running the simulation.")
        for _, row in edited.iterrows():
            if row["Source"] == row["Destination"]:
                raise ValueError("A packet's source and destination must be different.")
            if int(row["Size (bytes)"]) != row["Size (bytes)"] or row["Size (bytes)"] <= 0:
                raise ValueError("Packet sizes must be positive whole numbers.")
            if row["Generation cycle"] < 0:
                raise ValueError("Generation cycles must be nonnegative.")
        graph, traffic, routing = build_inputs(edited, bandwidth, link_latency, energy_per_bit)
        results = simulate(graph, traffic, routing, clock_period_ns=clock_period)
        metrics = analyze(results, simulation_duration_ns=duration)
        st.session_state.sim_output = (results, metrics, duration, link_kind)
    except (ValueError, TypeError) as exc:
        st.error(f"Simulation input error: {exc}")

if "sim_output" in st.session_state:
    results, metrics, run_duration, run_link_kind = st.session_state.sim_output
    st.subheader(f"2 · Performance summary — {run_link_kind}")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Delivered packets", f"{metrics.delivered_packets} / {metrics.total_packets}")
    c2.metric("Throughput", f"{metrics.throughput_gbps:.3f} Gbps")
    c3.metric("Average latency", "N/A" if metrics.average_latency_ns is None else f"{metrics.average_latency_ns:.2f} ns")
    c4.metric("Max latency", "N/A" if metrics.max_latency_ns is None else f"{metrics.max_latency_ns:.2f} ns")
    c5, c6, c7 = st.columns(3)
    c5.metric("Average queue delay", "N/A" if metrics.average_queue_delay_ns is None else f"{metrics.average_queue_delay_ns:.2f} ns")
    c6.metric("Max queue delay", "N/A" if metrics.max_queue_delay_ns is None else f"{metrics.max_queue_delay_ns:.2f} ns")
    c7.metric("Delivered-packet energy", "N/A" if metrics.total_energy_pj is None else f"{metrics.total_energy_pj:.2f} pJ")

    st.subheader("3 · Packet-by-packet results")
    records = [
        {
            "Packet": i + 1,
            "Direction": f"{r.source} → {r.destination}",
            "Size (bytes)": r.packet_size_bytes,
            "Generated (ns)": r.generation_ns,
            "Start TX (ns)": r.start_ns,
            "Finish TX (ns)": r.finish_tx_ns,
            "Arrival (ns)": r.arrival_ns,
            "Queue (ns)": r.queue_delay_ns,
            "Serialization (ns)": r.serialization_ns,
            "Latency (ns)": r.latency_ns,
            "Energy (pJ)": r.energy_pj,
            "Status": "Delivered" if r.arrival_ns <= run_duration else "Outside window",
        }
        for i, r in enumerate(results)
    ]
    result_df = pd.DataFrame(records)
    st.dataframe(result_df, hide_index=True, use_container_width=True)

    if not result_df.empty:
        st.subheader("4 · Packet timing")
        st.caption("Bars show serialization intervals. The receiver arrival time also includes the additional link latency.")
        try:
            import altair as alt
            chart = alt.Chart(result_df).mark_bar(size=22).encode(
                x=alt.X("Start TX (ns):Q", title="Simulation time (ns)"),
                x2="Finish TX (ns):Q",
                y=alt.Y("Packet:N", sort="ascending"),
                color=alt.Color("Direction:N"),
                tooltip=["Packet", "Direction", "Generated (ns)", "Start TX (ns)",
                         "Finish TX (ns)", "Arrival (ns)", "Queue (ns)", "Latency (ns)", "Status"],
            ).properties(height=max(200, len(result_df) * 42))
            st.altair_chart(chart, use_container_width=True)
        except ImportError:
            st.info("Install Altair to see the packet timing chart: python -m pip install altair")
        st.subheader("5 · Latency by packet")
        st.bar_chart(result_df.set_index("Packet")[["Latency (ns)"]])
        st.download_button("Download packet results (CSV)", data=result_df.to_csv(index=False),
                           file_name="packet_results.csv", mime="text/csv")

    st.info("Throughput and latency metrics count only packets arriving by the measurement deadline. "
            "Energy is the sum for delivered packets with known energy values; it is not total system power.")
else:
    st.info("Configure the link and packets, then click **Run simulation** to display results.")

# ============================================================
# RESEARCH VALIDATION — compare metrics with published references
# ============================================================
st.divider()
st.subheader("6 · Research validation")
st.caption("Upload published benchmark results as JSON. Values are only comparable when units, packet size, load, distance, and measurement definitions match.")
with st.expander("Reference JSON format", expanded=False):
    st.code('''{
  "source": "Paper title, DOI or citation",
  "conditions": "100-byte packets; 2-chiplet direct link; 500 ns window",
  "reference_metrics": {
    "average_latency_ns": 105.0,
    "throughput_gbps": 1.6,
    "total_energy_pj": 1600.0
  }
}''', language="json")

reference_file = st.file_uploader("Upload reference metrics (.json)", type=["json"])
tolerance = st.number_input("Allowed relative error (%)", min_value=0.0, max_value=1000.0, value=10.0, step=1.0)
if reference_file is not None:
    try:
        reference = json.load(reference_file)
        if not isinstance(reference, dict) or not isinstance(reference.get("reference_metrics"), dict):
            raise ValueError("JSON must contain a 'reference_metrics' object.")
        st.write("**Source:**", reference.get("source", "Not specified"))
        st.write("**Benchmark conditions:**", reference.get("conditions", "Not specified — verify comparability before interpreting results"))
        if "sim_output" not in st.session_state:
            st.warning("Run a simulation first to compare its metrics with the reference.")
        else:
            _, current_metrics, _, _ = st.session_state.sim_output
            comparisons = []
            allowed = {"average_latency_ns", "max_latency_ns", "average_queue_delay_ns", "max_queue_delay_ns", "throughput_gbps", "total_energy_pj", "delivered_packets", "total_packets"}
            for name, ref in reference["reference_metrics"].items():
                if name not in allowed:
                    comparisons.append({"Metric": name, "Simulated": "—", "Reference": str(ref), "Error (%)": "—", "Status": "Unsupported metric"})
                    continue
                value = getattr(current_metrics, name)
                if value is None or isinstance(ref, bool) or not isinstance(ref, (int, float)) or not math.isfinite(ref):
                    comparisons.append({"Metric": name, "Simulated": str(value), "Reference": str(ref), "Error (%)": "—", "Status": "Not validated"})
                    continue
                err = 0.0 if ref == value == 0 else (math.inf if ref == 0 else abs(value-ref)/abs(ref)*100)
                comparisons.append({"Metric": name, "Simulated": value, "Reference": ref, "Error (%)": round(err, 3) if math.isfinite(err) else "∞", "Status": "Within tolerance" if err <= tolerance else "Outside tolerance"})
            if comparisons:
                validation_df = pd.DataFrame(comparisons)
                st.dataframe(validation_df, hide_index=True, use_container_width=True)
                st.download_button("Download validation results (CSV)", validation_df.to_csv(index=False), "validation_results.csv", "text/csv")
            else:
                st.warning("The reference_metrics object is empty.")
    except (json.JSONDecodeError, ValueError, TypeError) as exc:
        st.error(f"Could not read reference JSON: {exc}")

st.caption("Validation compares reported numerical metrics only; it does not verify that the underlying paper and simulation use equivalent physical assumptions.")
