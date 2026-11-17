from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from software_model.data.enums import InterconnectType
class LatencyType(Enum):
    PHY = "phy_latency"
    PROPAGATION = "propagation_delay"
    EO_CONVERSION = "eo_conversion_latency"
    OE_CONVERSION = "oe_conversion_latency"

@dataclass
class LatencyComponent:
    """Represents an individual latency component."""

    latency_type: LatencyType
    value: float  # ns


@dataclass
class Vertex:
    """Represents a chiplet in the graph."""
    chiplet_id: int

@dataclass
class Link:
    """Represents the interconnect properties of a link."""
    interconnect_type: InterconnectType
    bandwidth: Optional[float] = None       # GB/s
    energy_per_bit: Optional[float] = None  # pJ/bit
    area: Optional[float] = None            # mm^2

    total_latency: Optional[float] = None
    latency_components: list[LatencyComponent] = field(default_factory=list)

    @property
    def known_latency(self) -> Optional[float]:
        """Sum of only recorded latency components."""

        if not self.latency_components:
            return None

        return sum(component.value for component in self.latency_components)

 

@dataclass
class Edge:
    """Represents a connection between two chiplets."""

    source: Vertex
    destination: Vertex
    distance: float           # mm
    link: Link


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