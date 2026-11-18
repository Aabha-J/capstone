import math

import pytest
from software_model.simulation_setup.generate_graph import generate_graph
from software_model.data.enums import InterconnectType, Topology, TrafficPattern
from software_model.data.experiment_classes import ExperimentConfig
from software_model.data.interconnect_classes.interconnect import Interconnect
from software_model.data.interconnect_classes.channel import Channel
from software_model.data.metrics import InterconnectOverall, Metric, MeasurementStatus


# --------------------------------------------------
# Test helpers
# --------------------------------------------------

def make_interconnect(interconnect_type=InterconnectType.ELECTRICAL, **overrides):
    """Create a representative interconnect using the current metric model."""
    properties = {
        "bandwidth": 64.0,
        "energy_per_bit": 2.5,
        "area": 1.5,
        "total_latency": None,
        "phy_latency": 1.0,
        "propagation_delay": 2.0,
        "eo_conversion_latency": None,
        "oe_conversion_latency": None,
    }
    properties.update(overrides)

    def overall(value, unit):
        return InterconnectOverall(
            reported=Metric(value=value, unit=unit) if value is not None else None
        )

    interconnect = Interconnect(
        interconnect_id="TEST_001",
        interconnect_type=interconnect_type,
        bandwidth=(Metric(properties["bandwidth"], "GB/s")
                   if properties["bandwidth"] is not None else None),
        energy_per_bit=overall(properties["energy_per_bit"], "pJ/bit"),
        area=overall(properties["area"], "mm²"),
        phy_latency=overall(properties["phy_latency"], "ns"),
        total_latency=overall(properties["total_latency"], "ns"),
        channel=Channel(
            propagation_delay=(Metric(properties["propagation_delay"], "ns")
                               if properties["propagation_delay"] is not None else None)
        ),
    )
    # E/O and O/E conversion delays are not separate fields on the current
    # Interconnect dataclass. Keep their test values in the component breakdown
    # rather than silently treating them as part of the reported total.
    for name in ("eo_conversion_latency", "oe_conversion_latency"):
        value = properties[name]
        if value is not None:
            interconnect.total_latency.components[name] = Metric(value, "ns")
    return interconnect


def make_config(topology, chiplet_count, link_distance=10.0):
    """Create a test experiment configuration."""

    return ExperimentConfig(
        config_id="TEST_EXP",
        chiplet_count=chiplet_count,
        topology=topology,
        link_distance=link_distance,
        traffic_pattern=TrafficPattern.UNIFORM,
        packet_size=64,
        injection_rate=0.1,
        duration=1000,
        seed=1,
    )


def get_edge_pairs(graph):
    """Return edge connections as unordered chiplet ID pairs."""

    return {
        frozenset((
            edge.source.chiplet_id,
            edge.destination.chiplet_id,
        ))
        for edge in graph.edges
    }


# --------------------------------------------------
# Topology tests
# --------------------------------------------------

@pytest.mark.parametrize(
    "topology",
    [
        Topology.MESH,
        Topology.RING,
        Topology.DIRECT,
    ],
)
@pytest.mark.parametrize("chiplet_count", range(1, 10))
def test_generate_graph_vertex_count(topology, chiplet_count):
    """Every topology should create the requested number of vertices."""

    graph = generate_graph(
        make_interconnect(),
        make_config(topology, chiplet_count),
    )

    assert len(graph.vertices) == chiplet_count


@pytest.mark.parametrize("chiplet_count", range(1, 10))
def test_mesh_edge_count(chiplet_count):
    """Check the number of horizontal and vertical mesh connections."""

    expected_counts = {
        1: 0,
        2: 1,
        3: 2,
        4: 4,
        5: 5,
        6: 7,
        7: 8,
        8: 10,
        9: 12,
    }

    graph = generate_graph(
        make_interconnect(),
        make_config(Topology.MESH, chiplet_count),
    )

    assert len(graph.edges) == expected_counts[chiplet_count]


@pytest.mark.parametrize("chiplet_count", range(1, 10))
def test_ring_edge_count(chiplet_count):
    """Check that the ring is closed when there are at least 3 chiplets."""

    graph = generate_graph(
        make_interconnect(),
        make_config(Topology.RING, chiplet_count),
    )

    expected_count = (
        0 if chiplet_count == 1
        else 1 if chiplet_count == 2
        else chiplet_count
    )

    assert len(graph.edges) == expected_count


@pytest.mark.parametrize("chiplet_count", range(1, 10))
def test_direct_edge_count(chiplet_count):
    """Every chiplet should connect to every other chiplet."""

    graph = generate_graph(
        make_interconnect(),
        make_config(Topology.DIRECT, chiplet_count),
    )

    expected_count = chiplet_count * (chiplet_count - 1) // 2

    assert len(graph.edges) == expected_count


@pytest.mark.parametrize(
    "topology",
    [
        Topology.MESH,
        Topology.RING,
        Topology.DIRECT,
    ],
)
@pytest.mark.parametrize("chiplet_count", range(1, 10))
def test_graph_has_no_duplicate_or_self_edges(topology, chiplet_count):
    """Check that edges connect distinct chiplets without duplicates."""

    graph = generate_graph(
        make_interconnect(),
        make_config(topology, chiplet_count),
    )

    edge_pairs = get_edge_pairs(graph)

    assert len(edge_pairs) == len(graph.edges)

    for edge in graph.edges:
        assert edge.source != edge.destination


