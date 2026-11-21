PAPER = {
    "name": "Das Sharma",
    "reference": "https://doi.org/10.1038/s41928-024-01126-y",

    "tests": {
        "bump_density": [
            {
                "inputs": {"pitch_um": 9},
                "expected": 12346,
                "tolerance": 1,
            },
        ],

        "theoretical_bandwidth_density": [
            {
                "inputs": {
                    "pitch_um": 9,
                    "data_rate_gt_s": 4,
                },
                "expected": 6173,
                "tolerance": 1,
            },
        ],

        "realizable_bandwidth_density": [
            {
                "inputs": {
                    "pitch_um": 9,
                    "data_rate_gt_s": 4,
                    "bump_efficiency": 1.15,
                    "total_overhead": 0.03 + 0.10 + 0.35,
                },
                "expected": 3691.358025, #(1/(9*10^-3)^2)(1.15)(1-0.03-0.1-0.35)*(4/8)
                "tolerance": 1,
            },
        ],
    },
}