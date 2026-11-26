"""Tests of generate_validators.py on a small model (no network, no other repository).

    python3 -m unittest -q test_generator        (from this folder)
"""
import os
import tempfile
import unittest
from collections import OrderedDict

import generate_validators as gv

XSI = 'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"'


class FakeModel:
    """IA { IB Coll (0..n), IC? Opt, Max35Text Name, ActiveCurrencyAndAmount Amt }; IB { Max35Text? X, ISODate? D }"""

    def __init__(self):
        self.ifaces = {
            "IA": OrderedDict(
                Coll=("IB", False, True),
                Opt=("IC", True, False),
                Name=("Max35Text", False, False),
                Amt=("ActiveCurrencyAndAmount", False, False),
                Mode=("Mode1Code", False, False),
            ),
            "IB": OrderedDict(X=("Max35Text", True, False), D=("ISODate", True, False)),
            "IC": OrderedDict(),
        }
        self.structs = {"Max35Text", "ISODate"}
        self.enums = {"Mode1Code"}
        self.hand = {}

    def kind(self, t):
        return gv.Model.kind(self, t)

    def is_choice(self, t):
        return False


def rule(kind, must=None, cond=None):
    def sec(s):
        if s is None:
            return ""
        tag, conn, brs = s
        body = "".join(
            f'<BooleanRule xsi:type="{t}"><leftOperand>{l}</leftOperand>' + (f"<rightOperand>{r}</rightOperand>" if r else "") + "</BooleanRule>"
            for t, l, r in brs
        )
        return f"<{tag}><connector>{conn}</connector>{body}</{tag}>"

    return f'<RuleDefinition {XSI}><{kind} {XSI} xsi:type="{kind}">{sec(must)}{sec(cond)}</{kind}></RuleDefinition>'


class RuleTests(unittest.TestCase):
    def setUp(self):
        self.g = gv.Gen(FakeModel())

    def expr(self, xml):
        kind, must, cond = gv.parse_rule(xml)
        body = self.g.section("x", "IA", must)
        return body if cond is None else f"!({self.g.section('x', 'IA', cond)}) || ({body})"

    def test_absence_of_every_item_is_a_negation_inside_the_quantifier(self):
        # "no item has X" is All(item has no X), not "not all items have X"
        e = self.expr(rule("SimpleRule", ("mustBe", "AND", [("Absence", "/Coll[*]/X", None)])))
        self.assertEqual(e, "(x?.Coll ?? []).All(i1 => !(i1?.X is not null))")

    def test_presence_of_every_item(self):
        e = self.expr(rule("SimpleRule", ("mustBe", "AND", [("Presence", "/Coll[*]/X", None)])))
        self.assertEqual(e, "(x?.Coll ?? []).All(i1 => i1?.X is not null)")

    def test_a_complex_rule_is_a_condition_and_a_consequence(self):
        e = self.expr(
            rule(
                "ComplexRule",
                ("mustBe", "AND", [("Absence", "/Opt", None)]),
                ("onCondition", "AND", [("Presence", "/Name", None)]),
            )
        )
        self.assertEqual(e, "!(x?.Name is not null) || (!(x?.Opt is not null))")

    def test_or_connector_joins_the_rules(self):
        e = self.expr(rule("SimpleRule", ("mustBe", "OR", [("Presence", "/Opt", None), ("Presence", "/Name", None)])))
        self.assertIn(" || ", e)

    def test_equal_to_value_on_a_code_compares_with_the_member(self):
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(os.path.join(d, "Codesets"))
            with open(os.path.join(d, "Codesets", "Mode1Code.cs"), "w") as f:
                f.write("public enum Mode1Code\n{\n    Alpha = 1,\n    Beta = 2,\n}\n")
            old, gv.PRIM = gv.PRIM, d + os.sep
            try:
                e = self.expr(rule("SimpleRule", ("mustBe", "AND", [("EqualToValue", "/Mode", "Alpha")])))
                self.assertEqual(e, "x?.Mode == Mode1Code.Alpha")
                with self.assertRaises(gv.Unsupported):  # a literal that is not a member is reported, not guessed
                    self.expr(rule("SimpleRule", ("mustBe", "AND", [("EqualToValue", "/Mode", "Gamma")])))
            finally:
                gv.PRIM = old

    def test_number_of_occurrences_and_sum_of(self):
        e = self.expr(rule("SimpleRule", ("mustBe", "AND", [("EqualToValue", "/Name", "number of occurrences of Coll")])))
        self.assertIn(".Count()", e)

    def test_an_unknown_member_is_reported_not_guessed(self):
        with self.assertRaises(gv.Unsupported):
            self.expr(rule("SimpleRule", ("mustBe", "AND", [("Presence", "/Nope", None)])))

    def test_an_unknown_rule_type_is_reported_not_guessed(self):
        with self.assertRaises(gv.Unsupported):
            self.expr(rule("SimpleRule", ("mustBe", "AND", [("SomethingNew", "/Name", None)])))


class PathTests(unittest.TestCase):
    def test_segments(self):
        self.assertEqual(gv.segs("/A/B[*]/C[1]/@Currency"), [("A", None), ("B", "*"), ("C", "1"), ("@Currency", None)])

    def test_a_segment_that_is_not_a_name_is_unsupported(self):
        with self.assertRaises(gv.Unsupported):
            gv.segs("/A/b c")


if __name__ == "__main__":
    unittest.main()
