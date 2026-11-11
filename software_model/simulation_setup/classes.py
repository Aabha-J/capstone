from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from ...data.data_classes import InterconnectType

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

    vertices: list[Vertex] = field(default_factory=list)
    edges: list[Edge] = field(default_factory=list)

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
    """Stores the packet events generated for an experiment."""

    events: list[PacketEvent] = field(default_factory=list)

    def add_event(self, event: PacketEvent) -> None:
        self.events.append(event)

@dataclass
class RoutingEntry:
    source: int
    destination: int
    path: list[int]


class RoutingTable:
    entries: list[RoutingEntry] = field(default_factory=list)

    def add_entry(self, entry: RoutingEntry) -> None:
        self.entries.append(entry)

    def get_route(self, source: int, destination: int) -> list[int] | None:
        for entry in self.entries:
            if entry.source == source and entry.destination == destination:
                return entry.path

        return None