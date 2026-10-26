"""Calculator logic, completely separate from the window.

The engine knows nothing about buttons or Tkinter: the GUI only calls methods such as
`press_digit("7")` or `press_operator("+")` and then reads `display` and `expression`.
Thanks to this, all of the maths can be tested without opening a window.

It works like the standard Windows calculator ("immediate execution"):
    2 + 3 × 4 =  gives 20, because 2 + 3 is calculated as soon as × is pressed.
Pressing = again repeats the last operation:  5 + 2 = = =  gives 7, 9, 11.

Numbers are stored as Decimal, not float, so 0.1 + 0.2 shows 0.3 (not 0.30000000000000004).
"""

from dataclasses import dataclass
from decimal import Decimal, DivisionByZero, InvalidOperation, getcontext

getcontext().prec = 32  # more precision than we show, so rounding errors stay invisible

MAX_DIGITS = 16  # the longest number a user can type, like in Windows
OPERATORS = {"+": "+", "-": "−", "*": "×", "/": "÷"}  # key -> symbol shown on screen

DIVIDE_BY_ZERO = "Cannot divide by zero"
INVALID_INPUT = "Invalid input"
OVERFLOW = "Overflow"


class CalculatorError(Exception):
    """Raised inside the engine when a calculation is not possible."""


@dataclass
class HistoryItem:
    expression: str  # e.g. "12 + 7 ="
    result: str      # e.g. "19"


def format_number(value: Decimal) -> str:
    """Decimal -> text for the display, e.g. 1234567.5 -> '1,234,567.5'"""
    if value.is_zero():
        return "0"
    if abs(value) >= Decimal("1e16") or abs(value) < Decimal("1e-15"):
        text = f"{value:.{MAX_DIGITS - 1}E}"               # very big or very small: scientific
        mantissa, exponent = text.split("E")
        mantissa = mantissa.rstrip("0").rstrip(".")
        return f"{mantissa}e{int(exponent):+d}"

    # round to 16 significant digits, then drop trailing zeros
    # (adjusted() is the position of the first digit: 123.4 -> 2, 0.05 -> -2)
    rounded = round(value, MAX_DIGITS - (value.adjusted() + 1))
    text = f"{rounded:,f}"
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text


