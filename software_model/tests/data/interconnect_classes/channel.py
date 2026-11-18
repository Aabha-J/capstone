from dataclasses import dataclass
from typing import Optional

from software_model.data.metrics import Metric


@dataclass
class Channel:

    link_length: Optional[Metric] = None  # mm
    reach: Optional[Metric] = None  # mm
    propagation_delay: Optional[Metric] = None  # ns
    area: Optional[Metric] = None  # mm²

    # Optical channel parameters
    propagation_loss: Optional[Metric] = None  # dB
    coupling_loss: Optional[Metric] = None  # dB

    # Electrical channel parameters
    insertion_loss: Optional[Metric] = None  # dB
    characteristic_impedance: Optional[Metric] = None  # Ohms
    crosstalk: Optional[Metric] = None  # Source-defined unit