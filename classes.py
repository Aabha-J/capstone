from __future__ import annotations

from numbers import Real
from typing import ClassVar, Iterable


def _parameter_value(value: Real | Parameter | Calculation) -> Real | Parameter | Calculation:
    # This check is shared by every arithmetic operator so expressions fail
    # clearly when given text or another unsupported value.
    if isinstance(value, bool) or not isinstance(value, (Real, Parameter, Calculation)):
        raise TypeError("Calculations require numeric values or parameters.")
    return value


def _known_value(value: Real | Parameter | Calculation) -> Real | None:
    # Keep the distinction between an unknown value and a real numeric zero.
    if isinstance(value, Parameter):
        return value.value
    if isinstance(value, Calculation):
        return value.value
    return value


class Calculation:
    """An arithmetic expression that can include parameters without known values.

    For example, if `power` is unknown and `energy` is 4, `power + energy`
    displays as `4 + power`. The expression keeps its operands so it can also
    provide a numeric result later if all parameter values become known.
    """

    def __init__(
        self,
        operator: str,
        left: Real | Parameter | Calculation,
        right: Real | Parameter | Calculation,
    ) -> None:
        self.operator = operator
        self.left = _parameter_value(left)
        self.right = _parameter_value(right)

    @property
    def value(self) -> Real | None:
        # A result is numeric only when every input needed by the operation is known.
        left = _known_value(self.left)
        right = _known_value(self.right)
        if left is None or right is None:
            return None
        if self.operator == "+":
            return left + right
        if self.operator == "-":
            return left - right
        if self.operator == "*":
            return left * right
        if self.operator == "/":
            return left / right
        if self.operator == "**":
            return left**right
        if self.operator == "min":
            return min(left, right)
        raise ValueError(f"Unsupported operator: {self.operator}")

    def _calculate(
        self, operator: str, other: Real | Parameter | Calculation
    ) -> Real | Calculation:
        other = _parameter_value(other)
        left_value = _known_value(self)
        right_value = _known_value(other)
        if left_value is not None and right_value is not None:
            if operator == "+":
                return left_value + right_value
            if operator == "-":
                return left_value - right_value
            if operator == "*":
                return left_value * right_value
            if operator == "/":
                return left_value / right_value
            if operator == "**":
                return left_value**right_value
        return Calculation(operator, self, other)

    def __add__(self, other: Real | Parameter | Calculation) -> Real | Calculation:
        # Implementing Python's arithmetic methods lets callers write `a + b`
        # instead of calling a separate calculation function.
        return self._calculate("+", other)

    def __radd__(self, other: Real | Parameter | Calculation) -> Real | Calculation:
        return self._calculate("+", other)

    def __sub__(self, other: Real | Parameter | Calculation) -> Real | Calculation:
        return self._calculate("-", other)

    def __rsub__(self, other: Real | Parameter | Calculation) -> Real | Calculation:
        return Calculation("-", other, self)

    def __mul__(self, other: Real | Parameter | Calculation) -> Real | Calculation:
        return self._calculate("*", other)

    def __rmul__(self, other: Real | Parameter | Calculation) -> Real | Calculation:
        return self._calculate("*", other)

    def __truediv__(self, other: Real | Parameter | Calculation) -> Real | Calculation:
        return self._calculate("/", other)

    def __rtruediv__(self, other: Real | Parameter | Calculation) -> Real | Calculation:
        return Calculation("/", other, self)

    def __pow__(self, other: Real | Parameter | Calculation) -> Real | Calculation:
        return self._calculate("**", other)

    def __str__(self) -> str:
        if self.operator == "+":
            terms = _addition_terms(self)
            numeric_terms = [term for term in terms if isinstance(term, Real)]
            symbolic_terms = [term for term in terms if not isinstance(term, Real)]
            # Combine known addends, then show unknown parameter names at the end.
            numeric_total = sum(numeric_terms)
            ordered_terms: list[Real | Parameter | Calculation] = []
            if numeric_total != 0 or not symbolic_terms:
                ordered_terms.append(numeric_total)
            ordered_terms.extend(symbolic_terms)
            return " + ".join(_format_term(term) for term in ordered_terms)

        if self.operator == "min":
            return f"min({_format_term(self.left)}, {_format_term(self.right)})"
        symbols = {"+": "+", "-": "-", "*": "*", "/": "/", "**": "**"}
        return f"{_format_term(self.left)} {symbols[self.operator]} {_format_term(self.right)}"

    def __repr__(self) -> str:
        return f"Calculation({self})"


def _addition_terms(
    expression: Calculation,
) -> list[Real | Parameter | Calculation]:
    """Flatten additions so known values can be combined for readable output."""
    terms: list[Real | Parameter | Calculation] = []
    for operand in (expression.left, expression.right):
        if isinstance(operand, Calculation) and operand.operator == "+":
            terms.extend(_addition_terms(operand))
            continue
        value = _known_value(operand)
        terms.append(value if value is not None else operand)
    return terms


