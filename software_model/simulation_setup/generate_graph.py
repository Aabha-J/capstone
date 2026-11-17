from itertools import combinations
from math import ceil, sqrt

from software_model.simulation_setup.classes import (
    Edge,
    Graph,
    Vertex,
)
from software_model.data.enums import Topology
from software_model.data.experiment_classes import ExperimentConfig
from software_model.data.interconnect_classes.interconnect import Interconnect


def generate_graph(
    interconnect: Interconnect,
    config: ExperimentConfig,
) -> Graph:
    """Generate a chiplet graph for the given experiment configuration."""

    graph = Graph()

    # Create vertices representing the chiplets.
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

            # Close the ring when there are at least three chiplets.
            if config.chiplet_count > 2:
                connections.append(
                    (config.chiplet_count - 1, 0)
                )

    elif config.topology == Topology.DIRECT:
        # Connect every pair of chiplets.
        connections = list(
            combinations(range(config.chiplet_count), 2)
        )

    else:
        raise ValueError(
            f"Unsupported topology: {config.topology}"
        )

    # Create edges using the original Interconnect object.
    for source_id, destination_id in connections:
        edge = Edge(
            source=vertices[source_id],
            destination=vertices[destination_id],
            distance=config.link_distance,
            interconnect=interconnect,
        )

        graph.add_edge(edge)

    return graph