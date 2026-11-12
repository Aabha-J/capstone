import math

import pytest
from software_model.simulation_setup.generate_graph import generate_graph
from software_model.data.data_classes import (
    Interconnect,
    InterconnectType,
    ExperimentConfig,
    Topology,
    TrafficPattern,
)


# --------------------------------------------------
# Test helpers
# --------------------------------------------------

def make_interconnect(
    interconnect_type=InterconnectType.ELECTRICAL,
    **overrides,
):
    """Create an interconnect with test properties."""

    interconnect = Interconnect(
        interconnect_id="TEST_001",
        interconnect_type=interconnect_type,
    )

    # Default properties.
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

    for attribute, value in properties.items():
        setattr(interconnect, attribute, value)

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
    """Check that interconnect properties are transferred to graph links."""

    interconnect = make_interconnect(
        bandwidth=128.0,
        energy_per_bit=1.5,
        area=2.0,
        total_latency=8.0,
    )

    graph = generate_graph(
        interconnect,
        make_config(Topology.RING, 3),
    )

    for edge in graph.edges:
        assert edge.link.bandwidth == 128.0
        assert edge.link.energy_per_bit == 1.5
        assert edge.link.area == 2.0

        # Existing total latency takes priority.
        assert edge.link.total_latency == 8.0



def test_partial_latency_components_are_preserved():
    """Keep known latency values even if total latency cannot be calculated."""

    interconnect = make_interconnect(
        total_latency=None,
        phy_latency=1.0,
        propagation_delay=None,
    )

    graph = generate_graph(
        interconnect,
        make_config(Topology.RING, 3),
    )

    for edge in graph.edges:
        assert edge.link.total_latency is None
        assert len(edge.link.latency_components) == 1
        assert edge.link.known_latency == 1.0


def test_missing_link_properties_are_preserved():
    """Missing interconnect properties should remain None, even if total latency given"""

    interconnect = make_interconnect(
        bandwidth=None,
        energy_per_bit=None,
        area=None,
        total_latency=5.0,
        phy_latency=None,
        propagation_delay=None,
    )

    graph = generate_graph(
        interconnect,
        make_config(Topology.RING, 3),
    )

    for edge in graph.edges:
        assert edge.link.bandwidth is None
        assert edge.link.energy_per_bit is None
        assert edge.link.area is None
        assert edge.link.total_latency == 5.0
        assert edge.link.latency_components == []
        assert edge.link.known_latency is None


def test_optical_total_latency_includes_conversion():
    """Optical total latency should include both conversion components."""

    interconnect = make_interconnect(
        interconnect_type=InterconnectType.OPTICAL,
        total_latency=10.0,
        phy_latency=1.0,
        propagation_delay=2.0,
        eo_conversion_latency=3.0,
        oe_conversion_latency=4.0,
    )

    graph = generate_graph(
        interconnect,
        make_config(Topology.RING, 3),
    )

    for edge in graph.edges:
        assert edge.link.total_latency == 10.0
        assert len(edge.link.latency_components) == 4


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