def _format_term(value: Real | Parameter | Calculation) -> str:
    if isinstance(value, Calculation) and value.operator in ("+", "-"):
        return f"({value})"
    return str(value)


class Parameter:
    """A named numeric quantity; a missing value is represented by its name.

    `unit` is optional metadata for display or data import; calculations operate
    on the numeric value only.
    """

    def __init__(self, name: str, value: Real | None = None, unit: str | None = None) -> None:
        if not name or not name.strip():
            raise ValueError("A parameter name is required.")
        if value is not None and (isinstance(value, bool) or not isinstance(value, Real)):
            raise TypeError("Parameter values must be numeric or None.")
        self.name = name
        self.value = value
        self.unit = unit

    # Each operator returns a normal number when both operands are known.
    # If either operand is unknown, it returns a Calculation to retain the
    # symbolic expression instead of treating the unknown as zero.
    def _calculate(
        self, operator: str, other: Real | Parameter | Calculation
    ) -> Real | Calculation:
        other = _parameter_value(other)
        left_value = _known_value(self)
        right_value = _known_value(other)
        if left_value is not None and right_value is not None:
            if operator == "+":
                return left_value + right_value
            if operator == "-":
                return left_value - right_value
            if operator == "*":
                return left_value * right_value
            if operator == "/":
                return left_value / right_value
            if operator == "**":
                return left_value**right_value
        return Calculation(operator, self, other)

    def __add__(self, other: Real | Parameter | Calculation) -> Real | Calculation:
        return self._calculate("+", other)

    def __radd__(self, other: Real | Parameter | Calculation) -> Real | Calculation:
        return self._calculate("+", other)

    def __sub__(self, other: Real | Parameter | Calculation) -> Real | Calculation:
        return self._calculate("-", other)

    def __rsub__(self, other: Real | Parameter | Calculation) -> Real | Calculation:
        return Calculation("-", other, self)

    def __mul__(self, other: Real | Parameter | Calculation) -> Real | Calculation:
        return self._calculate("*", other)

    def __rmul__(self, other: Real | Parameter | Calculation) -> Real | Calculation:
        return self._calculate("*", other)

    def __truediv__(self, other: Real | Parameter | Calculation) -> Real | Calculation:
        return self._calculate("/", other)

    def __rtruediv__(self, other: Real | Parameter | Calculation) -> Real | Calculation:
        return Calculation("/", other, self)

    def __pow__(self, other: Real | Parameter | Calculation) -> Real | Calculation:
        return self._calculate("**", other)

    def __str__(self) -> str:
        if self.value is not None:
            return str(self.value)
        if self.unit:
            return f"{self.name} ({self.unit})"
        return self.name

    def __repr__(self) -> str:
        return (
            f"{type(self).__name__}(name={self.name!r}, "
            f"value={self.value!r}, unit={self.unit!r})"
        )


class ElectricalParameter(Parameter):
    """A single parameter belonging to an electrical link.

    Example: `ElectricalParameter("lane_count", 4)`.
    """


class OpticalParameter(Parameter):
    """A single parameter belonging to an optical link.

    Example: `OpticalParameter("wavelength", 1550, "nm")`.
    """


class ParameterSet:
    """Base class for link parameter groups with shared named quantities.

    Subclasses define their own parameter names and parameter type, while this
    class creates each field consistently and allows both attribute and key access.
    """

    common_parameters: ClassVar[tuple[str, ...]] = (
        "data_rate",
        "energy_per_bit",
        "ber",
        "latency",
        "reach",
        "bandwidth_density",
        "area_footprint",
    )
    # A subclass overrides these two class attributes to choose its allowed
    # fields and the concrete Parameter type created for each field.
    parameter_type: ClassVar[type[Parameter]] = Parameter
    parameters: ClassVar[tuple[str, ...]] = common_parameters
    parameter_units: ClassVar[dict[str, str]] = {
        "data_rate": "Gbit/s",
        "energy_per_bit": "pJ/bit",
        "ber": "1",
        "latency": "ps",
        "reach": "mm",
        "bandwidth_density": "Gbit/s/mm^2",
        "area_footprint": "mm^2",
    }

    def __init__(self, **values: Real | str | None) -> None:
        # Reject misspelled column names rather than silently ignoring input.
        unexpected = set(values) - set(self.parameters)
        if unexpected:
            names = ", ".join(sorted(unexpected))
            raise TypeError(f"Unexpected {type(self).__name__} parameter(s): {names}")

        self._parameters: dict[str, Parameter] = {}
        for name in self.parameters:
            # Missing keys and blank CSV cells both become unknown parameters.
            value = _parse_value(values.get(name))
            self._parameters[name] = self.parameter_type(
                name, value, self.parameter_units.get(name)
            )

    @classmethod
    def from_mapping(cls, values: dict[str, Real | str | None]) -> ParameterSet:
        """Build a parameter set from row-like data, treating blank cells as unknown."""
        return cls(**values)

    def __getitem__(self, name: str) -> Parameter:
        try:
            return self._parameters[name]
        except KeyError:
            raise KeyError(f"{name!r} is not a parameter of {type(self).__name__}.") from None

    def __iter__(self) -> Iterable[str]:
        return iter(self._parameters)

    def __getattr__(self, name: str) -> Parameter:
        # Fields are exposed as attributes (set.data_rate) as well as dictionary
        # entries (set["data_rate"]) for convenient use in calculations.
        parameters = self.__dict__.get("_parameters", {})
        if name in parameters:
            return parameters[name]
        raise AttributeError(f"{type(self).__name__!s} has no parameter {name!r}.")


