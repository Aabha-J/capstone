"""Compare FPGA cycle counts with the units used in software_model/formulas.py.

Run: python3 tools/compare_metrics.py --packet-bits 256 --cycles 4 --packets 100 --duration-cycles 5000
This is a unit/metric bridge, not a claim that the FPGA models a 320-Gbit/s link.
"""
import argparse


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--packet-bits', type=int, default=256)
    p.add_argument('--cycles', type=int, default=4, help='Measured send-to-receive cycles')
    p.add_argument('--packets', type=int, default=100)
    p.add_argument('--duration-cycles', type=int, default=5000)
    p.add_argument('--clock-hz', type=float, default=50_000_000)
    p.add_argument('--energy-per-bit-pj', type=float, default=None)
    p.add_argument('--ber', type=float, default=None)
    args = p.parse_args()
    if args.packet_bits <= 0 or args.cycles < 0 or args.packets < 0 or args.duration_cycles <= 0 or args.clock_hz <= 0:
        p.error('packet bits, duration, and clock rate must be positive; other counts nonnegative')
    clock_period_ns = 1e9 / args.clock_hz
    latency_ps = args.cycles * clock_period_ns * 1000
    duration_ns = args.duration_cycles * clock_period_ns
    offered_rate = args.packets / duration_ns
    print(f'FPGA measured latency: {latency_ps:g} ps ({args.cycles} cycles)')
    print(f'Offered packet rate: {offered_rate:g} packets/ns')
    print(f'Offered bit rate: {offered_rate * args.packet_bits:g} Gbit/s')
    if args.energy_per_bit_pj is not None:
        print(f'Model-based total energy: {args.packets * args.packet_bits * args.energy_per_bit_pj:g} pJ')
    if args.ber is not None:
        if not 0 <= args.ber <= 1:
            p.error('--ber must be between 0 and 1')
        print(f'Model-based packet error probability: {1 - (1 - args.ber) ** args.packet_bits:g}')
    print('Note: modeled energy and BER are estimates, not physical FPGA measurements.')


if __name__ == '__main__':
    main()
