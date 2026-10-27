from __future__ import annotations

from dataclasses import dataclass
from heapq import heappop, heappush
from itertools import count
from math import ceil, isfinite, sqrt
from numbers import Real
from typing import Iterable

from .classes import Calculation, ElectricalInterconnect, Interconnect, OpticalInterconnect, Parameter
from .formulas import (
    average_latency_ps,
    average_packet_error_probability,
    end_to_end_error_probability,
    packet_energy_pj,
    packet_error_probability,
    serialization_latency_ps,
    total_energy_pj,
)

MetricValue = Real | Calculation
TopologyName = str


def topology_pairs(
    chiplets: Iterable[Chiplet], topology: TopologyName
) -> tuple[tuple[Chiplet, Chiplet], ...]:
    """Return links for a reusable topology preset.

    Supported presets are ``ring``, ``mesh`` (2D row-major), ``star``,
    ``line``, and ``fully_connected``.
    """
    nodes = tuple(chiplets)
    if len(set(nodes)) != len(nodes):
        raise ValueError("Chiplets must be unique.")
    if topology not in {"ring", "mesh", "star", "line", "fully_connected"}:
        raise ValueError(f"Unknown topology preset: {topology!r}.")

    pairs: set[tuple[int, int]] = set()
    if topology == "fully_connected":
        pairs = {(i, j) for i in range(len(nodes)) for j in range(i + 1, len(nodes))}
    elif topology == "star":
        pairs = {(0, i) for i in range(1, len(nodes))}
    elif topology == "line":
        pairs = {(i, i + 1) for i in range(len(nodes) - 1)}
    elif topology == "ring" and len(nodes) > 1:
        pairs = {
            (min(i, (i + 1) % len(nodes)), max(i, (i + 1) % len(nodes)))
            for i in range(len(nodes))
        }
    elif topology == "mesh":
        columns = ceil(sqrt(len(nodes))) if nodes else 0
        for i in range(len(nodes)):
            if columns and i % columns < columns - 1 and i + 1 < len(nodes):
                pairs.add((i, i + 1))
            if i + columns < len(nodes):
                pairs.add((i, i + columns))

    return tuple((nodes[i], nodes[j]) for i, j in sorted(pairs))


@dataclass(frozen=True)
class Chiplet:
    """A graph vertex representing a chiplet."""

    name: str

    def __post_init__(self) -> None:
        if not self.name or not self.name.strip():
            raise ValueError("A chiplet name is required.")


@dataclass(frozen=True)
class Packet:
    """A packet to route between chiplets. Size is measured in bits."""

    source: Chiplet
    destination: Chiplet
    size_bits: int

    def __post_init__(self) -> None:
        if isinstance(self.size_bits, bool) or not isinstance(self.size_bits, int):
            raise TypeError("Packet size_bits must be an integer.")
        if self.size_bits <= 0:
            raise ValueError("Packet size_bits must be greater than zero.")


@dataclass(frozen=True)
class PacketResult:
    """Measured metrics for one packet traversing the network."""

    packet: Packet
    path: tuple[Chiplet, ...]
    latency: MetricValue
    energy: MetricValue
    error_probability: MetricValue


@dataclass(frozen=True)
class SimulationResult:
    """Results for a batch of independently routed packets."""

    packets: tuple[PacketResult, ...]

    @property
    def total_energy(self) -> MetricValue:
        return total_energy_pj(result.energy for result in self.packets)

    @property
    def average_latency(self) -> MetricValue:
        return average_latency_ps(result.latency for result in self.packets)

    @property
    def average_error_probability(self) -> MetricValue:
        return average_packet_error_probability(
            result.error_probability for result in self.packets
        )


@dataclass(frozen=True)
class _Link:
    destination: Chiplet
    interconnect: Interconnect
    distance: Real | None


