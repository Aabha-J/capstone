from dataclasses import dataclass, field
from typing import Optional

from software_model.data.enums import InterconnectType
from software_model.data.interconnect_classes.channel import Channel
from software_model.data.interconnect_classes.receiver import Receiver
from software_model.data.interconnect_classes.transmitter import Transmitter
from software_model.data.metrics import (
    InterconnectOverall,
    Metric,
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
    energy_per_bit: InterconnectOverall = field(default_factory=InterconnectOverall)  # pJ/bit
    power: InterconnectOverall = field(default_factory=InterconnectOverall)  # W
    area: InterconnectOverall = field(default_factory=InterconnectOverall)  # mm²

    # Aggregate latency
    phy_latency: InterconnectOverall = field(default_factory=InterconnectOverall)  # ns
    total_latency: InterconnectOverall = field(default_factory=InterconnectOverall)  # ns

    # Component parameters
    transmitter: Optional[Transmitter] = None
    channel: Optional[Channel] = None
    receiver: Optional[Receiver] = None

    # Metadata
    source: Optional[str] = None
    notes: Optional[str] = None

    def calculate_energy_per_bit(self):
        """Calculate total interconnect energy per bit."""

        self.energy_per_bit.calculate_sum(
            parts={
                "transmitter": (
                    self.transmitter.energy_per_bit if self.transmitter else None
                ),
                "receiver": (
                    self.receiver.energy_per_bit if self.receiver else None
                ),
            },
            formula="transmitter + receiver",
        )

    def calculate_power(self):
        """Calculate total interconnect power."""

        self.power.calculate_sum(
            parts={
                "transmitter": (
                    self.transmitter.power if self.transmitter else None
                ),
                "receiver": (
                    self.receiver.power if self.receiver else None
                ),
            },
            formula="transmitter + receiver",
        )

    def calculate_area(self):
        """Calculate total interconnect area."""

        self.area.calculate_sum(
            parts={
                "transmitter": (
                    self.transmitter.area if self.transmitter else None
                ),
                "channel": (
                    self.channel.area if self.channel else None
                ),
                "receiver": (
                    self.receiver.area if self.receiver else None
                ),
            },
            formula="transmitter + channel + receiver",
        )

    def calculate_phy_latency(self):
        """Calculate PHY latency from transmitter and receiver."""

        self.phy_latency.calculate_sum(
            parts={
                "transmitter": (
                    self.transmitter.latency if self.transmitter else None
                ),
                "receiver": (
                    self.receiver.latency if self.receiver else None
                ),
            },
            formula="transmitter + receiver",
        )

    def calculate_total_latency(self):
        """Calculate total interconnect latency."""

        self.total_latency.calculate_sum(
            parts={
                "phy_latency": self.phy_latency,
                "channel_propagation_delay": (
                    self.channel.propagation_delay if self.channel else None
                ),
            },
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