
from software_model.data.enums import InterconnectType


def calculate_bandwidth(interconnect) -> float | None:
    """
    Calculate aggregate raw bandwidth in GB/s.

    Assumes data_rate_per_lane is in Gb/s.
    """

    rate = interconnect.data_rate_per_lane

    if rate is None:
        return None

    if interconnect.interconnect_type == InterconnectType.ELECTRICAL:

        if interconnect.lane_width is None:
            return None

        bandwidth_gbps = rate * interconnect.lane_width

    elif interconnect.interconnect_type == InterconnectType.OPTICAL:

        if (
            interconnect.channel_count is None
            or interconnect.wavelength_count is None
        ):
            return None

        bandwidth_gbps = (
            rate
            * interconnect.channel_count
            * interconnect.wavelength_count
        )

    else:
        return None

    return bandwidth_gbps / 8


def calculate_total_latency(interconnect) -> float | None:
    """Calculate total latency if all required components are available."""

    components = [
        interconnect.phy_latency,
        interconnect.propagation_delay
    ]

    if interconnect.interconnect_type == InterconnectType.OPTICAL:
        components.extend([
            interconnect.eo_conversion_latency,
            interconnect.oe_conversion_latency
        ])

    if any(component is None for component in components):
        return None

    return sum(components)