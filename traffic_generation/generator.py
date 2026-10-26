from __future__ import annotations

import random
from dataclasses import dataclass
from math import isfinite
from numbers import Real
from typing import Iterator, Sequence

from ..network import Chiplet, Packet


@dataclass(frozen=True)
class TrafficMatrix:
    """A reusable packet-count matrix for a fixed set of chiplets.

    Matrix rows are sources and columns are destinations. Each nonzero cell
    creates that many equal-sized packets when the matrix is iterated.
    ``simulation_time`` is measured in ns, so offered_packet_rate is packets/ns.
    """

    chiplets: tuple[Chiplet, ...]
    packet_counts: tuple[tuple[int, ...], ...]
    packet_size_bits: int
    simulation_time: Real

    def __post_init__(self) -> None:
        size = len(self.chiplets)
        if len(set(self.chiplets)) != size:
            raise ValueError("Traffic matrix chiplets must be unique.")
        if len(self.packet_counts) != size or any(len(row) != size for row in self.packet_counts):
            raise ValueError("Traffic matrix must be square with one row and column per chiplet.")
        if isinstance(self.packet_size_bits, bool) or not isinstance(self.packet_size_bits, int):
            raise TypeError("packet_size_bits must be an integer.")
        if self.packet_size_bits <= 0:
            raise ValueError("packet_size_bits must be greater than zero.")
        if (
            isinstance(self.simulation_time, bool)
            or not isinstance(self.simulation_time, Real)
            or not isfinite(self.simulation_time)
            or self.simulation_time <= 0
        ):
            raise ValueError("simulation_time must be a finite positive number.")
        for source_index, row in enumerate(self.packet_counts):
            for destination_index, packet_count in enumerate(row):
                if isinstance(packet_count, bool) or not isinstance(packet_count, int):
                    raise TypeError("Traffic matrix entries must be integer packet counts.")
                if packet_count < 0:
                    raise ValueError("Traffic matrix entries cannot be negative.")
                if source_index == destination_index and packet_count:
                    raise ValueError("Self-traffic is not supported.")

    @property
    def total_packets(self) -> int:
        return sum(sum(row) for row in self.packet_counts)

    @property
    def offered_packet_rate(self) -> float:
        """Total generated packet count divided by the configured duration."""
        return self.total_packets / float(self.simulation_time)

    def packets(self) -> Iterator[Packet]:
        """Yield the same deterministic packet workload on every iteration."""
        for source_index, source in enumerate(self.chiplets):
            for destination_index, destination in enumerate(self.chiplets):
                for _ in range(self.packet_counts[source_index][destination_index]):
                    yield Packet(source, destination, self.packet_size_bits)

    def __iter__(self) -> Iterator[Packet]:
        return self.packets()

    def __getitem__(self, pair: tuple[Chiplet, Chiplet]) -> int:
        source, destination = pair
        try:
            source_index = self.chiplets.index(source)
            destination_index = self.chiplets.index(destination)
        except ValueError:
            raise KeyError("Both chiplets must be part of this traffic matrix.") from None
        return self.packet_counts[source_index][destination_index]


class RandomTrafficMatrixGenerator:
    """Generate reproducible uniform-random traffic across directed chiplet pairs."""

    @staticmethod
    def generate(
        chiplets: Sequence[Chiplet],
        total_packets: int,
        packet_size_bits: int,
        simulation_time: Real,
        seed: int | None = None,
    ) -> TrafficMatrix:
        """Randomly assign a fixed packet budget to non-self chiplet pairs.

        Pass a seed to reproduce exactly the same matrix for comparisons between
        different interconnect topologies.
        """
        chiplet_tuple = tuple(chiplets)
        if isinstance(total_packets, bool) or not isinstance(total_packets, int):
            raise TypeError("total_packets must be an integer.")
        if total_packets < 0:
            raise ValueError("total_packets cannot be negative.")
        if len(set(chiplet_tuple)) != len(chiplet_tuple):
            raise ValueError("Chiplets must be unique.")

        pairs = [
            (source_index, destination_index)
            for source_index in range(len(chiplet_tuple))
            for destination_index in range(len(chiplet_tuple))
            if source_index != destination_index
        ]
        if total_packets and not pairs:
            raise ValueError("At least two chiplets are required to generate non-self traffic.")

        counts = [[0 for _ in chiplet_tuple] for _ in chiplet_tuple]
        generator = random.Random(seed)
        for _ in range(total_packets):
            source_index, destination_index = generator.choice(pairs)
            counts[source_index][destination_index] += 1

        return TrafficMatrix(
            chiplets=chiplet_tuple,
            packet_counts=tuple(tuple(row) for row in counts),
            packet_size_bits=packet_size_bits,
            simulation_time=simulation_time,
        )
