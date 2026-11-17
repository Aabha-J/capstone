
from dataclasses import dataclass, field

from software_model.data.enums import InterconnectType
from software_model.data.interconnect_components import RECEIVER_PARTS
from software_model.data.metrics import (
    AggregateMetric,
    Metric,
    calculate_aggregate_sum,
)


@dataclass
class Receiver:
    interconnect_type: InterconnectType

    # Receiver aggregate measurements
    energy_per_bit: AggregateMetric = field(default_factory=AggregateMetric)  # pJ/bit
    latency: AggregateMetric = field(default_factory=AggregateMetric)  # ns
    power: AggregateMetric = field(default_factory=AggregateMetric)  # W
    area: AggregateMetric = field(default_factory=AggregateMetric)  # mm²

    # Individual component measurements for each agregate
    components: dict[str, dict[str, Metric | None]] = field(default_factory=dict)

    # Electrical RX parameters
    input_impedance: Metric | None = None  # Ohms
    equalization: Metric | None = None

    # Optical RX parameters
    responsivity: Metric | None = None  # A/W
    sensitivity: Metric | None = None  # dBm
    input_capacitance: Metric | None = None  # pF

    # Reliability
    target_ber: Metric | None = None  # BER (unitless probability)

    def __post_init__(self):
        """Initialize component measurements from the source of truth."""
        parts = RECEIVER_PARTS[self.interconnect_type]

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
    def calculate_aggregates(self):
        """Calculate receiver aggregate measurements from its components."""

        parts = RECEIVER_PARTS[self.interconnect_type]

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