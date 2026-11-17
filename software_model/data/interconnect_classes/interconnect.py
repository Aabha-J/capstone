from dataclasses import dataclass, field
from typing import Optional

from software_model.data.enums import InterconnectType
from software_model.data.interconnect_classes.channel import Channel
from software_model.data.interconnect_classes.receiver import Receiver
from software_model.data.interconnect_classes.transmitter import Transmitter
from software_model.data.metrics import (
    AggregateMetric,
    Metric,
    calculate_aggregate_sum,
)


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

    def calculate_energy_per_bit(self):
        """Calculate total interconnect energy per bit."""

        calculate_aggregate_sum(
            aggregate=self.energy_per_bit,
            parts=(
                self.transmitter.energy_per_bit.metric if self.transmitter else None,
                self.receiver.energy_per_bit.metric if self.receiver else None,
            ),
            formula="transmitter + receiver",
        )


    def calculate_power(self):
        """Calculate total interconnect power."""

        calculate_aggregate_sum(
            aggregate=self.power,
            parts=(
                self.transmitter.power.metric if self.transmitter else None,
                self.receiver.power.metric if self.receiver else None,
            ),
            formula="transmitter + receiver",
        )


    def calculate_area(self):
        """Calculate total interconnect area."""

        calculate_aggregate_sum(
            aggregate=self.area,
            parts=(
                self.transmitter.area.metric if self.transmitter else None,
                self.channel.area if self.channel else None,
                self.receiver.area.metric if self.receiver else None,
            ),
            formula="transmitter + channel + receiver",
        )


    def calculate_phy_latency(self):
        """Calculate PHY latency from transmitter and receiver."""

        calculate_aggregate_sum(
            aggregate=self.phy_latency,
            parts=(
                self.transmitter.latency.metric if self.transmitter else None,
                self.receiver.latency.metric if self.receiver else None,
            ),
            formula="transmitter + receiver",
        )


    def calculate_total_latency(self):
        """Calculate total interconnect latency."""

        calculate_aggregate_sum(
            aggregate=self.total_latency,
            parts=(
                self.phy_latency.metric,
                self.channel.propagation_delay if self.channel else None,
            ),
            formula="PHY latency + channel propagation delay",
        )

    def calculate_aggregates(self):
        """Calculate all interconnect aggregate measurements."""

        self.calculate_energy_per_bit()
        self.calculate_power()
        self.calculate_area()

        # PHY latency must be calculated before total latency.
        self.calculate_phy_latency()
        self.calculate_total_latency()