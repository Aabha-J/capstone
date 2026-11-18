
"""
Unit tests for the two-chiplet Simulation Engine.

Tests:
1. Single packet transmission
2. Two packets competing for the same link
3. Full-duplex communication
4. Clock cycle conversion
5. Different packet sizes
6. Packets generated at different times
7. Electrical vs optical link parameters
8. Empty traffic
9. Invalid bandwidth
10. Invalid clock period
11. Invalid packet size
12. Invalid chiplet count
13. Missing route
14. Packet energy calculation

All tests use dummy inputs so we do not depend on
the unfinished Traffic Generator or Router modules.
"""

import pytest
from software_model.simulation.simulation_engine import simulate
from software_model.simulation_setup.classes import (
    Graph, Vertex, Edge, PacketEvent, TrafficTrace, RoutingEntry, RoutingTable
)
from software_model.data.enums import InterconnectType
from software_model.data.metrics import Metric, InterconnectOverall
from software_model.data.interconnect_classes.interconnect import Interconnect


class MissingRoutingTable:
    def get_route(self, source, destination):
        return None


def make_scenario(packets, bandwidth=1.0, latency=5.0, energy_per_bit=2.0):
    v0, v1 = Vertex(0), Vertex(1)
    link = Interconnect(
        interconnect_id="TEST", interconnect_type=InterconnectType.ELECTRICAL,
        bandwidth=Metric(value=bandwidth, unit="GB/s"),
        total_latency=InterconnectOverall(reported=Metric(value=latency, unit="ns")),
        energy_per_bit=(InterconnectOverall(reported=Metric(value=energy_per_bit, unit="pJ/bit"))
                        if energy_per_bit is not None else InterconnectOverall()),
    )
    graph = Graph()
    graph.add_vertex(v0)
    graph.add_vertex(v1)
    graph.add_edge(Edge(source=v0, destination=v1, distance=10.0, interconnect=link))
    traffic = TrafficTrace()
    for time, source, destination, size in packets:
        traffic.add_event(PacketEvent(time, source, destination, size))
    routing = RoutingTable()
    routing.add_entry(RoutingEntry(0, 1, [0, 1]))
    routing.add_entry(RoutingEntry(1, 0, [1, 0]))
    return graph, traffic, routing


# ============================================================
# TEST 1: SINGLE PACKET TRANSMISSION
# ============================================================

def test_single_packet():
    """
    100 bytes / 1 GB/s = 100 ns serialization.
    Additional link latency = 5 ns.
    Total latency = 105 ns.
    """

    graph, traffic, routing = make_scenario([
        (0, 0, 1, 100)
    ])

    results = simulate(graph, traffic, routing)

    assert len(results) == 1

    packet = results[0]

    assert packet.generation_ns == pytest.approx(0)
    assert packet.start_ns == pytest.approx(0)
    assert packet.serialization_ns == pytest.approx(100)
    assert packet.finish_tx_ns == pytest.approx(100)
    assert packet.arrival_ns == pytest.approx(105)
    assert packet.queue_delay_ns == pytest.approx(0)
    assert packet.latency_ns == pytest.approx(105)


# ============================================================
# TEST 2: TWO PACKETS IN THE SAME DIRECTION
# ============================================================

def test_queueing_same_direction():
    """
    Two packets are generated simultaneously.

    Packet 1:
        Starts at 0 ns
        Finishes at 100 ns
        Arrives at 105 ns

    Packet 2:
        Waits 100 ns
        Starts at 100 ns
        Finishes at 200 ns
        Arrives at 205 ns
    """

    graph, traffic, routing = make_scenario([
        (0, 0, 1, 100),
        (0, 0, 1, 100),
    ])

    results = simulate(graph, traffic, routing)

    assert len(results) == 2

    assert results[0].queue_delay_ns == pytest.approx(0)
    assert results[1].queue_delay_ns == pytest.approx(100)

    assert results[0].arrival_ns == pytest.approx(105)
    assert results[1].arrival_ns == pytest.approx(205)

    assert results[1].latency_ns == pytest.approx(205)


# ============================================================
# TEST 3: FULL-DUPLEX COMMUNICATION
# ============================================================

def test_full_duplex():
    """
    Packets travel in opposite directions.

    Since the link is full-duplex, both packets
    should transmit simultaneously.
    """

    graph, traffic, routing = make_scenario([
        (0, 0, 1, 100),
        (0, 1, 0, 100),
    ])

    results = simulate(graph, traffic, routing)

    assert results[0].start_ns == pytest.approx(0)
    assert results[1].start_ns == pytest.approx(0)

    assert results[0].arrival_ns == pytest.approx(105)
    assert results[1].arrival_ns == pytest.approx(105)

    assert results[0].queue_delay_ns == pytest.approx(0)
    assert results[1].queue_delay_ns == pytest.approx(0)


# ============================================================
# TEST 4: CLOCK CYCLE CONVERSION
# ============================================================

def test_clock_conversion():
    """
    Packet generated at cycle 10.
    Clock period = 10 ns.

    Generation time = 100 ns.
    Arrival time = 100 + 100 + 5 = 205 ns.
    """

    graph, traffic, routing = make_scenario([
        (10, 0, 1, 100)
    ])

    results = simulate(
        graph,
        traffic,
        routing,
        clock_period_ns=10.0,
    )

    assert results[0].generation_ns == pytest.approx(100)
    assert results[0].start_ns == pytest.approx(100)
    assert results[0].arrival_ns == pytest.approx(205)
    assert results[0].latency_ns == pytest.approx(105)


# ============================================================
# TEST 5: DIFFERENT PACKET SIZES
# ============================================================

