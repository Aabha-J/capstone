
"""
Unit tests for the Performance Analyzer.

Tests:
1. Single delivered packet
2. Multiple delivered packets
3. Throughput calculation
4. Average queuing delay
5. Maximum queuing delay
6. Packet arriving after simulation ends
7. Packet arriving exactly at simulation end
8. Empty packet list
9. No delivered packets
10. Missing energy data
11. Invalid simulation duration
12. Different packet sizes
13. Electrical vs optical performance
"""

import pytest

from software_model.simulation.simulation_engine import PacketResult
from software_model.simulation.performance_analyzer import analyze


# ============================================================
# 1. HELPER FUNCTION
# ============================================================

def make_packet(
    packet_size=100,
    generation=0,
    start=0,
    arrival=105,
    energy_per_bit=2.0,
):
    """
    Create a dummy PacketResult for testing.

    All times are in nanoseconds.
    Packet size is in bytes.
    Energy per bit is in pJ/bit.

    This helper allows us to test the Performance Analyzer
    without running the full Simulation Engine.
    """

    # Assume a fixed 5 ns physical link latency.
    link_latency = 5.0

    # Calculate when transmission finishes.
    finish = arrival - link_latency

    # Calculate serialization time.
    serialization = finish - start

    # Calculate time spent waiting.
    queue_delay = start - generation

    # Calculate total end-to-end latency.
    latency = arrival - generation

    # Calculate packet energy.
    if energy_per_bit is not None:
        energy = packet_size * 8 * energy_per_bit
    else:
        energy = None

    return PacketResult(
        source=0,
        destination=1,
        packet_size_bytes=packet_size,
        generation_ns=generation,
        start_ns=start,
        finish_tx_ns=finish,
        arrival_ns=arrival,
        queue_delay_ns=queue_delay,
        serialization_ns=serialization,
        latency_ns=latency,
        energy_pj=energy,
    )


# ============================================================
# TEST 1: SINGLE PACKET
# ============================================================

def test_single_packet():
    """
    One 100-byte packet arrives at 105 ns.

    Simulation duration = 200 ns.
    Throughput = 800 / 200 = 4 Gbps.
    """

    packets = [
        make_packet()
    ]

    metrics = analyze(
        packets,
        simulation_duration_ns=200,
    )

    assert metrics.total_packets == 1
    assert metrics.delivered_packets == 1

    assert metrics.average_latency_ns == pytest.approx(105)
    assert metrics.max_latency_ns == pytest.approx(105)

    assert metrics.throughput_gbps == pytest.approx(4.0)

    assert metrics.total_energy_pj == pytest.approx(1600)


# ============================================================
# TEST 2: MULTIPLE PACKETS
# ============================================================

def test_multiple_packets():
    """
    Packet 1 latency = 105 ns.
    Packet 2 latency = 205 ns.

    Average latency = (105 + 205) / 2 = 155 ns.
    Maximum latency = 205 ns.
    """

    packets = [
        make_packet(
            generation=0,
            start=0,
            arrival=105,
        ),
        make_packet(
            generation=0,
            start=100,
            arrival=205,
        ),
    ]

    metrics = analyze(packets, simulation_duration_ns=250)

    assert metrics.total_packets == 2
    assert metrics.delivered_packets == 2

    assert metrics.average_latency_ns == pytest.approx(155)
    assert metrics.max_latency_ns == pytest.approx(205)


# ============================================================
# TEST 3: THROUGHPUT
# ============================================================

def test_throughput():
    """
    Two packets of 100 bytes each.

    Total delivered data = 200 bytes = 1600 bits.

    Simulation duration = 250 ns.

    Throughput = 1600 / 250 = 6.4 Gbps.
    """

    packets = [
        make_packet(arrival=105),
        make_packet(start=100, arrival=205),
    ]

    metrics = analyze(packets, simulation_duration_ns=250)

    assert metrics.throughput_gbps == pytest.approx(6.4)


# ============================================================
# TEST 4: AVERAGE QUEUING DELAY
# ============================================================

def test_average_queue_delay():
    """
    Packet 1 waits 0 ns.
    Packet 2 waits 100 ns.

    Average queue delay = (0 + 100) / 2 = 50 ns.
    """

    packets = [
        make_packet(
            generation=0,
            start=0,
            arrival=105,
        ),
        make_packet(
            generation=0,
            start=100,
            arrival=205,
        ),
    ]

    metrics = analyze(packets, simulation_duration_ns=250)

    assert metrics.average_queue_delay_ns == pytest.approx(50)


# ============================================================
# TEST 5: MAXIMUM QUEUING DELAY
# ============================================================

def test_max_queue_delay():

    packets = [
        make_packet(
            generation=0,
            start=0,
            arrival=105,
        ),
        make_packet(
            generation=0,
            start=100,
            arrival=205,
        ),
    ]

    metrics = analyze(packets, simulation_duration_ns=250)

    assert metrics.max_queue_delay_ns == pytest.approx(100)


# ============================================================
# TEST 6: PACKET ARRIVES AFTER SIMULATION ENDS
# ============================================================

