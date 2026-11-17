"""
Performance Analyzer for the two-chiplet capstone model.

Purpose:
    Analyze packet results produced by the Simulation Engine.

Input:
    A list of PacketResult objects.
    Total simulation duration in nanoseconds.

Output:
    Performance metrics:
        - Total generated packets
        - Total delivered packets
        - Average packet latency
        - Maximum packet latency
        - Average queuing delay
        - Maximum queuing delay
        - Throughput in Gbps
        - Total delivered communication energy

Important assumptions:
    1. Only packets arriving within the simulation
       duration count as delivered.

    2. Latency and queue metrics are calculated
       using delivered packets only.

    3. Throughput is measured over the entire
       simulation duration.

    4. Energy is calculated only for delivered
       packets with known energy values.
"""

from dataclasses import dataclass
from math import isfinite
from typing import Optional, Sequence

from software_model.simulation.simulation_engine import PacketResult

# 1. PERFORMANCE METRICS DATA CLASS
@dataclass(frozen=True)
class PerformanceMetrics:
    """
    Stores the final performance results.
    The Simulation Engine returns one PacketResult for each packet.
    The Performance Analyzer combines those results into a 
    single PerformanceMetrics object.
    """
    total_packets: int
    delivered_packets: int
    average_latency_ns: Optional[float]
    max_latency_ns: Optional[float]
    average_queue_delay_ns: Optional[float]
    max_queue_delay_ns: Optional[float]
    throughput_gbps: float
    total_energy_pj: Optional[float]

# 2. MAIN PERFORMANCE ANALYZER FUNCTION
def analyze(
    packet_results: Sequence[PacketResult],
    simulation_duration_ns: float,
) -> PerformanceMetrics:
    """
    Calculate performance metrics from simulated packets.
    Parameters
    ----------
    packet_results:
        Results returned by simulation_engine.simulate().

    simulation_duration_ns:
        Total simulation measurement duration in ns.

    Returns
    -------
    PerformanceMetrics:
        Aggregated latency, throughput, queueing,
        and energy measurements.
    """

    # STEP 1: VALIDATE SIMULATION DURATION
    # Simulation duration must be a positive finite number.
    if (
        not isfinite(simulation_duration_ns)
        or simulation_duration_ns <= 0
    ):
        raise ValueError(
            "simulation_duration_ns must be finite and positive"
        )

    # STEP 2: COUNT ALL GENERATED PACKETS
    # The Simulation Engine produces one result per packet.
    total_packets = len(packet_results)

    # STEP 3: IDENTIFY DELIVERED PACKETS
    # A packet counts as delivered only if it arrives
    # before or exactly at the end of the simulation.
    # Example:
    #     Simulation duration = 200 ns
    #     Packet A arrives at 105 ns -> delivered
    #     Packet B arrives at 205 ns -> not delivered
    delivered = [
        packet
        for packet in packet_results
        if packet.arrival_ns <= simulation_duration_ns
    ]

    # Count successfully delivered packets.
    delivered_packets = len(delivered)

    # STEP 4: CALCULATE LATENCY METRICS
    if delivered_packets > 0:
        # Add all delivered packet latencies.
        total_latency = sum(
            packet.latency_ns
            for packet in delivered
        )

        # Average latency = total latency / packet count.
        average_latency = (
            total_latency / delivered_packets
        )

        # Maximum latency = largest packet latency.
        max_latency = max(
            packet.latency_ns
            for packet in delivered
        )
    else:
        # No delivered packets means there is no meaningful average or maximum latency.
        average_latency = None
        max_latency = None

    # STEP 5: CALCULATE QUEUING DELAY
    if delivered_packets > 0:
        # Total time packets spent waiting for the link.
        total_queue_delay = sum(
            packet.queue_delay_ns
            for packet in delivered
        )

        # Avg queueing delay
        average_queue_delay = (
            total_queue_delay / delivered_packets
        )

        # Max queueing delay
        max_queue_delay = max(
            packet.queue_delay_ns
            for packet in delivered
        )
    else:
        average_queue_delay = None
        max_queue_delay = None

    # STEP 6: CALCULATE THROUGHPUT
    # Throughput measures how much data was successfully
    # delivered per unit of simulation time.
    
    # Formula:
    # Throughput (Gbps) =
    #     Total delivered bits / Simulation duration (ns)
    # Numerically, bits/ns = Gbps.
    # Count all delivered bytes.
    delivered_bytes = sum(
        packet.packet_size_bytes
        for packet in delivered
    )

    # Convert bytes to bits
    delivered_bits = delivered_bytes * 8

    # Calculate throughput in gigabits per second.
    throughput = (
        delivered_bits / simulation_duration_ns
    )

    # STEP 7: CALCULATE COMMUNICATION ENERGY
    # Energy per packet was already calculated by the
    # Simulation Engine:
    # Packet energy = packet bits * link energy per bit
    # Here, we sum the energy for delivered packets.

    # First check whether energy data is available for every delivered packet.
    if all(
        packet.energy_pj is not None
        for packet in delivered
    ):
        total_energy = sum(
            packet.energy_pj
            for packet in delivered
        )

    else:
        # If any delivered packet has missing energy information, we cannot 
        # calculate a complete total energy estimate.
        total_energy = None

    # STEP 8: RETURN THE PERFORMANCE METRICS
    return PerformanceMetrics(
        total_packets=total_packets,
        delivered_packets=delivered_packets,
        average_latency_ns=average_latency,
        max_latency_ns=max_latency,
        average_queue_delay_ns=average_queue_delay,
        max_queue_delay_ns=max_queue_delay,
        throughput_gbps=throughput,
        total_energy_pj=total_energy,
    )
