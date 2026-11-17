
from enum import Enum


class InterconnectType(Enum):
    OPTICAL = "optical"
    ELECTRICAL = "electrical"


class Topology(Enum):
    MESH = "Mesh"
    RING = "Ring"
    DIRECT = "Direct"


class TrafficPattern(Enum):
    UNIFORM = "uniform"
    RANDOM = "random"
    HOTSPOT = "hotspot"