# --------------------------------------------------
# Edge and link property tests
# --------------------------------------------------

def test_edge_distance_is_copied_from_config():
    """Every generated edge should use the configured link distance."""

    graph = generate_graph(
        make_interconnect(),
        make_config(Topology.RING, 4, link_distance=25.0),
    )

    assert all(edge.distance == 25.0 for edge in graph.edges)


def test_link_properties_are_copied():
    """Each generated edge retains the interconnect and its reported metrics."""
    interconnect = make_interconnect(
        bandwidth=128.0, energy_per_bit=1.5, area=2.0, total_latency=8.0
    )
    graph = generate_graph(interconnect, make_config(Topology.RING, 3))
    for edge in graph.edges:
        assert edge.interconnect is interconnect
        assert edge.interconnect.bandwidth.value == pytest.approx(128.0)
        assert edge.interconnect.energy_per_bit.value == pytest.approx(1.5)
        assert edge.interconnect.area.value == pytest.approx(2.0)
        assert edge.interconnect.total_latency.value == pytest.approx(8.0)


def test_partial_latency_components_are_preserved():
    """Missing propagation delay must not be invented as a complete total."""
    interconnect = make_interconnect(
        total_latency=None, phy_latency=1.0, propagation_delay=None
    )
    graph = generate_graph(interconnect, make_config(Topology.RING, 3))
    for edge in graph.edges:
        link = edge.interconnect
        assert link is interconnect
        assert link.total_latency.value is None
        assert link.phy_latency.value == pytest.approx(1.0)
        assert link.channel.propagation_delay is None


def test_missing_link_properties_are_preserved():
    """Unavailable metrics remain unavailable; reported latency is preserved."""
    interconnect = make_interconnect(
        bandwidth=None, energy_per_bit=None, area=None,
        total_latency=5.0, phy_latency=None, propagation_delay=None
    )
    graph = generate_graph(interconnect, make_config(Topology.RING, 3))
    for edge in graph.edges:
        link = edge.interconnect
        assert link.bandwidth is None
        assert link.energy_per_bit.value is None
        assert link.energy_per_bit.status == MeasurementStatus.UNAVAILABLE
        assert link.area.value is None
        assert link.total_latency.value == pytest.approx(5.0)
        assert link.phy_latency.value is None
        assert link.channel.propagation_delay is None


def test_optical_total_latency_includes_conversion():
    """Preserve reported optical latency and available conversion inputs.

    The current Interconnect model has no dedicated E/O or O/E latency fields,
    so this test does not claim that calculate_total_latency adds them.
    """
    interconnect = make_interconnect(
        interconnect_type=InterconnectType.OPTICAL,
        total_latency=10.0, phy_latency=1.0, propagation_delay=2.0,
        eo_conversion_latency=3.0, oe_conversion_latency=4.0,
    )
    graph = generate_graph(interconnect, make_config(Topology.RING, 3))
    for edge in graph.edges:
        link = edge.interconnect
        assert link is interconnect
        assert link.total_latency.value == pytest.approx(10.0)
        assert link.phy_latency.value == pytest.approx(1.0)
        assert link.channel.propagation_delay.value == pytest.approx(2.0)
        assert link.total_latency.components["eo_conversion_latency"].value == 3.0
        assert link.total_latency.components["oe_conversion_latency"].value == 4.0


# --------------------------------------------------
# Visual check
# --------------------------------------------------

def visualize_small_graphs():
    """
    Display Mesh, Ring, and Direct topologies with four chiplets each.

    Run this separately from pytest.
    """

    import matplotlib.pyplot as plt

    interconnect = make_interconnect()

    topologies = [
        Topology.MESH,
        Topology.RING,
        Topology.DIRECT,
    ]

    fig, axes = plt.subplots(1, 3, figsize=(14, 5))

    for ax, topology in zip(axes, topologies):
        graph = generate_graph(
            interconnect,
            make_config(topology, 4),
        )

        # Position nodes.
        if topology == Topology.MESH:
            positions = {
                vertex.chiplet_id: (
                    vertex.chiplet_id % 2,
                    -(vertex.chiplet_id // 2),
                )
                for vertex in graph.vertices
            }
        else:
            positions = {
                vertex.chiplet_id: (
                    math.cos(2 * math.pi * vertex.chiplet_id / 4),
                    math.sin(2 * math.pi * vertex.chiplet_id / 4),
                )
                for vertex in graph.vertices
            }

        # Draw edges.
        for edge in graph.edges:
            source = positions[edge.source.chiplet_id]
            destination = positions[edge.destination.chiplet_id]

            ax.plot(
                [source[0], destination[0]],
                [source[1], destination[1]],
                linewidth=2,
            )

        # Draw vertices and labels.
        for chiplet_id, (x, y) in positions.items():
            ax.scatter(x, y, s=500, zorder=2)
            ax.text(
                x,
                y,
                str(chiplet_id),
                ha="center",
                va="center",
                color="white",
                zorder=3,
            )

        ax.set_title(topology.value)
        ax.axis("equal")
        ax.axis("off")

    plt.tight_layout()
    plt.show()


if __name__ == "__main__":
    visualize_small_graphs()