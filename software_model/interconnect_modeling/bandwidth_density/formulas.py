#https://doi.org/10.1038/s41928-024-01126-y

def bump_density(pitch_um):
    """Das Sharma Eq. 1: bump density in bumps/mm²."""
    pitch_mm = pitch_um / 1000
    return 1 / pitch_mm**2


def theoretical_bandwidth_density(pitch_um, data_rate_gt_s):
    """Das Sharma Eq. 2: theoretical bandwidth density in GB/s/mm²."""
    return bump_density(pitch_um) * (data_rate_gt_s / 8) #/8 to go from bits to bytes


def realizable_bandwidth_density(
    pitch_um,
    data_rate_gt_s,
    bump_efficiency,
    total_overhead,
):
    """Das Sharma Eq. 3: realizable bandwidth density in GB/s/mm²."""

    return bump_density(pitch_um) * bump_efficiency * (1 - total_overhead)*(data_rate_gt_s / 8)