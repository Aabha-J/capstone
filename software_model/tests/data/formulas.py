
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