def test_packet_not_delivered():
    """
    Simulation ends at 200 ns.

    Packet 1 arrives at 105 ns -> delivered.
    Packet 2 arrives at 205 ns -> not delivered.

    Only Packet 1 contributes to the metrics.
    """

    packets = [
        make_packet(arrival=105),
        make_packet(start=100, arrival=205),
    ]

    metrics = analyze(packets, simulation_duration_ns=200)

    assert metrics.total_packets == 2
    assert metrics.delivered_packets == 1

    assert metrics.average_latency_ns == pytest.approx(105)
    assert metrics.max_latency_ns == pytest.approx(105)

    # 800 bits / 200 ns = 4 Gbps.
    assert metrics.throughput_gbps == pytest.approx(4)

    assert metrics.total_energy_pj == pytest.approx(1600)


# ============================================================
# TEST 7: ARRIVAL EXACTLY AT SIMULATION END
# ============================================================

def test_arrival_at_boundary():
    """
    A packet arriving exactly at the simulation end
    should count as delivered.
    """

    packets = [
        make_packet(arrival=105)
    ]

    metrics = analyze(packets, simulation_duration_ns=105)

    assert metrics.delivered_packets == 1


# ============================================================
# TEST 8: EMPTY PACKET LIST
# ============================================================

def test_empty_packets():
    """
    No generated packets.

    Throughput should be zero.
    Latency should be None.
    """

    metrics = analyze(
        [],
        simulation_duration_ns=200,
    )

    assert metrics.total_packets == 0
    assert metrics.delivered_packets == 0

    assert metrics.average_latency_ns is None
    assert metrics.max_latency_ns is None

    assert metrics.average_queue_delay_ns is None
    assert metrics.max_queue_delay_ns is None

    assert metrics.throughput_gbps == pytest.approx(0)
    assert metrics.total_energy_pj == pytest.approx(0)


# ============================================================
# TEST 9: NO DELIVERED PACKETS
# ============================================================

def test_no_delivered_packets():
    """
    A packet exists, but it arrives after the
    simulation duration.
    """

    packets = [
        make_packet(arrival=105)
    ]

    metrics = analyze(packets, simulation_duration_ns=50)

    assert metrics.total_packets == 1
    assert metrics.delivered_packets == 0

    assert metrics.average_latency_ns is None
    assert metrics.max_latency_ns is None

    assert metrics.throughput_gbps == pytest.approx(0)


# ============================================================
# TEST 10: MISSING ENERGY DATA
# ============================================================

def test_missing_energy():
    """
    If energy data is missing for a delivered packet,
    the total energy estimate should be None.
    """

    packets = [
        make_packet(
            arrival=105,
            energy_per_bit=None,
        )
    ]

    metrics = analyze(packets, simulation_duration_ns=200)

    assert metrics.total_energy_pj is None


# ============================================================
# TEST 11: INVALID SIMULATION DURATION
# ============================================================

@pytest.mark.parametrize(
    "duration",
    [0, -10, float("inf"), float("nan")],
)
def test_invalid_duration(duration):
    """
    Simulation duration must be positive and finite.
    """

    packets = [
        make_packet()
    ]

    with pytest.raises(ValueError, match="simulation_duration_ns"):
        analyze(packets, simulation_duration_ns=duration)


# ============================================================
# TEST 12: DIFFERENT PACKET SIZES
# ============================================================

def test_different_packet_sizes():
    """
    Packet 1 = 100 bytes.
    Packet 2 = 200 bytes.

    Total = 300 bytes = 2400 bits.

    Duration = 400 ns.

    Throughput = 2400 / 400 = 6 Gbps.
    """

    packets = [
        make_packet(
            packet_size=100,
            arrival=105,
        ),
        make_packet(
            packet_size=200,
            start=100,
            arrival=305,
        ),
    ]

    metrics = analyze(packets, simulation_duration_ns=400)

    assert metrics.delivered_packets == 2

    assert metrics.throughput_gbps == pytest.approx(6.0)

    # 300 bytes * 8 bits/byte * 2 pJ/bit
    assert metrics.total_energy_pj == pytest.approx(4800)


# ============================================================
# TEST 13: ELECTRICAL VS OPTICAL PERFORMANCE
# ============================================================

def test_electrical_vs_optical():
    """
    Compare two hypothetical interconnect configurations.

    Electrical packet:
        Latency = 55 ns

    Optical packet:
        Latency = 40 ns

    Verify that the analyzer reports the correct metrics.
    """

    electrical_packets = [
        make_packet(
            generation=0,
            start=0,
            arrival=55,
            energy_per_bit=2.0,
        )
    ]

    optical_packets = [
        make_packet(
            generation=0,
            start=0,
            arrival=40,
            energy_per_bit=1.0,
        )
    ]

    electrical = analyze(
        electrical_packets,
        simulation_duration_ns=100,
    )

    optical = analyze(
        optical_packets,
        simulation_duration_ns=100,
    )

    assert electrical.average_latency_ns == pytest.approx(55)
    assert optical.average_latency_ns == pytest.approx(40)

    assert optical.average_latency_ns < electrical.average_latency_ns

    # Both delivered 800 bits in 100 ns.
    assert electrical.throughput_gbps == pytest.approx(8)
    assert optical.throughput_gbps == pytest.approx(8)

    # Optical uses less energy in this example.
    assert electrical.total_energy_pj == pytest.approx(1600)
    assert optical.total_energy_pj == pytest.approx(800)
