from dataclasses import dataclass, field
from typing import Optional

from software_model.data.metrics import AggregateMetric, Metric


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
