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
class Link:
    """Represents the interconnect properties of a link."""

    interconnect_type: InterconnectType

    bandwidth: Optional[float] = None       # GB/s
    energy_per_bit: Optional[float] = None  # pJ/bit
    area: Optional[float] = None            # mm^2

    reported_total_latency: Optional[float] = None  # ns

    latency_components: list[LatencyComponent] = field(default_factory=list)

    @property
    def known_latency(self) -> Optional[float]:
        if not self.latency_components:
            return None

        return sum(component.value for component in self.latency_components)

    @property
    def calculated_total_latency(self) -> Optional[float]:
        required = {
            LatencyType.PHY,
            LatencyType.PROPAGATION
        }

        if self.interconnect_type == InterconnectType.OPTICAL:
            required.update({
                LatencyType.EO_CONVERSION,
                LatencyType.OE_CONVERSION
            })

        available = {
            component.latency_type
            for component in self.latency_components
        }

        if not required.issubset(available):
            return None

        return sum(
            component.value
            for component in self.latency_components
            if component.latency_type in required
        )

    @property
    def total_latency(self) -> Optional[float]:
        if self.reported_total_latency is not None:
            #if  reported latency is available, use it
            return self.reported_total_latency

        return self.calculated_total_latency

@dataclass
class Vertex:
    """Represents a chiplet in the graph."""
    chiplet_id: int


from dataclasses import dataclass, field
from typing import Optional


@dataclass
class LatencyComponent:
    """Stores a latency value and where it came from."""

    name: str #type of latency component (e.g., phy_latency, propagation_delay, etc.)
    value: float


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


@dataclass
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


@dataclass
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


@dataclass
class RoutingTable:
    entries: list[RoutingEntry] = field(default_factory=list)

    def add_entry(self, entry: RoutingEntry) -> None:
        self.entries.append(entry)

    def get_route(self, source: int, destination: int) -> list[int] | None:
        for entry in self.entries:
            if entry.source == source and entry.destination == destination:
                return entry.path

        return None