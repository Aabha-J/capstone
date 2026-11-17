from dataclasses import dataclass, field
from typing import Optional

from software_model.data.enums import InterconnectType
from software_model.data.metrics import AggregateMetric, Metric

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

