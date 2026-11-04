# Chiplet interconnect FPGA baseline (DE1-SoC)

This is a first milestone, **not** the full 2x2 mesh or a physical optical link.
Two logical chiplets communicate through a simple clocked link in the FPGA fabric.

## Files
- `rtl/chiplet_link.sv`: one-packet link with configurable cycle delay and ready/valid.
- `rtl/de1_soc_top.sv`: traffic generator, receiver checking, and counters.
- `quartus/de1_soc_pins.qsf`: board pin and project assignments (copy into your Quartus project `.qsf`, adjusting source paths).
- `quartus/de1_soc.sdc`: 50 MHz clock constraint.

## Board demo
1. Create a Quartus project targeting **5CSEMA5F31C6** with top `de1_soc_top`.
2. Add both SystemVerilog files and the SDC; merge the pin assignments into your project QSF. Source paths in the supplied QSF are relative to this package root.
3. Compile, inspect warnings and timing, and program the `.sof` via USB-Blaster.
4. KEY0 resets. KEY1 toggles traffic generation. SW[3:0] selects packet interval.
5. LEDR0 = running, LEDR1 toggles after a packet arrives, LEDR2 = any data mismatch, LEDR[9:3] = latency cycles (low 7 bits).

At 50 MHz, each cycle is 20 ns. The measured latency is an FPGA logical-path latency, not physical inter-chiplet propagation delay. This demo only has one outstanding packet and does not yet implement a FIFO, 2x2 mesh, or realistic link bandwidth. Throughput and packet counters are internal for now; expose them through UART, HPS/Avalon, or SignalTap later.

## Next implementation steps
1. Add a small FIFO and ready/valid backpressure.
2. Define a packet header with source/destination IDs, payload, and timestamp or packet ID.
3. Build a 2x2 mesh with four routers and XY routing.
4. Add uniform/hotspot traffic and configurable injection rate.
5. Export packets, cycles, stalls, and error counts to CSV to compare with the Python model.
6. Keep electrical/photonic/hybrid link parameters and E/O + O/E overhead in the Python prediction layer; validate the electrical logical-network baseline first.

## Limitations
The GitHub software_model folder was not accessible while preparing this starter, so the packet format and parameters have **not** been matched to that code. Pin mappings are provided for the standard DE1-SoC board and should be checked against your board revision's Terasic pin table before programming. This package has not been compiled in Quartus or tested on a physical board in this environment.

## Matching the team's Python software model (Nov 2026)

The software model defines **packet size in bits**, **simulation duration in ns**,
**link latency in ps**, **bandwidth in Gbit/s**, **energy in pJ/bit**, and
**BER as a probability**. Keep these units separate from FPGA clock cycles.

For an electrical edge, the software predicts:

- `capacity_gbps = min(data_rate_Gtransfers_s * lane_width * lane_count, bandwidth_density * area_footprint)`
- `edge_latency_ps = base_latency_ps + 1000 * packet_bits / capacity_gbps`
- `edge_energy_pj = packet_bits * energy_per_bit_pj`
- `edge_error_probability = 1 - (1 - BER) ** packet_bits`

The FPGA baseline measures **clocked transfers**, not a physical high-speed
chiplet link. At 50 MHz, one cycle is **20 ns = 20,000 ps**. Do not directly
compare FPGA cycle latency with the Python link's 10,003 ps example: these
are different technologies and timing assumptions. First compare packet counts,
correct delivery, packet order, and traffic configuration. Use a separate
calibrated clocked model if you later want latency agreement.

### Files added for alignment

- `tb/tb_chiplet_link.sv`: basic self-checking link testbench (two packets).
- `tools/compare_metrics.py`: convert FPGA cycle results to the Python model's
  units and calculate modeled energy and BER using the same equations.

### Suggested next RTL milestones

1. **Traffic matrix replay**: load a fixed list of `(source, destination, count)`
   generated from `RandomTrafficMatrixGenerator` instead of trying to reproduce
   Python's `random.Random(seed)` in hardware. This guarantees identical workloads.
2. **Packet format**: add `source_id`, `destination_id`, `sequence_id`, and a
   configurable payload length; preserve the model's `packet_size_bits` meaning.
3. **FIFO + ready/valid**: track accepted transfers and stalls separately.
4. **Four-chiplet mesh**: add routers and route tables; check paths against the
   software model's lowest-latency paths. Note: Python currently has no queuing
   or contention, so measured congestion delays are an extension, not a mismatch.
5. **Counter export**: expose sent, delivered, corrupted, latency sum, and
   measurement window through UART or HPS for reproducible CSV comparisons.
6. **Optical/hybrid analysis**: use the Python model's E/O and O/E conversion
   equations. The FPGA itself does not implement photonic devices.

### Run the added unit conversion helper

```bash
python3 tools/compare_metrics.py --packet-bits 256 --cycles 4 --packets 100 --duration-cycles 5000 --energy-per-bit-pj 0.5 --ber 0.000001
```

### Simulate the link (if Icarus Verilog is installed)

```bash
iverilog -g2012 -s tb_chiplet_link -o link_test tb/tb_chiplet_link.sv rtl/chiplet_link.sv
vvp link_test
```

This is a **starter**, not a verified Quartus compilation or hardware-tested
implementation. Check DE1-SoC board revision and pin assignments. The current
RTL has only two logical chiplets, a 16-bit test transfer, and a single
in-flight packet. It does **not** yet implement a 256-bit packet serializer,
mesh routing, FIFO, traffic-matrix replay, or power measurement.
