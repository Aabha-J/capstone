
from dataclasses import dataclass
from typing import Optional

from software_model.data.enums import Topology, TrafficPattern

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
