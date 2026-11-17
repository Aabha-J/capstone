
from dataclasses import dataclass, field
from typing import Optional

from software_model.data.enums import InterconnectType
from software_model.data.interconnect_components import TRANSMITTER_PARTS
from software_model.data.metrics import (
    AggregateMetric,
    Metric,
    calculate_aggregate_sum,
)


@dataclass
class Transmitter:
    interconnect_type: InterconnectType

    # Common TX / SERDES aggregates
    energy_per_bit: AggregateMetric = field(default_factory=AggregateMetric)  # pJ/bit
    latency: AggregateMetric = field(default_factory=AggregateMetric)  # ns
    power: AggregateMetric = field(default_factory=AggregateMetric)  # W
    area: AggregateMetric = field(default_factory=AggregateMetric)  # mm²

    # Individual component measurements for each agreagte
    components: dict[str, dict[str, Optional[Metric]]] = field(default_factory=dict)

    # Electrical TX parameters
    output_impedance: Optional[Metric] = None  # Ohms
    voltage_swing: Optional[Metric] = None  # V
    equalization: Optional[Metric] = None

    # Optical TX parameters
    modulator_insertion_loss: Optional[Metric] = None  # dB
    extinction_ratio: Optional[Metric] = None  # dB
    laser_efficiency: Optional[Metric] = None  # Fraction (0-1)

    def __post_init__(self):
        """Initialize component measurements from the source of truth."""
        parts = TRANSMITTER_PARTS[self.interconnect_type]

        self.components = {
            component: {
                aggregate: None
                for aggregate, components in parts.items()
                if component in components
            }
            for component in dict.fromkeys(
                component
                for components in parts.values()
                for component in components
            )
        }

    #needs to be called after creation
    def calculate_aggregates(self):
        """Calculate receiver aggregate measurements from its components."""

        parts = TRANSMITTER_PARTS[self.interconnect_type]

        for metric_name, aggregate in (
            ("energy_per_bit", self.energy_per_bit),
            ("latency", self.latency),
            ("power", self.power),
            ("area", self.area),
        ):
            calculate_aggregate_sum(
                aggregate=aggregate,
                parts=tuple(
                    self.components[component][metric_name]
                    for component in parts[metric_name]
                ),
                formula=" + ".join(parts[metric_name]),
            )
