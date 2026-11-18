from dataclasses import dataclass, field

from software_model.data.enums import InterconnectType
from software_model.data.interconnect_components import RECEIVER_PARTS
from software_model.data.metrics import AggregateMetric, Metric


@dataclass
class Receiver:
    interconnect_type: InterconnectType

    # Receiver aggregate measurements
    energy_per_bit: AggregateMetric = field(default_factory=AggregateMetric)  # pJ/bit
    latency: AggregateMetric = field(default_factory=AggregateMetric)  # ns
    power: AggregateMetric = field(default_factory=AggregateMetric)  # W
    area: AggregateMetric = field(default_factory=AggregateMetric)  # mm²

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
        """Initialize component measurements for each aggregate."""
        parts = RECEIVER_PARTS[self.interconnect_type]

        for aggregate_name, component_names in parts.items():
            aggregate = getattr(self, aggregate_name)
            aggregate.components = {
                component: None
                for component in component_names
            }