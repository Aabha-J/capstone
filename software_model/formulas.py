"""Central place for the simulator's updateable model equations.

Per packet, the simulator evaluates each traversed edge in this order:

1. Exclude the edge if known ``distance_mm > reach_mm``.
2. Compute effective edge bandwidth:
   ``min(aggregate_rate, bandwidth_density * area_footprint)``.
   Electrical aggregate rate is ``data_rate * lane_width * lane_count``,
   where data_rate is in Gtransfer/s and lane_width is bits per transfer per
   lane. Optical aggregate rate is
   ``data_rate * wavelength_count * channel_count``, where data_rate is
   Gbit/s per wavelength, wavelength_count is the number of wavelengths
   carried per fiber, and channel_count is the number of physical fibers or
   waveguides.
3. Add edge latency: ``base_latency_ps + 1000 * packet_bits / bandwidth_gbps``.
   Optical edges additionally add both conversion latencies.
4. Add edge energy: ``packet_bits * edge_energy_per_bit``. Optical edges add
   both conversion energies to ``edge_energy_per_bit`` before multiplying.
5. Compute edge packet error: ``1 - (1 - BER) ** packet_bits``.

Per-packet outputs are the sums of edge latency and energy, and the independent
hop-error combination ``1 - product(1 - edge_packet_error)``. Batch outputs
are the arithmetic mean packet latency, the sum of packet energy, the
arithmetic mean packet error probability, and generated packets divided by
simulation duration.

When changing an assumption, edit the corresponding function here first,
update the focused checks, and keep this flow, README, and UI units in sync.
"""

from __future__ import annotations

from numbers import Real
from typing import Iterable

from .classes import Calculation, Parameter


MetricInput = Real | Parameter | Calculation
MetricResult = Real | Calculation

# With rates in Gbit/s and packet sizes in bits:
# bits / (Gbit/s) = nanoseconds. Multiply by 1000 for picoseconds.
PS_PER_NS = 1000


def effective_bandwidth(
    *,
    data_rate: MetricInput,
    bandwidth_density: MetricInput,
    area_footprint: MetricInput,
    optical: bool,
    lane_count: MetricInput | None = None,
    lane_width: MetricInput | None = None,
    wavelength_count: MetricInput | None = None,
    channel_count: MetricInput | None = None,
) -> MetricResult:
    """Return effective edge capacity in Gbit/s, preserving unknowns.

    Electrical ``data_rate`` is in Gtransfer/s and aggregate rate is
    ``data_rate * lane_width * lane_count``. Optical ``data_rate`` is in
    Gbit/s per wavelength. Optical aggregate rate is
    ``data_rate * wavelength_count * channel_count``, where wavelength_count
    is wavelengths per fiber and channel_count is the count of physical
    fibers/waveguides. The area limit is
    ``bandwidth_density * area_footprint``. The edge capacity is the smaller
    limit. Unknown terms remain in a symbolic ``min(...)`` expression
    instead of being treated as zero.
    """
    if optical:
        if wavelength_count is None or channel_count is None:
            raise ValueError("Optical bandwidth needs wavelength_count and channel_count.")
        aggregate_rate = data_rate * wavelength_count * channel_count
    else:
        if lane_count is None or lane_width is None:
            raise ValueError("Electrical bandwidth needs lane_count and lane_width.")
        aggregate_rate = data_rate * lane_width * lane_count

    area_limited_rate = bandwidth_density * area_footprint
    if isinstance(aggregate_rate, Real) and isinstance(area_limited_rate, Real):
        return min(aggregate_rate, area_limited_rate)
    return Calculation("min", aggregate_rate, area_limited_rate)


def serialization_latency_ps(packet_size_bits: int, bandwidth_gbps: MetricInput) -> MetricResult:
    """Calculate edge serialization latency: ``1000 * bits / Gbit/s`` in ps."""
    return PS_PER_NS * packet_size_bits / bandwidth_gbps


def packet_energy_pj(packet_size_bits: int, energy_per_bit_pj: MetricInput) -> MetricResult:
    """Calculate per-edge packet energy: ``bits * pJ/bit`` in pJ."""
    return packet_size_bits * energy_per_bit_pj


def packet_error_probability(packet_size_bits: int, ber: MetricInput) -> MetricResult:
    """Calculate per-edge packet error: ``1 - (1 - BER) ** bits``."""
    return 1 - (1 - ber) ** packet_size_bits


def end_to_end_error_probability(
    hop_error_probabilities: list[MetricInput],
) -> MetricResult:
    """Combine edge packet errors as ``1 - product(1 - edge_error)``."""
    if not hop_error_probabilities:
        return 0.0
    success_probability: MetricResult = 1.0
    for hop_error in hop_error_probabilities:
        success_probability *= 1 - hop_error
    return 1 - success_probability


def average_latency_ps(packet_latencies: Iterable[MetricInput]) -> MetricResult:
    """Final output: arithmetic mean of routed packet latencies in ps."""
    values = tuple(packet_latencies)
    if not values:
        return 0.0
    return sum(values, 0.0) / len(values)


def total_energy_pj(packet_energies: Iterable[MetricInput]) -> MetricResult:
    """Final output: sum packet energies in pJ across this simulation."""
    return sum(packet_energies, 0.0)


def average_packet_error_probability(
    packet_error_probabilities: Iterable[MetricInput],
) -> MetricResult:
    """Final output: arithmetic mean of per-packet error probabilities."""
    values = tuple(packet_error_probabilities)
    if not values:
        return 0.0
    return sum(values, 0.0) / len(values)


def offered_packet_rate(total_packets: int, simulation_time_ns: Real) -> Real:
    """Final output: generated packets divided by configured duration in ns."""
    if simulation_time_ns <= 0:
        raise ValueError("simulation_time_ns must be greater than zero.")
    return total_packets / simulation_time_ns
