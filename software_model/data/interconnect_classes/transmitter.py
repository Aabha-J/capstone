from dataclasses import dataclass, field
from typing import Optional

from software_model.data.enums import InterconnectType
from software_model.data.interconnect_components import TRANSMITTER_PARTS
from software_model.data.metrics import AggregateMetric, Metric


@dataclass
class Transmitter:
    interconnect_type: InterconnectType

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
    modulator_insertion_loss: Optional[Metric] = None  # dB
    extinction_ratio: Optional[Metric] = None  # dB
    laser_efficiency: Optional[Metric] = None  # Fraction (0-1)

    def __post_init__(self):
        """Initialize component measurements for each aggregate."""
        parts = TRANSMITTER_PARTS[self.interconnect_type]

        for aggregate_name, component_names in parts.items():
            aggregate = getattr(self, aggregate_name)
            aggregate.components = {
                component: None
                for component in component_names
            }