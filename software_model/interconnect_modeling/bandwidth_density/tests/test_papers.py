import pytest

from software_model.interconnect_modeling.bandwidth_density.tests.paper_data import (
    PAPER as DAS_SHARMA,
)


PAPERS = [
    DAS_SHARMA,
]


from software_model.interconnect_modeling.bandwidth_density.formulas import (
    bump_density,
    theoretical_bandwidth_density,
    realizable_bandwidth_density,
)


def evaluate_case(formula, case):
    """Run one paper validation case against a formula."""

    result = formula(**case["inputs"])

    if case["expected"] is not None:
        assert result == pytest.approx(
            case["expected"],
            abs=case["tolerance"],
        )

    return result


def evaluate_paper(paper):
    """Evaluate every supplied test case for one paper."""

    formulas = {
        "bump_density": bump_density,
        "theoretical_bandwidth_density": theoretical_bandwidth_density,
        "realizable_bandwidth_density": realizable_bandwidth_density,
    }

    for formula_name, cases in paper["tests"].items():
        formula = formulas[formula_name]

        for case in cases:
            evaluate_case(formula, case)


def test_papers():
    for paper in PAPERS:
        evaluate_paper(paper)