from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from software_model.data.enums import InterconnectType
from software_model.data.interconnect_classes.interconnect import Interconnect

@dataclass
class Vertex:
    """Represents a chiplet in the graph."""
    chiplet_id: int

@dataclass
class Edge:
    """Represents an interconnect connection between two chiplets."""

    source: Vertex
    destination: Vertex
    distance: float  # mm
    interconnect: Interconnect


class Graph:
    """Represents a chiplet interconnect graph."""

    def __init__(self):
        self.vertices: list[Vertex] = []
        self.edges: list[Edge] = []

    def add_vertex(self, vertex: Vertex) -> None:
        self.vertices.append(vertex)

    def add_edge(self, edge: Edge) -> None:
        self.edges.append(edge)

@dataclass
class PacketEvent:
    """Represents a packet generated during an experiment."""

    generation_time: float  # cycles
    source: int             # Source chiplet ID
    destination: int        # Destination chiplet ID
    packet_size: int        # bytes


class TrafficTrace:
    def __init__(self):
        self.events: list[PacketEvent] = []

    def add_event(self, event: PacketEvent) -> None:
        self.events.append(event)

@dataclass
class RoutingEntry:
    source: int
    destination: int
    path: list[int]


class RoutingTable:
    def __init__(self):
        self.entries: list[RoutingEntry] = []

    def add_entry(self, entry: RoutingEntry) -> None:
        self.entries.append(entry)

    def get_route(self, source: int, destination: int) -> list[int] | None:
        for entry in self.entries:
            if entry.source == source and entry.destination == destination:
                return entry.path

        return None