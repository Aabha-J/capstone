
from dataclasses import dataclass
from enum import Enum
from typing import Optional


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
class Interconnect:

    # Identification
    interconnect_id: str
    interconnect_type: InterconnectType

    # General parameters
    data_rate_per_lane: Optional[float] = None
    bandwidth: Optional[float] = None
    energy_per_bit: Optional[float] = None
    reach: Optional[float] = None
    area: Optional[float] = None

    total_latency: Optional[float] = None

    #Latency
    phy_latency: Optional[float] = None
    propagation_delay: Optional[float] = None



    # Electrical parameters
    lane_width: Optional[int] = None

    # Optical parameters
    channel_count: Optional[int] = None
    wavelength_count: Optional[int] = None

    #Latency (optical only)
    oe_conversion_latency: Optional[int] = None
    eo_conversion_latency: Optional[int] = None


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
    topology: str
    link_distance: float

    # Traffic properties
    traffic_pattern: str
    packet_size: int
    injection_rate: float
    hotspot_count: Optional[int]
    hotspot_probability: Optional[float]

    # Execution settings
    duration: float
    seed: int
