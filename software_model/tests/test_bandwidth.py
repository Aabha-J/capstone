import unittest

from software_model.classes import Calculation, ElectricalInterconnect, OpticalInterconnect
from software_model.network import Chiplet, InterconnectGraph, Packet


class EffectiveBandwidthTests(unittest.TestCase):
    def test_electrical_bandwidth_includes_lane_width(self) -> None:
        interconnect = ElectricalInterconnect(
            data_rate=10,
            lane_count=4,
            lane_width=8,
            bandwidth_density=1_000,
            area_footprint=1,
        )

        self.assertEqual(interconnect.effective_bandwidth, 320)

    def test_optical_rate_scales_by_wavelengths_and_fiber_count(self) -> None:
        interconnect = OpticalInterconnect(
            data_rate=100,
            wavelength_count=4,
            channel_count=4,
            bandwidth_density=1_000,
            area_footprint=2,
        )

        self.assertEqual(interconnect.effective_bandwidth, 1_600)

    def test_area_limit_caps_aggregate_rate(self) -> None:
        interconnect = ElectricalInterconnect(
            data_rate=10,
            lane_count=4,
            lane_width=8,
            bandwidth_density=100,
            area_footprint=1,
        )

        self.assertEqual(interconnect.effective_bandwidth, 100)

    def test_unknown_electrical_width_remains_symbolic(self) -> None:
        interconnect = ElectricalInterconnect(
            data_rate=10,
            lane_count=4,
            lane_width=None,
            bandwidth_density=1_000,
            area_footprint=1,
        )

        self.assertIsInstance(interconnect.effective_bandwidth, Calculation)
        self.assertIsNone(interconnect.effective_bandwidth.value)

    def test_simulation_serialization_uses_effective_electrical_bandwidth(self) -> None:
        source = Chiplet("source")
        destination = Chiplet("destination")
        graph = InterconnectGraph()
        graph.add_chiplet(source)
        graph.add_chiplet(destination)
        graph.add_interconnect(
            source,
            destination,
            ElectricalInterconnect(
                data_rate=10,
                lane_count=4,
                lane_width=8,
                bandwidth_density=1_000,
                area_footprint=1,
                latency=3,
                energy_per_bit=0,
                ber=0,
                reach=100,
            ),
        )

        result = graph.simulate_packet(Packet(source, destination, 3_200))

        self.assertEqual(result.latency, 10_003)


if __name__ == "__main__":
    unittest.main()
