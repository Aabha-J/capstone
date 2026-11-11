from itertools import combinations
from math import ceil, sqrt

from .classes import (
    Graph,
    Vertex,
    Edge,
    Link,
    LatencyComponent,
    LatencyType,
)

from ..data.data_classes import (
    Interconnect,
    InterconnectType,
    ExperimentConfig,
    Topology,
)

from ..data.formulas import calculate_total_latency


def create_link(interconnect: Interconnect) -> Link:
    """Copy processed interconnect properties into a graph Link."""

    latency_fields = [
        (LatencyType.PHY, "phy_latency"),
        (LatencyType.PROPAGATION, "propagation_delay"),
        (LatencyType.EO_CONVERSION, "eo_conversion_latency"),
        (LatencyType.OE_CONVERSION, "oe_conversion_latency"),
    ]

    latency_components = []

    for latency_type, attribute in latency_fields:
        value = getattr(interconnect, attribute, None)

        if value is not None:
            latency_components.append(
                LatencyComponent(
                    latency_type=latency_type,
                    value=value,
                )
            )

    return Link(
        interconnect_type=interconnect.interconnect_type,
        bandwidth=interconnect.bandwidth,
        energy_per_bit=interconnect.energy_per_bit,
        area=interconnect.area,
        total_latency=interconnect.total_latency,
        latency_components=latency_components,
    )


def generate_graph(
    interconnect: Interconnect,
    config: ExperimentConfig,
) -> Graph:
    """Generate a chiplet graph for the given experiment configuration."""

    graph = Graph()

    # Create vertices.
    vertices = [
        Vertex(chiplet_id=i)
        for i in range(config.chiplet_count)
    ]

    for vertex in vertices:
        graph.add_vertex(vertex)

    # Determine which chiplets should be connected.
    connections = []

    if config.topology == Topology.MESH:
        columns = ceil(sqrt(config.chiplet_count))

        for i in range(config.chiplet_count):
            row = i // columns
            column = i % columns

            # Connect to the right neighbour.
            right = i + 1
            if (
                column + 1 < columns
                and right < config.chiplet_count
            ):
                connections.append((i, right))

            # Connect to the neighbour below.
            below = i + columns
            if below < config.chiplet_count:
                connections.append((i, below))

    elif config.topology == Topology.RING:
        if config.chiplet_count > 1:
            connections = [
                (i, i + 1)
                for i in range(config.chiplet_count - 1)
            ]

            # Close the ring.
            if config.chiplet_count > 2:
                connections.append(
                    (config.chiplet_count - 1, 0)
                )

    elif config.topology == Topology.DIRECT:
        connections = list(
            combinations(range(config.chiplet_count), 2)
        )

    else:
        raise ValueError(
            f"Unsupported topology: {config.topology}"
        )

    # Create edges.
    for source_id, destination_id in connections:
        edge = Edge(
            source=vertices[source_id],
            destination=vertices[destination_id],
            distance=config.link_distance,
            link=create_link(interconnect),
        )

        graph.add_edge(edge)

    return graph