class ElectricalParameters(ParameterSet):
    """Electrical link quantities, including shared metrics and lane count."""

    parameter_type = ElectricalParameter
    # Electrical-only fields are added to the shared fields above.
    parameters = ParameterSet.common_parameters + ("lane_count",)
    parameter_units = ParameterSet.parameter_units | {"lane_count": "lanes"}


class OpticalParameters(ParameterSet):
    """Optical link quantities, including wavelength/channel and conversion metrics."""

    parameter_type = OpticalParameter
    # These include wavelength/channel details plus the energy and latency
    # contributions for both directions of optical/electrical conversion.
    parameters = ParameterSet.common_parameters + (
        "wavelength",
        "wavelength_count",
        "channel_count",
        "electrical_to_optical_conversion_energy",
        "electrical_to_optical_conversion_latency",
        "optical_to_electrical_conversion_energy",
        "optical_to_electrical_conversion_latency",
    )
    parameter_units = ParameterSet.parameter_units | {
        "wavelength": "nm",
        "wavelength_count": "wavelengths",
        "channel_count": "channels",
        "electrical_to_optical_conversion_energy": "pJ/bit",
        "electrical_to_optical_conversion_latency": "ps",
        "optical_to_electrical_conversion_energy": "pJ/bit",
        "optical_to_electrical_conversion_latency": "ps",
    }


class Interconnect:
    """An interconnect with a technology-specific set of parameters."""

    parameter_set_type: ClassVar[type[ParameterSet]] = ParameterSet

    def __init__(self, **values: Real | str | None) -> None:
        self.parameters = self.parameter_set_type(**values)

    @classmethod
    def from_mapping(cls, values: dict[str, Real | str | None]) -> Interconnect:
        """Build an interconnect from row-like data."""
        return cls(**values)

    def __getitem__(self, name: str) -> Parameter:
        return self.parameters[name]

    def __iter__(self) -> Iterable[str]:
        return iter(self.parameters)

    @property
    def effective_bandwidth(self) -> Real | Calculation:
        """Estimate capacity in Gbit/s; equations live in ``formulas.py``."""
        from .formulas import effective_bandwidth

        if isinstance(self, ElectricalInterconnect):
            return effective_bandwidth(
                data_rate=self.data_rate,
                bandwidth_density=self.bandwidth_density,
                area_footprint=self.area_footprint,
                lane_count=self.lane_count,
                optical=False,
            )
        if isinstance(self, OpticalInterconnect):
            return effective_bandwidth(
                data_rate=self.data_rate,
                bandwidth_density=self.bandwidth_density,
                area_footprint=self.area_footprint,
                wavelength_count=self.wavelength_count,
                channel_count=self.channel_count,
                optical=True,
            )
        raise TypeError("Effective bandwidth requires an electrical or optical interconnect.")

    def __getattr__(self, name: str) -> Parameter:
        # Expose parameter fields directly (interconnect.latency).
        parameters = self.__dict__.get("parameters")
        if parameters is not None:
            return getattr(parameters, name)
        raise AttributeError(f"{type(self).__name__!s} has no parameter {name!r}.")


class ElectricalInterconnect(Interconnect):
    """An interconnect with electrical-specific parameters such as lane count."""

    parameter_set_type = ElectricalParameters


class OpticalInterconnect(Interconnect):
    """An interconnect with optical-specific channel and conversion parameters."""

    parameter_set_type = OpticalParameters


def _parse_value(value: Real | str | None) -> Real | None:
    """Convert a CSV-style cell to a number; blanks remain unknown (`None`)."""
    if value is None or (isinstance(value, str) and not value.strip()):
        return None
    if isinstance(value, str):
        try:
            # Preserve whole numbers as integers and allow decimal/scientific values.
            value = float(value) if "." in value or "e" in value.lower() else int(value)
        except ValueError as error:
            raise ValueError(f"Parameter value must be numeric or blank: {value!r}") from error
    if isinstance(value, bool) or not isinstance(value, Real):
        raise TypeError("Parameter values must be numeric, numeric strings, or None.")
    return value