class InterconnectGraph:
    """Undirected chiplet graph that routes packets over electrical/optical links.

    Packets are routed independently; this model does not simulate queuing or
    contention. Bandwidth and latency must use consistent time units. If a
    metric is unknown, results retain it as a symbolic Calculation. Latency
    is measured in ps, effective bandwidth in Gbit/s, energy in pJ/bit, and
    link distances/reach in mm. Electrical data_rate is in Gtransfer/s and its
    aggregate rate is data_rate * lane_width * lane_count. Optical data_rate
    is in Gbit/s per wavelength and its aggregate rate is
    data_rate * wavelength_count * channel_count, with wavelength_count per
    fiber and channel_count as physical fibers or waveguides. Effective
    bandwidth is the minimum of this aggregate rate and bandwidth_density
    times area_footprint. A link is excluded when its known distance exceeds
    the interconnect's known reach.
    """

    def __init__(self) -> None:
        self._links: dict[Chiplet, list[_Link]] = {}

    @classmethod
    def from_topology(
        cls,
        chiplets: Iterable[Chiplet],
        interconnect: Interconnect,
        topology: TopologyName,
        distance_mm: Real = 1,
    ) -> InterconnectGraph:
        """Build a graph from a common preset; all link distances are in mm."""
        nodes = tuple(chiplets)
        graph = cls()
        for chiplet in nodes:
            graph.add_chiplet(chiplet)
        for first, second in topology_pairs(nodes, topology):
            graph.add_interconnect(first, second, interconnect, distance=distance_mm)
        return graph

    @property
    def chiplets(self) -> tuple[Chiplet, ...]:
        return tuple(self._links)

    def add_chiplet(self, chiplet: Chiplet) -> None:
        if not isinstance(chiplet, Chiplet):
            raise TypeError("Graph vertices must be Chiplet instances.")
        if chiplet in self._links:
            raise ValueError(f"Chiplet {chiplet.name!r} is already in the graph.")
        self._links[chiplet] = []

    def add_interconnect(
        self,
        first: Chiplet,
        second: Chiplet,
        interconnect: Interconnect,
        distance: Real | None = None,
    ) -> None:
        """Add a bidirectional link with an optional physical distance in mm."""
        if first == second:
            raise ValueError("An interconnect must connect two different chiplets.")
        if first not in self._links or second not in self._links:
            raise ValueError("Both chiplets must be added to the graph before linking.")
        if not isinstance(interconnect, (ElectricalInterconnect, OpticalInterconnect)):
            raise TypeError("Interconnects must be electrical or optical.")
        if distance is not None and (
            isinstance(distance, bool)
            or not isinstance(distance, Real)
            or not isfinite(distance)
            or distance < 0
        ):
            raise ValueError("Link distance must be a finite non-negative number or None.")
        if any(link.destination == second for link in self._links[first]):
            raise ValueError(f"An interconnect already connects {first.name!r} and {second.name!r}.")
        self._links[first].append(_Link(second, interconnect, distance))
        self._links[second].append(_Link(first, interconnect, distance))

    def simulate_packet(self, packet: Packet) -> PacketResult:
        """Route one packet over the lowest-latency path and measure its metrics."""
        if not isinstance(packet, Packet):
            raise TypeError("simulate_packet expects a Packet.")
        if packet.source not in self._links or packet.destination not in self._links:
            raise ValueError("The packet source and destination must be in the graph.")

        path = self._shortest_path(packet.source, packet.destination, packet.size_bits)
        latency: Real | Calculation = 0.0
        energy: Real | Calculation = 0.0
        hop_error_probabilities: list[Real | Calculation] = []
        for source, destination in zip(path, path[1:]):
            link = self._find_link(source, destination)
            interconnect = link.interconnect
            hop_latency = self._validated_parameter(
                interconnect.latency, "latency", source, destination, minimum=0
            )
            bandwidth = self._effective_bandwidth(interconnect, source, destination)
            latency += hop_latency + serialization_latency_ps(packet.size_bits, bandwidth)

            energy_per_bit = self._validated_parameter(
                interconnect.energy_per_bit, "energy_per_bit", source, destination, minimum=0
            )
            ber = self._validated_parameter(
                interconnect.ber, "ber", source, destination, minimum=0, maximum=1
            )
            if isinstance(interconnect, OpticalInterconnect):
                latency += self._validated_parameter(
                    interconnect.electrical_to_optical_conversion_latency,
                    "electrical_to_optical_conversion_latency",
                    source,
                    destination,
                    minimum=0,
                )
                latency += self._validated_parameter(
                    interconnect.optical_to_electrical_conversion_latency,
                    "optical_to_electrical_conversion_latency",
                    source,
                    destination,
                    minimum=0,
                )
                energy_per_bit += self._validated_parameter(
                    interconnect.electrical_to_optical_conversion_energy,
                    "electrical_to_optical_conversion_energy",
                    source,
                    destination,
                    minimum=0,
                )
                energy_per_bit += self._validated_parameter(
                    interconnect.optical_to_electrical_conversion_energy,
                    "optical_to_electrical_conversion_energy",
                    source,
                    destination,
                    minimum=0,
                )
            energy += packet_energy_pj(packet.size_bits, energy_per_bit)
            hop_error_probabilities.append(packet_error_probability(packet.size_bits, ber))

        return PacketResult(
            packet=packet,
            path=path,
            latency=latency,
            energy=energy,
            error_probability=end_to_end_error_probability(hop_error_probabilities),
        )

    def simulate(self, packets: Iterable[Packet]) -> SimulationResult:
        """Simulate a batch of packets independently and return aggregate metrics."""
        return SimulationResult(tuple(self.simulate_packet(packet) for packet in packets))

    def _shortest_path(
        self, source: Chiplet, destination: Chiplet, size_bits: int
    ) -> tuple[Chiplet, ...]:
        if source == destination:
            return (source,)

        distances = {source: 0.0}
        previous: dict[Chiplet, Chiplet] = {}
        sequence = count()
        queue: list[tuple[float, int, Chiplet]] = [(0.0, next(sequence), source)]

        while queue:
            distance, _, current = heappop(queue)
            if distance != distances.get(current):
                continue
            if current == destination:
                break
            for link in self._links[current]:
                if not self._within_reach(current, link):
                    continue
                edge_latency = self._routing_latency(current, link, size_bits)
                candidate = distance + edge_latency
                if candidate < distances.get(link.destination, float("inf")):
                    distances[link.destination] = candidate
                    previous[link.destination] = current
                    heappush(queue, (candidate, next(sequence), link.destination))

        if destination not in previous:
            raise ValueError(f"No path exists from {source.name!r} to {destination.name!r}.")

        path = [destination]
        while path[-1] != source:
            path.append(previous[path[-1]])
        path.reverse()
        return tuple(path)

    def _routing_latency(self, source: Chiplet, link: _Link, size_bits: int) -> float:
        interconnect = link.interconnect
        latency = self._known_nonnegative(
            interconnect.latency, "latency", source, link.destination
        ) or 0.0
        bandwidth = self._effective_bandwidth(interconnect, source, link.destination)
        numeric_bandwidth = bandwidth.value if isinstance(bandwidth, Calculation) else bandwidth
        if numeric_bandwidth is not None:
            if numeric_bandwidth <= 0:
                raise ValueError(
                    f"Effective bandwidth must be positive on link "
                    f"{source.name!r} -> {link.destination.name!r}."
                )
            latency += serialization_latency_ps(size_bits, numeric_bandwidth)
        if isinstance(interconnect, OpticalInterconnect):
            latency += self._known_nonnegative(
                interconnect.electrical_to_optical_conversion_latency,
                "electrical_to_optical_conversion_latency",
                source,
                link.destination,
            ) or 0.0
            latency += self._known_nonnegative(
                interconnect.optical_to_electrical_conversion_latency,
                "optical_to_electrical_conversion_latency",
                source,
                link.destination,
            ) or 0.0
        return latency

    def _within_reach(self, source: Chiplet, link: _Link) -> bool:
        reach = link.interconnect.reach.value
        if isinstance(reach, Real) and link.distance is not None:
            self._validated_parameter(
                link.interconnect.reach,
                "reach",
                source,
                link.destination,
                minimum=0,
            )
            return link.distance <= reach
        return True

    @classmethod
    def _effective_bandwidth(
        cls, interconnect: Interconnect, source: Chiplet, destination: Chiplet
    ) -> Real | Calculation:
        data_rate = cls._validated_parameter(
            interconnect.data_rate, "data_rate", source, destination, minimum=0
        )
        if isinstance(interconnect, ElectricalInterconnect):
            cls._validated_parameter(
                interconnect.lane_count,
                "lane_count",
                source,
                destination,
                minimum=1,
                integer=True,
            )
            cls._validated_parameter(
                interconnect.lane_width,
                "lane_width",
                source,
                destination,
                minimum=1,
                integer=True,
            )
        else:
            cls._validated_parameter(
                interconnect.channel_count,
                "channel_count",
                source,
                destination,
                minimum=1,
                integer=True,
            )
            cls._validated_parameter(
                interconnect.wavelength_count,
                "wavelength_count",
                source,
                destination,
                minimum=1,
                integer=True,
            )
        cls._validated_parameter(
            interconnect.bandwidth_density,
            "bandwidth_density",
            source,
            destination,
            minimum=0,
        )
        cls._validated_parameter(
            interconnect.area_footprint, "area_footprint", source, destination, minimum=0
        )
        return interconnect.effective_bandwidth

    def _find_link(self, source: Chiplet, destination: Chiplet) -> _Link:
        for link in self._links[source]:
            if link.destination == destination:
                return link
        raise RuntimeError("The routed path contains a missing interconnect.")

    @staticmethod
    def _validated_parameter(
        parameter: Parameter,
        name: str,
        source: Chiplet,
        destination: Chiplet,
        minimum: float | None = None,
        maximum: float | None = None,
        strict_minimum: bool = False,
        integer: bool = False,
    ) -> Parameter:
        value = parameter.value
        if value is None:
            return parameter
        if isinstance(value, bool) or not isinstance(value, Real) or not isfinite(value):
            raise ValueError(
                f"Parameter {name!r} must be finite on link {source.name!r} -> {destination.name!r}."
            )
        if integer and isinstance(value, Real) and int(value) != value:
            raise ValueError(
                f"Parameter {name!r} must be an integer on link {source.name!r} -> {destination.name!r}."
            )
        if minimum is not None and (value <= minimum if strict_minimum else value < minimum):
            raise ValueError(
                f"Parameter {name!r} must be {'greater than' if strict_minimum else 'at least'} "
                f"{minimum} on link {source.name!r} -> {destination.name!r}."
            )
        if maximum is not None and value > maximum:
            raise ValueError(
                f"Parameter {name!r} must be at most {maximum} on link "
                f"{source.name!r} -> {destination.name!r}."
            )
        return parameter

    @classmethod
    def _known_nonnegative(
        cls,
        parameter: Parameter,
        name: str,
        source: Chiplet,
        destination: Chiplet,
        strict_positive: bool = False,
    ) -> float | None:
        cls._validated_parameter(
            parameter,
            name,
            source,
            destination,
            minimum=0,
            strict_minimum=strict_positive,
        )
        if parameter.value is None:
            return None
        return float(parameter.value)
