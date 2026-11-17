from dataclasses import dataclass, field
from typing import Optional

from software_model.data.enums import InterconnectType
from software_model.data.interconnect_classes.channel import Channel
from software_model.data.interconnect_classes.receiver import Receiver
from software_model.data.interconnect_classes.transmitter import Transmitter
from software_model.data.metrics import AggregateMetric, Metric


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