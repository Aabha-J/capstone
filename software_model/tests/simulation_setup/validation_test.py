import pytest
from software_model.simulation.performance_analyzer import analyze, validate_metrics
from software_model.simulation.simulation_engine import PacketResult

def test_validation_matches_reference():
    packet = PacketResult(0, 1, 100, 0, 0, 100, 105, 0, 100, 105, 1600)
    metrics = analyze([packet], 200)
    result = validate_metrics(metrics, {"average_latency_ns": 105, "throughput_gbps": 4})
    assert all(r.passed for r in result)

def test_missing_energy_not_validated():
    packet = PacketResult(0, 1, 100, 0, 0, 100, 105, 0, 100, 105, None)
    metrics = analyze([packet], 200)
    assert validate_metrics(metrics, {"total_energy_pj": 1600})[0].passed is None

def test_bad_reference_rejected():
    with pytest.raises(ValueError):
        validate_metrics(analyze([], 100), {"bandwidth": 2})