def test_different_packet_sizes():
    """
    Larger packets require more serialization time.
    """

    graph, traffic, routing = make_scenario([
        (0, 0, 1, 50),
        (0, 0, 1, 200),
    ])

    results = simulate(graph, traffic, routing)

    assert results[0].serialization_ns == pytest.approx(50)
    assert results[1].serialization_ns == pytest.approx(200)

    assert results[0].arrival_ns == pytest.approx(55)
    assert results[1].arrival_ns == pytest.approx(255)


# ============================================================
# TEST 6: PACKETS GENERATED AT DIFFERENT TIMES
# ============================================================

def test_different_generation_times():
    """
    Packet 1 finishes transmitting at 100 ns.

    Packet 2 is generated at 150 ns, so it should
    transmit immediately without queuing.
    """

    graph, traffic, routing = make_scenario([
        (0, 0, 1, 100),
        (150, 0, 1, 100),
    ])

    results = simulate(graph, traffic, routing)

    assert results[0].arrival_ns == pytest.approx(105)

    assert results[1].start_ns == pytest.approx(150)
    assert results[1].queue_delay_ns == pytest.approx(0)
    assert results[1].arrival_ns == pytest.approx(255)


# ============================================================
# TEST 7: ELECTRICAL VS OPTICAL PARAMETERS
# ============================================================

def test_electrical_vs_optical():
    """
    Compare two hypothetical link configurations.

    Electrical:
        Bandwidth = 2 GB/s
        Link latency = 5 ns

    Optical:
        Bandwidth = 4 GB/s
        Link latency = 15 ns

    Both transmit a 100-byte packet.
    """

    electrical = make_scenario(
        [(0, 0, 1, 100)],
        bandwidth=2.0,
        latency=5.0,
    )

    optical = make_scenario(
        [(0, 0, 1, 100)],
        bandwidth=4.0,
        latency=15.0,
    )

    electrical_result = simulate(*electrical)
    optical_result = simulate(*optical)

    # Electrical: 100 / 2 + 5 = 55 ns
    assert electrical_result[0].latency_ns == pytest.approx(55)

    # Optical: 100 / 4 + 15 = 40 ns
    assert optical_result[0].latency_ns == pytest.approx(40)

    assert (
        optical_result[0].latency_ns
        < electrical_result[0].latency_ns
    )


# ============================================================
# TEST 8: EMPTY TRAFFIC
# ============================================================

def test_empty_traffic():
    """No generated packets should produce no results."""

    graph, traffic, routing = make_scenario([])

    results = simulate(graph, traffic, routing)

    assert results == []


# ============================================================
# TEST 9: INVALID BANDWIDTH
# ============================================================

@pytest.mark.parametrize(
    "bandwidth",
    [0.0, -1.0, float("inf"), float("nan")],
)
def test_invalid_bandwidth(bandwidth):
    """Invalid bandwidth values should be rejected."""

    graph, traffic, routing = make_scenario(
        [(0, 0, 1, 100)],
        bandwidth=bandwidth,
    )

    with pytest.raises(ValueError, match="bandwidth"):
        simulate(graph, traffic, routing)


# ============================================================
# TEST 10: INVALID CLOCK PERIOD
# ============================================================

@pytest.mark.parametrize(
    "clock_period",
    [0.0, -1.0, float("inf"), float("nan")],
)
def test_invalid_clock_period(clock_period):

    graph, traffic, routing = make_scenario([
        (0, 0, 1, 100)
    ])

    with pytest.raises(ValueError, match="clock_period_ns"):
        simulate(
            graph,
            traffic,
            routing,
            clock_period_ns=clock_period,
        )


# ============================================================
# TEST 11: INVALID PACKET SIZE
# ============================================================

@pytest.mark.parametrize(
    "packet_size",
    [0, -10, 1.5, True],
)
def test_invalid_packet_size(packet_size):

    graph, traffic, routing = make_scenario([
        (0, 0, 1, packet_size)
    ])

    with pytest.raises(ValueError, match="Packet size"):
        simulate(graph, traffic, routing)


# ============================================================
# TEST 12: INVALID CHIPLET COUNT
# ============================================================

def test_invalid_chiplet_count():
    """A three-chiplet graph must be rejected."""

    graph, traffic, routing = make_scenario([
        (0, 0, 1, 100)
    ])

    graph.vertices.append(Vertex(chiplet_id=2))

    with pytest.raises(ValueError, match="chiplets"):
        simulate(graph, traffic, routing)


# ============================================================
# TEST 13: MISSING ROUTE
# ============================================================

def test_missing_route():
    """A packet without a valid route must be rejected."""

    graph, traffic, _ = make_scenario([
        (0, 0, 1, 100)
    ])

    routing = MissingRoutingTable()

    with pytest.raises(ValueError, match="route"):
        simulate(graph, traffic, routing)


# ============================================================
# TEST 14: PACKET ENERGY
# ============================================================

def test_packet_energy():
    """
    100 bytes = 800 bits.
    Energy per bit = 2 pJ.

    Total energy = 800 * 2 = 1600 pJ.
    """

    graph, traffic, routing = make_scenario([
        (0, 0, 1, 100)
    ])

    results = simulate(graph, traffic, routing)

    assert results[0].energy_pj == pytest.approx(1600)


def test_missing_energy_data():
    """Missing energy data should produce None, not zero."""

    graph, traffic, routing = make_scenario(
        [(0, 0, 1, 100)],
        energy_per_bit=None,
    )

    results = simulate(graph, traffic, routing)

    assert results[0].energy_pj is None
