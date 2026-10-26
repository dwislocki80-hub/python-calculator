"""Tests for the calculator logic (no window needed).

Run:  python -m unittest -v
"""

import unittest
from decimal import Decimal

from calculator.engine import DIVIDE_BY_ZERO, INVALID_INPUT, Calculator, format_number


def press(calc: Calculator, keys: str) -> Calculator:
    """Press a sequence of keys, e.g. press(calc, "12+7=").
    Letters stand for the function buttons: n = +/-, q = x², r = √, i = 1/x, p = %, b = backspace
    """
    actions = {
        "+": lambda: calc.press_operator("+"), "-": lambda: calc.press_operator("-"),
        "*": lambda: calc.press_operator("*"), "/": lambda: calc.press_operator("/"),
        "=": calc.press_equals, ".": calc.press_decimal_point, "n": calc.negate,
        "q": calc.square, "r": calc.square_root, "i": calc.reciprocal, "p": calc.percent,
        "b": calc.backspace, "C": calc.clear, "E": calc.clear_entry,
    }
    for key in keys:
        if key.isdigit():
            calc.press_digit(key)
        else:
            actions[key]()
    return calc


class TestFormatting(unittest.TestCase):
    def test_format_number(self):
        self.assertEqual(format_number(Decimal("0")), "0")
        self.assertEqual(format_number(Decimal("1234567.5")), "1,234,567.5")
        self.assertEqual(format_number(Decimal("2.50")), "2.5")
        self.assertEqual(format_number(Decimal("-42")), "-42")
        self.assertEqual(format_number(Decimal(1) / Decimal(3)), "0.3333333333333333")
        self.assertEqual(format_number(Decimal("1e20")), "1e+20")


class TestBasicMaths(unittest.TestCase):
    def check(self, keys: str, expected: str):
        self.assertEqual(press(Calculator(), keys).display, expected, f"keys: {keys}")

    def test_four_operations(self):
        self.check("12+7=", "19")
        self.check("12-20=", "-8")
        self.check("6*7=", "42")
        self.check("7/2=", "3.5")

    def test_no_float_rounding_errors(self):
        self.check(".1+.2=", "0.3")
        self.check("1/3*3=", "1")

    def test_immediate_execution_like_windows(self):
        self.check("2+3*4=", "20")  # (2+3)*4, not 2+(3*4)

    def test_repeated_equals(self):
        self.check("5+2===", "11")

    def test_operator_pressed_twice_replaces_it(self):
        self.check("8+*3=", "24")

    def test_continue_after_result(self):
        self.check("2+3=*10=", "50")

    def test_new_number_after_result_starts_over(self):
        self.check("2+3=7+1=", "8")


class TestTyping(unittest.TestCase):
    def test_thousands_separator_while_typing(self):
        self.assertEqual(press(Calculator(), "1234567").display, "1,234,567")

    def test_decimal_point_shown_while_typing(self):
        self.assertEqual(press(Calculator(), "3.").display, "3.")
        self.assertEqual(press(Calculator(), "3.05").display, "3.05")
        self.assertEqual(press(Calculator(), "3..5").display, "3.5")  # second point ignored

    def test_leading_zero_replaced(self):
        self.assertEqual(press(Calculator(), "007").display, "7")

    def test_max_16_digits(self):
        self.assertEqual(press(Calculator(), "12345678901234567890").display, "1,234,567,890,123,456")

    def test_backspace(self):
        self.assertEqual(press(Calculator(), "123b").display, "12")
        self.assertEqual(press(Calculator(), "5bb").display, "0")


class TestFunctions(unittest.TestCase):
    def test_square_root_square_reciprocal(self):
        self.assertEqual(press(Calculator(), "9r").display, "3")
        self.assertEqual(press(Calculator(), "5q").display, "25")
        self.assertEqual(press(Calculator(), "4i").display, "0.25")

    def test_negate(self):
        self.assertEqual(press(Calculator(), "5n").display, "-5")
        self.assertEqual(press(Calculator(), "5nn").display, "5")
        self.assertEqual(press(Calculator(), "0n").display, "0")

    def test_percent_like_windows(self):
        self.assertEqual(press(Calculator(), "200+10p=").display, "220")  # 10% of 200 added
        self.assertEqual(press(Calculator(), "50*10p=").display, "5")     # 50 * 0.1

    def test_function_inside_expression(self):
        calc = press(Calculator(), "2+9r")
        self.assertEqual(calc.expression, "2 + √(9)")
        press(calc, "=")
        self.assertEqual(calc.display, "5")
        self.assertEqual(calc.expression, "2 + √(9) =")

    def test_function_as_first_number_stays_in_expression(self):
        calc = press(Calculator(), "144r+.5=")
        self.assertEqual(calc.expression, "√(144) + 0.5 =")
        self.assertEqual(calc.display, "12.5")

    def test_function_after_result_starts_new_expression(self):
        calc = press(Calculator(), "5+4=r=")
        self.assertEqual(calc.display, "3")


class TestErrors(unittest.TestCase):
    def test_divide_by_zero(self):
        calc = press(Calculator(), "5/0=")
        self.assertEqual(calc.display, DIVIDE_BY_ZERO)
        self.assertEqual(calc.expression, "5 ÷ 0 =")

    def test_reciprocal_of_zero(self):
        self.assertEqual(press(Calculator(), "0i").display, DIVIDE_BY_ZERO)

    def test_square_root_of_negative(self):
        self.assertEqual(press(Calculator(), "4nr").display, INVALID_INPUT)

    def test_typing_after_error_starts_over(self):
        self.assertEqual(press(Calculator(), "5/0=7+1=").display, "8")

    def test_operators_ignored_during_error(self):
        self.assertEqual(press(Calculator(), "5/0=+").display, DIVIDE_BY_ZERO)


class TestClearAndExpression(unittest.TestCase):
    def test_expression_line(self):
        calc = press(Calculator(), "12+")
        self.assertEqual(calc.expression, "12 + ")
        press(calc, "7=")
        self.assertEqual(calc.expression, "12 + 7 =")

    def test_clear_entry_keeps_operation(self):
        self.assertEqual(press(Calculator(), "12+99E7=").display, "19")

    def test_clear_everything(self):
        calc = press(Calculator(), "12+7C")
        self.assertEqual((calc.display, calc.expression), ("0", ""))


class TestHistory(unittest.TestCase):
    def test_results_saved_newest_first(self):
        calc = press(Calculator(), "1+1=2*3=")
        self.assertEqual([h.result for h in calc.history], ["6", "2"])
        self.assertEqual(calc.history[0].expression, "2 × 3 =")

    def test_history_survives_clear(self):
        calc = press(Calculator(), "1+1=C")
        self.assertEqual(len(calc.history), 1)

    def test_use_history_item(self):
        calc = press(Calculator(), "1000*2=C")
        calc.use_history_item(calc.history[0])
        press(calc, "+1=")
        self.assertEqual(calc.display, "2,001")


if __name__ == "__main__":
    unittest.main()