class Calculator:
    def __init__(self):
        self.history: list[HistoryItem] = []
        self.clear()

    # ---------- what the GUI reads ----------

    @property
    def display(self) -> str:
        """Big number at the bottom of the screen."""
        if self.error:
            return self.error
        if self._typing is not None:
            return self._format_typing(self._typing)
        return format_number(self.entry)

    @property
    def expression(self) -> str:
        """Small line above the number, e.g. '12 + ' or '12 + 7 ='."""
        return self._expression

    # ---------- buttons ----------

    def clear(self) -> None:
        """C – forget everything except the history."""
        self.entry = Decimal(0)          # number currently on screen
        self._typing: str | None = None  # text while the user is typing digits, e.g. "12."
        self._entry_label = ""           # how the entry appears in the expression, e.g. "sqr(5)"
        self._accumulator: Decimal | None = None
        self._left_label = ""             # first number as shown in the expression, e.g. "√(144)"
        self._pending: str | None = None  # operator waiting for its second number
        self._repeat: tuple[str, Decimal] | None = None  # for pressing = several times
        self._expression = ""
        self.error = ""

    def clear_entry(self) -> None:
        """CE – clear only the number being typed."""
        if self.error:
            self.clear()
            return
        if self._expression.endswith("="):
            self._detach_from_result()
        self.entry = Decimal(0)
        self._typing = None
        self._entry_label = ""
        if self._pending is None:
            self._expression = ""

    def press_digit(self, digit: str) -> None:
        self._start_fresh_if_needed()
        if self._typing is None:
            self._typing = ""
            self._entry_label = ""
        if self._typing == "0":
            self._typing = ""
        if len(self._typing.replace(".", "").replace("-", "")) >= MAX_DIGITS:
            return  # number is already as long as allowed
        self._typing += digit
        self.entry = Decimal(self._typing)

    def press_decimal_point(self) -> None:
        self._start_fresh_if_needed()
        if self._typing is None:
            self._typing = "0"
            self._entry_label = ""
        if "." not in self._typing:
            self._typing += "."

    def backspace(self) -> None:
        if self.error:
            self.clear()
            return
        if self._typing is None:
            return  # a result is on screen – Windows does not edit results
        self._typing = self._typing[:-1]
        if self._typing in ("", "-", "-0"):
            self._typing = "0"
        self.entry = Decimal(self._typing.rstrip("."))

    def press_operator(self, key: str) -> None:
        if self.error:
            return
        if key not in OPERATORS:
            raise ValueError(f"Unknown operator: {key}")
        just_finished = self._expression.endswith("=")

        if self._pending is not None and self._typing is None and not self._entry_label and not just_finished:
            # operator pressed twice in a row (2 + ×): just swap the operator
            self._pending = key
        else:
            if self._pending is not None and not just_finished:
                if not self._calculate(self._pending, self.entry):
                    return
                self._left_label = format_number(self._accumulator)
            else:
                self._accumulator = self.entry
                self._left_label = self._entry_label or format_number(self.entry)
            self._pending = key
            self.entry = self._accumulator

        self._typing = None
        self._entry_label = ""
        self._repeat = None
        self._expression = f"{self._left_label} {OPERATORS[key]} "

    def press_equals(self) -> None:
        if self.error:
            self.clear()
            return
        label = self._entry_label or format_number(self.entry)

        if self._pending is not None and not self._expression.endswith("="):
            operator, operand = self._pending, self.entry
            left = self._left_label
        elif self._repeat is not None:
            operator, operand = self._repeat        # = pressed again: repeat last operation
            self._accumulator = self.entry
            left, label = format_number(self.entry), format_number(operand)
        else:
            self._expression = f"{label} ="           # just a number and =
            self._finish_with(self.entry)
            return

        self._expression = f"{left} {OPERATORS[operator]} {label} ="  # shown even if it fails
        if self._calculate(operator, operand):
            self._repeat = (operator, operand)
            self._pending = operator
            self.entry = self._accumulator
            self._finish_with(self.entry)
            self.history.insert(0, HistoryItem(self._expression, self.display))

    def negate(self) -> None:
        """+/- button"""
        if self.error:
            return
        if self._typing is not None:
            if Decimal(self._typing.rstrip(".") or "0") == 0:
                return
            self._typing = self._typing[1:] if self._typing.startswith("-") else "-" + self._typing
            self.entry = Decimal(self._typing.rstrip(".") or "0")
        else:
            self._apply_function(lambda x: -x, "negate")

    def percent(self) -> None:
        """% works like in Windows: in 200 + 10 % the 10 % means 10 % of 200 = 20."""
        if self.error:
            return
        if self._expression.endswith("="):
            self._detach_from_result()
        if self._pending in ("+", "-") and self._accumulator is not None:
            value = self._accumulator * self.entry / 100
        else:
            value = self.entry / 100
        self.entry = value
        self._typing = None
        self._entry_label = format_number(value)
        self._show_entry_in_expression()

    def reciprocal(self) -> None:
        """1/x"""
        self._apply_function(lambda x: 1 / x, "1/")

    def square(self) -> None:
        """x²"""
        self._apply_function(lambda x: x * x, "sqr")

    def square_root(self) -> None:
        """√x"""
        def root(x: Decimal) -> Decimal:
            if x < 0:
                raise CalculatorError(INVALID_INPUT)
            return x.sqrt()
        self._apply_function(root, "√")

    def use_history_item(self, item: HistoryItem) -> None:
        """Clicking a history entry puts its result back on the screen."""
        self.clear()
        self._expression = item.expression
        self.entry = Decimal(item.result.replace(",", ""))

    # ---------- internals ----------

    def _start_fresh_if_needed(self) -> None:
        """Typing a digit after an error or after = starts a new calculation."""
        if self.error or self._expression.endswith("="):
            history = self.history
            self.clear()
            self.history = history

    def _detach_from_result(self) -> None:
        """Keep the result on screen, but forget the finished calculation around it."""
        self._pending = None
        self._repeat = None
        self._accumulator = None
        self._left_label = ""
        self._expression = ""

    def _calculate(self, operator: str, operand: Decimal) -> bool:
        """accumulator = accumulator <operator> operand.  Returns False after an error."""
        try:
            a, b = self._accumulator, operand
            if operator == "+":
                result = a + b
            elif operator == "-":
                result = a - b
            elif operator == "*":
                result = a * b
            else:
                if b == 0:
                    raise CalculatorError(DIVIDE_BY_ZERO)
                result = a / b
            self._accumulator = self._check_size(result)
            return True
        except CalculatorError as error:
            self._fail(str(error))
            return False

    def _apply_function(self, function, name: str) -> None:
        """Run a one-number function (√, x², 1/x, negate) on the number on screen."""
        if self.error:
            return
        label = self._entry_label or format_number(self.entry)
        try:
            if name == "1/" and self.entry == 0:
                raise CalculatorError(DIVIDE_BY_ZERO)
            value = self._check_size(function(self.entry))
        except (CalculatorError, InvalidOperation, DivisionByZero) as error:
            message = str(error) if isinstance(error, CalculatorError) else INVALID_INPUT
            self._fail(message)
            return
        if self._expression.endswith("="):
            self._detach_from_result()     # √ right after a result starts a new expression
        self.entry = value
        self._typing = None
        self._entry_label = f"{name}({label})" if name != "1/" else f"1/({label})"
        self._show_entry_in_expression()

    def _show_entry_in_expression(self) -> None:
        if self._pending is not None and not self._expression.endswith("="):
            self._expression = f"{self._left_label} {OPERATORS[self._pending]} {self._entry_label}"
        else:
            self._expression = self._entry_label

    @staticmethod
    def _check_size(value: Decimal) -> Decimal:
        if abs(value) >= Decimal("1e10000"):
            raise CalculatorError(OVERFLOW)
        return value

    def _finish_with(self, value: Decimal) -> None:
        self.entry = value
        self._typing = None
        self._entry_label = ""

    def _fail(self, message: str) -> None:
        history = self.history
        expression = self._expression
        self.clear()
        self.history = history
        self._expression = expression
        self.error = message

    @staticmethod
    def _format_typing(text: str) -> str:
        """Show typed text with thousands separators, keeping a trailing '.' or zeros."""
        sign = "-" if text.startswith("-") else ""
        digits = text.lstrip("-")
        whole, dot, fraction = digits.partition(".")
        return f"{sign}{int(whole or 0):,}{dot}{fraction}"
