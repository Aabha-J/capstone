from software_model.data.enums import InterconnectType


TRANSMITTER_PARTS = {
    InterconnectType.ELECTRICAL: {
        "energy_per_bit": ("serializer",),
        "latency": ("serializer",),
        "power": ("serializer",),
        "area": ("serializer",),
    },
    InterconnectType.OPTICAL: {
        "energy_per_bit": ("serializer", "modulator", "laser"),
        "latency": ("serializer", "modulator", "eo_conversion"),
        "power": ("serializer", "modulator", "laser"),
        "area": ("serializer", "modulator", "laser"),
    },
}


RECEIVER_PARTS = {
    InterconnectType.ELECTRICAL: {
        "energy_per_bit": ("deserializer",),
        "latency": ("deserializer",),
        "power": ("deserializer",),
        "area": ("deserializer",),
    },
    InterconnectType.OPTICAL: {
        "energy_per_bit": ("photodetector", "deserializer"),
        "latency": ("photodetector", "oe_conversion", "deserializer"),
        "power": ("photodetector", "deserializer"),
        "area": ("photodetector", "deserializer"),
    },
}


