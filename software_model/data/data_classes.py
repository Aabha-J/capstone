
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
from software_model.data.metrics import AggregateMetric, Metric

class InterconnectType(Enum):
    OPTICAL = "optical"
    ELECTRICAL = "electrical"

class Topology(Enum):
    MESH = "Mesh"
    RING = "Ring"
    DIRECT = "Direct"


class TrafficPattern(Enum):
    UNIFORM = "uniform"
    RANDOM = "random"
    HOTSPOT = "hotspot"

@dataclass
class Transmitter:

    # Common TX / SERDES aggregates
    energy_per_bit: AggregateMetric = field(default_factory=AggregateMetric)  # pJ/bit
    latency: AggregateMetric = field(default_factory=AggregateMetric)  # ns
    power: AggregateMetric = field(default_factory=AggregateMetric)  # W
    area: AggregateMetric = field(default_factory=AggregateMetric)  # mm²

    # Electrical TX parameters
    output_impedance: Optional[Metric] = None  # Ohms
    voltage_swing: Optional[Metric] = None  # V
    equalization: Optional[Metric] = None

    # Optical TX parameters
    modulator_energy_per_bit: Optional[Metric] = None  # pJ/bit
    modulator_insertion_loss: Optional[Metric] = None  # dB
    extinction_ratio: Optional[Metric] = None  # dB
    laser_power: Optional[Metric] = None  # W: electrical laser input power
    laser_efficiency: Optional[Metric] = None  # Fraction (0-1)
    eo_conversion_latency: Optional[Metric] = None  # ns


@dataclass
class Receiver:

    # Common RX / SERDES aggregates
    energy_per_bit: AggregateMetric = field(default_factory=AggregateMetric)  # pJ/bit
    latency: AggregateMetric = field(default_factory=AggregateMetric)  # ns
    power: AggregateMetric = field(default_factory=AggregateMetric)  # W
    area: AggregateMetric = field(default_factory=AggregateMetric)  # mm²

    # Electrical RX parameters
    input_impedance: Optional[Metric] = None  # Ohms
    equalization: Optional[Metric] = None

    # Optical RX parameters
    responsivity: Optional[Metric] = None  # A/W
    sensitivity: Optional[Metric] = None  # dBm
    input_capacitance: Optional[Metric] = None  # pF
    oe_conversion_latency: Optional[Metric] = None  # ns

    # Reliability
    target_ber: Optional[Metric] = None  # BER (unitless probability)


@dataclass
class Channel:

    link_length: Optional[Metric] = None  # mm
    reach: Optional[Metric] = None  # mm
    propagation_delay: Optional[Metric] = None  # ns
    area: Optional[Metric] = None  # mm²

    # Optical channel parameters
    propagation_loss: Optional[Metric] = None  # dB
    coupling_loss: Optional[Metric] = None  # dB

    # Electrical channel parameters
    insertion_loss: Optional[Metric] = None  # dB
    characteristic_impedance: Optional[Metric] = None  # Ohms
    crosstalk: Optional[Metric] = None  # Source-defined unit


@dataclass
class Interconnect:

    # Identification
    interconnect_id: str
    interconnect_type: InterconnectType

    # Signaling format
    modulation_format: Optional[str] = None  # NRZ, PAM4, PAM8
    bits_per_symbol: Optional[int] = None

    # Signaling rate
    symbol_rate: Optional[Metric] = None  # GBaud
    data_rate_per_lane: Optional[Metric] = None  # Gbps
    bandwidth: Optional[Metric] = None  # GB/s

    # Electrical configuration
    lane_width: Optional[int] = None

    # Optical configuration
    channel_count: Optional[int] = None
    wavelength_count: Optional[int] = None

    # Aggregate energy, power, and area
    energy_per_bit: AggregateMetric = field(default_factory=AggregateMetric)  # pJ/bit
    power: AggregateMetric = field(default_factory=AggregateMetric)  # W
    area: AggregateMetric = field(default_factory=AggregateMetric)  # mm²

    # Aggregate latency
    phy_latency: AggregateMetric = field(default_factory=AggregateMetric)  # ns
    total_latency: AggregateMetric = field(default_factory=AggregateMetric)  # ns

    # Component parameters
    transmitter: Optional[Transmitter] = None
    channel: Optional[Channel] = None
    receiver: Optional[Receiver] = None

    # Metadata
    source: Optional[str] = None
    notes: Optional[str] = None

@dataclass
class ExperimentOptions:
    """Options used to generate simulation configurations."""

    chiplet_counts: list[int]
    topologies: list[Topology]
    link_distances: list[float]

    traffic_patterns: list[TrafficPattern]
    packet_sizes: list[int]
    injection_rates: list[float]
    hotspot_counts: list[int]
    hotspot_probabilities: list[float]

    durations: list[float]
    seeds: list[int]


@dataclass
class ExperimentConfig:
    """One fully specified simulation configuration."""

    config_id: str

    # Simulation settings
    chiplet_count: int
    topology: Topology
    link_distance: float

    # Traffic properties
    traffic_pattern: TrafficPattern
    packet_size: int
    injection_rate: float

    # Execution settings
    duration: float
    seed: int

    #Optional hotspot parameters
    hotspot_count: Optional[int] = None
    hotspot_probability: Optional[float] = None
