"""Tests of generate_validators.py on a small model (no network, no other repository).

    python3 -m unittest -q test_generator        (from this folder)
"""
import os
import json
import tempfile
import unittest
from collections import OrderedDict

import generate_validators as gv
import rules_ir as ri

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
                Kind=("IKind", True, False),
            ),
            "IB": OrderedDict(X=("Max35Text", True, False), D=("ISODate", True, False)),
            "IC": OrderedDict(),
            "IKind": OrderedDict(),
            "IE": OrderedDict(
                Country=("CountryCode", True, False),
                Purpose=("ExternalPurpose9Code", False, False),
                Others=("ExternalPurpose9Code", False, True),
            ),
        }
        self.structs = {"Max35Text", "ISODate"}
        self.enums = {"Mode1Code"}
        self.hand = {}
        self.ext_codes = {"CountryCode", "ExternalPurpose9Code"}

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


class RuleBase(unittest.TestCase):
    def setUp(self):
        self.g = gv.Gen(FakeModel())

    def expr(self, xml):
        kind, must, cond = gv.parse_rule(xml)
        body = self.g.section("x", "IA", must)
        return body if cond is None else f"!({self.g.section('x', 'IA', cond)}) || ({body})"


class RuleTests(RuleBase):

    def test_absence_of_every_item_is_a_negation_inside_the_quantifier(self):
        # "no item has X" is All(item has no X), not "not all items have X"
        e = self.expr(rule("SimpleRule", ("mustBe", "AND", [("Absence", "/Coll[*]/X", None)])))
        self.assertEqual(e, "(x?.Coll ?? []).All(i1 => !(i1?.X is not null))")

    def test_absence_without_an_index_means_no_item_has_it(self):
        e = self.expr(rule("SimpleRule", ("mustBe", "AND", [("Absence", "/Coll/X", None)])))
        self.assertEqual(e, "(x?.Coll ?? []).All(i1 => !(i1?.X is not null))")

    def test_presence_of_every_item(self):
        # every item has an X, and there is an item: with no item at all, X is not present
        e = self.expr(rule("SimpleRule", ("mustBe", "AND", [("Presence", "/Coll[*]/X", None)])))
        self.assertEqual(e, "((x?.Coll ?? []).All(i1 => i1?.X is not null)) && ((x?.Coll ?? []).Any(i2 => i2?.X is not null))")

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

    def test_the_phrases_the_data_uses_for_a_count_are_counts(self):
        for phrase in ("Number Occurrences Coll", "number occurrences Coll", "number of occurrences of Coll"):
            e = self.expr(rule("SimpleRule", ("mustBe", "AND", [("EqualToValue", "/Name", phrase)])))
            self.assertIn(".Count()", e, phrase)

    def test_a_phrase_that_describes_the_rule_is_reported_not_compared(self):
        # "Branch of DebtorAgent" is a description in the data; compared literally it would refuse every message
        with self.assertRaises(gv.Unsupported):
            self.expr(rule("SimpleRule", ("mustBe", "AND", [("EqualToValue", "/Name", "Branch of DebtorAgent")])))

    def test_the_specifications_own_misspellings_are_read_as_the_member(self):
        self.assertEqual(gv.segs("/TransactionInformation/ReversedInterbankSttlementAmount")[1][0], "ReversedInterbankSettlementAmount")

    def test_the_first_item_on_the_right_of_a_comparison(self):
        e = self.expr(rule("SimpleRule", ("mustBe", "AND", [("EqualToNode", "/Name", "/Coll[1]/X")])))
        self.assertIn("x?.Coll?.Skip(0).FirstOrDefault()?.X", e)

    def test_every_item_on_the_right_of_a_comparison_is_reported(self):
        with self.assertRaises(gv.Unsupported):
            self.expr(rule("SimpleRule", ("mustBe", "AND", [("EqualToNode", "/Name", "/Coll[*]/X")])))

    def test_substring_of_a_value(self):
        e = self.expr(rule("SimpleRule", ("mustBe", "AND", [("DifferentFromValue", "substring(/Name,1,8)", "pacs.003")])))
        self.assertEqual(e, '!RuleOps.IsText(RuleOps.Substring(x?.Name, 1, 8), "pacs.003")')

    def test_a_code_written_as_its_value_is_the_member_that_has_it(self):
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(os.path.join(d, "Codesets"))
            with open(os.path.join(d, "Codesets", "Mode1Code.cs"), "w") as f:
                f.write('public enum Mode1Code\n{\n    [EnumMember(Value = "ALFA")]\n    Alpha = 1,\n    [EnumMember(Value = "BETA")]\n    Beta = 2,\n}\n')
            old, gv.PRIM = gv.PRIM, d + os.sep
            try:
                e = self.expr(rule("SimpleRule", ("mustBe", "AND", [("EqualToValue", "/Mode", "BETA")])))
            finally:
                gv.PRIM = old
        self.assertEqual(e, "x?.Mode == Mode1Code.Beta")

    def test_an_unknown_member_is_reported_not_guessed(self):
        with self.assertRaises(gv.Unsupported):
            self.expr(rule("SimpleRule", ("mustBe", "AND", [("Presence", "/Nope", None)])))

    def test_an_unknown_rule_type_is_reported_not_guessed(self):
        with self.assertRaises(gv.Unsupported):
            self.expr(rule("SimpleRule", ("mustBe", "AND", [("SomethingNew", "/Name", None)])))


class VariantTests(RuleBase):
    """A rule that names the alternative of a choice (`Kind/Code`) reads it as `Kind as Variant`, and its Value."""

    def setUp(self):
        super().setUp()
        real = self.g.variant
        self.g.variant = lambda itype, name: ("V|Kind.ICode|Mode1Code", True, False) if (itype, name) == ("IKind", "Code") else real(itype, name)

    def test_presence_of_an_alternative_is_a_cast(self):
        e = self.expr(rule("SimpleRule", ("mustBe", "AND", [("Presence", "/Kind/Code", None)])))
        self.assertEqual(e, "(x?.Kind as BeneficialStrategies.Iso20022.Choices.Kind.ICode) is not null")

    def test_a_value_of_an_alternative_is_compared_by_its_Value(self):
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(os.path.join(d, "Codesets"))
            with open(os.path.join(d, "Codesets", "Mode1Code.cs"), "w") as f:
                f.write("public enum Mode1Code\n{\n    Alpha = 1,\n}\n")
            old, gv.PRIM = gv.PRIM, d + os.sep
            try:
                e = self.expr(rule("SimpleRule", ("mustBe", "AND", [("EqualToValue", "/Kind/Code", "Alpha")])))
                self.assertEqual(e, "(x?.Kind as BeneficialStrategies.Iso20022.Choices.Kind.ICode)?.Value == Mode1Code.Alpha")
            finally:
                gv.PRIM = old

    def test_an_alternative_that_does_not_exist_is_reported(self):
        with self.assertRaises(gv.Unsupported):
            self.expr(rule("SimpleRule", ("mustBe", "AND", [("Presence", "/Kind/Nope", None)])))


class ExternalCodeTests(unittest.TestCase):
    """A member whose type is an open code is checked by the validator of its code set, which is injected."""

    def emit(self):
        m = FakeModel()
        m.hand = {"CountryCode": ("CountryCodeValidator", "Codesets")}  # a hand-written one; the other is generated
        e = {
            "name": "E",
            "children": [
                {"name": "Country", "xmlElementName": "messageElement", "minOccurs": "0", "maxOccurs": "1"},
                {"name": "Purpose", "xmlElementName": "messageElement", "minOccurs": "1", "maxOccurs": "1"},
                {"name": "Others", "xmlElementName": "messageElement", "minOccurs": "0"},
            ],
        }
        g = gv.Gen(m)
        report = {k: [] for k in ("no_interface", "mismatch", "prose_only", "guidelines", "unsupported", "generated_rules")}
        return g, gv.emit_type(g, e, report)[1]

    def test_each_open_code_member_is_checked_by_an_injected_validator(self):
        g, code = self.emit()
        self.assertIn("IValidator<CountryCode> countryCodeValidator", code)
        self.assertIn("IValidator<ExternalPurpose9Code> externalPurpose9CodeValidator", code)
        self.assertIn("When(x => x.Country is not null, () => RuleFor(x => x.Country!.Value).SetValidator(countryCodeValidator!));", code)
        self.assertIn("RuleFor(x => x.Purpose).SetValidator(externalPurpose9CodeValidator!);", code)
        self.assertIn("RuleForEach(x => x.Others).SetValidator(externalPurpose9CodeValidator!);", code)
        self.assertEqual(g.ext_used, {"CountryCode", "ExternalPurpose9Code"})

    def test_the_default_constructor_uses_the_hand_written_validator_or_the_generated_one(self):
        _, code = self.emit()
        self.assertIn("new BeneficialStrategies.Iso20022.Messages.Validation.CodesetValidators.CountryCodeValidator()", code)
        self.assertIn("new ExternalPurpose9CodeValidator()", code)

    def test_a_required_code_is_also_required_to_have_a_value(self):
        _, code = self.emit()
        self.assertIn("RuleFor(x => x.Purpose).NotDefaultValue()", code)


class HandWrittenRuleTests(unittest.TestCase):
    """A rule that is not generated is written by hand, next to the validator, and the generator finds it there."""

    ENTITY = {
        "name": "E",
        "children": [
            {"name": "Name", "xmlElementName": "messageElement", "minOccurs": "1", "maxOccurs": "1"},
            {"name": "ProseRule", "xmlElementName": "constraint", "definition": "Name must be what the prose says."},
            {"name": "SomeGuideline", "xmlElementName": "constraint", "definition": "Advice."},
        ],
    }

    def emit(self, rules_dir):
        old, gv.RULES_DIRS = gv.RULES_DIRS, [rules_dir]
        try:
            m = FakeModel()
            m.ifaces["IE"] = OrderedDict(Name=("Max35Text", False, False))
            report = {k: [] for k in ("no_interface", "mismatch", "prose_only", "guidelines", "unsupported", "pending", "generated_rules")}
            return report, gv.emit_type(gv.Gen(m), self.ENTITY, report)[1]
        finally:
            gv.RULES_DIRS = old

    def test_a_prose_rule_with_no_hand_written_rule_is_pending(self):
        with tempfile.TemporaryDirectory() as d:
            report, code = self.emit(d)
        self.assertEqual(report["pending"], ["E.ProseRule"])
        self.assertIn("ProseRule: NOT IMPLEMENTED", code)
        self.assertIn("public partial class EValidator", code)
        self.assertIn("AddHandWrittenRules();", code)
        self.assertIn("partial void AddHandWrittenRules();", code)

    def test_a_prose_rule_found_in_the_rules_file_is_implemented(self):
        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(d, "EValidator.Rules.cs"), "w") as f:
                f.write('public partial class EValidator { partial void AddHandWrittenRules() { RuleFor(x => x).Must(x => true).WithName("ProseRule"); } }')
            report, code = self.emit(d)
        self.assertEqual(report["pending"], [])
        self.assertIn("ProseRule: implemented by hand in EValidator.Rules.cs", code)

    def test_a_guideline_is_a_comment_and_is_not_pending(self):
        with tempfile.TemporaryDirectory() as d:
            report, code = self.emit(d)
        self.assertNotIn("E.SomeGuideline", report["pending"])
        self.assertIn("SomeGuideline: a guideline of the specification", code)


class TranslationTests(unittest.TestCase):
    """A rule given in prose is read once, kept in translations/, and applied to every type that has the same text."""

    PROSE = "If Name is present, then Coll must not have an X."
    ENTITY = {
        "name": "E",
        "children": [{"name": "Name", "xmlElementName": "messageElement", "minOccurs": "1", "maxOccurs": "1"},
                     {"name": "ProseRule", "xmlElementName": "constraint", "definition": "  If Name is present,\n then Coll must not have an X. "}],
    }

    def translation(self, path):
        return {"rule": "ProseRule", "text": self.PROSE, "reading": "r",
                "rules": [{"when": {"rules": [["Presence", "/Name"]]}, "must": {"rules": [["Absence", path]]}}]}

    def emit(self, translation, text_changed=False):
        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(d, gv.text_key("ProseRule", self.PROSE) + ".json"), "w") as f:
                json.dump(translation, f)
            old, ri.TRANSLATIONS_DIR, gv.RULES_DIRS = ri.TRANSLATIONS_DIR, d, [d]
            try:
                m = FakeModel()
                m.ifaces["IE"] = OrderedDict(Name=("Max35Text", False, False), Coll=("IB", False, True))
                entity = json.loads(json.dumps(self.ENTITY))
                if text_changed:
                    entity["children"][1]["definition"] += " (changed)"
                report = {k: [] for k in ("no_interface", "mismatch", "prose_only", "guidelines", "unsupported", "pending", "generated_rules", "translated_rules")}
                return report, gv.emit_type(gv.Gen(m), entity, report)[1]
            finally:
                ri.TRANSLATIONS_DIR, gv.RULES_DIRS = old, []

    def test_the_translation_becomes_a_rule_and_says_where_it_comes_from(self):
        report, code = self.emit(self.translation("/Coll[*]/X"))
        self.assertEqual(report["pending"], [])
        self.assertEqual(report["translated_rules"], ["E.ProseRule"])
        self.assertIn("(the rule is read from the prose (translations/ProseRule.", code)
        self.assertIn(".Must(x => !(x?.Name is not null) || ((x?.Coll ?? []).All(i1 => !(i1?.X is not null))))", code)
        self.assertNotIn("partial", code)

    def test_a_translation_that_does_not_fit_the_type_leaves_the_rule_pending(self):
        report, code = self.emit(self.translation("/Nope/X"))
        self.assertEqual(report["pending"], ["E.ProseRule"])
        self.assertIn("does not fit this type", code)

    def test_a_change_in_the_text_of_the_specification_is_not_silently_translated(self):
        report, _ = self.emit(self.translation("/Coll[*]/X"), text_changed=True)
        self.assertEqual(report["pending"], ["E.ProseRule"])

    def test_a_rule_without_a_translation_gets_a_stub_named_as_the_generator_looks_for_it(self):
        with tempfile.TemporaryDirectory() as empty, tempfile.TemporaryDirectory() as out:
            old, ri.TRANSLATIONS_DIR, ri.SCAFFOLD_DIR = ri.TRANSLATIONS_DIR, empty, out
            try:
                m = FakeModel()
                m.ifaces["IE"] = OrderedDict(Name=("Max35Text", False, False), Coll=("IB", False, True))
                for name in ("E", "F"):  # the same text in two types: one file
                    entity = json.loads(json.dumps(self.ENTITY))
                    entity["name"] = name
                    m.ifaces["I" + name] = m.ifaces["IE"]
                    report = {k: [] for k in ("no_interface", "mismatch", "prose_only", "guidelines", "unsupported", "pending", "generated_rules", "translated_rules")}
                    gv.emit_type(gv.Gen(m), entity, report)
            finally:
                ri.TRANSLATIONS_DIR, ri.SCAFFOLD_DIR = old, None
            files = os.listdir(out)
            self.assertEqual(files, [gv.text_key("ProseRule", self.PROSE) + ".json"])
            stub = json.load(open(os.path.join(out, files[0])))
            self.assertEqual((stub["first_seen_in"], stub["also_in"], stub["rules"], stub["text"]), ("E", ["F"], [], self.PROSE))
            self.assertEqual([x["name"] for x in stub["members"]], ["Name"])

    def test_the_ir_of_a_type_is_plain_data_with_the_expression_and_the_reading(self):
        entity = json.loads(json.dumps(self.ENTITY))
        entity["children"].append({"name": "ExprRule", "xmlElementName": "constraint", "definition": "Name must be present.",
                                   "attributes": {"expression": "<r><SimpleRule><mustBe><connector>AND</connector><BooleanRule xmlns:xsi=\"http://www.w3.org/2001/XMLSchema-instance\" xsi:type=\"Presence\"><leftOperand>/Name</leftOperand></BooleanRule></mustBe></SimpleRule></r>"}})
        entity["children"].append({"name": "SomeGuideline", "xmlElementName": "constraint", "definition": "Advice."})
        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(d, gv.text_key("ProseRule", self.PROSE) + ".json"), "w") as f:
                json.dump(self.translation("/Coll[*]/X"), f)
            old, ri.TRANSLATIONS_DIR = ri.TRANSLATIONS_DIR, d
            try:
                recs = json.loads(json.dumps(ri.type_rules(entity)))  # nothing in it that JSON cannot carry
            finally:
                ri.TRANSLATIONS_DIR = old
        prose, expr, guide = recs
        self.assertEqual(prose["translation"]["rules"][0]["must"]["rules"], [["Absence", "/Coll[*]/X"]])
        self.assertIsNone(prose["expression"])
        self.assertEqual(expr["expression"]["rule"]["must"], {"connector": "AND", "rules": [["Presence", "/Name", None]]})
        self.assertEqual(expr["expression"]["rule"]["kind"], "SimpleRule")
        self.assertTrue(guide["guideline"])

    def test_the_same_value_in_all_items_ignores_absent_values(self):
        g = gv.Gen(FakeModel())
        e = g.section("x", "IA", ("AND", [("SameInAll", "/Coll[*]/X", None)]))
        self.assertEqual(e, "RuleOps.AllSame((x?.Coll ?? []).Select(i1 => i1?.X))")


class TranslationFilesTests(unittest.TestCase):
    """The files in translations/ are data that a generator run trusts, so they are checked as such."""

    def files(self):
        return sorted(f for f in os.listdir(ri.TRANSLATIONS_DIR) if f.endswith(".json"))

    def test_each_file_is_named_by_its_rule_and_the_hash_of_its_text(self):
        for f in self.files():
            with open(os.path.join(ri.TRANSLATIONS_DIR, f), encoding="utf-8") as fh:
                t = json.load(fh)
            self.assertEqual(f, gv.text_key(t["rule"], t["text"]) + ".json", f)

    def test_each_file_says_what_it_is_or_why_it_is_not_a_reading(self):
        for f in self.files():
            with open(os.path.join(ri.TRANSLATIONS_DIR, f), encoding="utf-8") as fh:
                t = json.load(fh)
            self.assertTrue(t.get("rules") or t.get("known_issue") or t.get("hand"), f)
            if t.get("rules"):
                self.assertTrue(t.get("reading"), f)

    def test_each_reading_uses_only_the_rule_types_the_generator_knows(self):
        known = {"Presence", "Absence", "EqualToValue", "DifferentFromValue", "EqualToNode", "DifferentFromNode", "WithInList",
                 "NotWithInList", "SameInAll", "CountEquals", "IsBranchOf"}
        for f in self.files():
            with open(os.path.join(ri.TRANSLATIONS_DIR, f), encoding="utf-8") as fh:
                raw = json.load(fh)
            for r in raw.get("rules", []) + [x for a in raw.get("alternatives", []) for x in a["rules"]]:
                for sec in ("must", "when", "eachWhen"):
                    for rule in (r.get(sec) or {"rules": []})["rules"]:
                        self.assertIn(rule[0], known, f)


class ChoiceTests(unittest.TestCase):
    """A choice is validated alternative by alternative, from the variant interfaces of the model."""

    def test_each_alternative_gets_its_value_validated(self):
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(os.path.join(d, "Choices", "XChoice"))
            with open(os.path.join(d, "Choices", "XChoice", "IAlpha.cs"), "w") as f:
                f.write("public interface IAlpha : IXChoice, IIsoChoiceVariant\n{\n    IB Value { get; }\n    IB? Extra { get; }\n}\n")
            with open(os.path.join(d, "Choices", "XChoice", "IBeta.cs"), "w") as f:
                f.write("public interface IBeta : IXChoice, IIsoChoiceVariant\n{\n    Max35Text Value { get; }\n}\n")
            old, gv.MSGS = gv.MSGS, d + os.sep
            try:
                g = gv.Gen(FakeModel())
                cls, code = gv.emit_choice(g, {"name": "XChoice"}, {"mismatch": []})
            finally:
                gv.MSGS = old
        self.assertEqual(cls, "XChoice_Validator")
        self.assertIn("new InlineValidator<BeneficialStrategies.Iso20022.Choices.XChoice.IAlpha>()", code)
        self.assertIn("alphaVariantValidator.RuleFor(x => x.Value).NotNull()", code)  # required: not nullable on the interface
        self.assertIn("alphaVariantValidator.RuleFor(x => x.Value).SetValidator(bValidator!);", code)
        self.assertIn("alphaVariantValidator.When(x => x.Extra is not null", code)  # optional: only when present
        self.assertIn("betaVariantValidator.RuleFor(x => x.Value).NotDefaultValue()", code)
        self.assertIn("this.SetVariantValidators", code)


class PathTests(unittest.TestCase):
    def test_segments(self):
        self.assertEqual(gv.segs("/A/B[*]/C[1]/@Currency"), [("A", None), ("B", "*"), ("C", "1"), ("@Currency", None)])

    def test_a_segment_that_is_not_a_name_is_unsupported(self):
        with self.assertRaises(gv.Unsupported):
            gv.segs("/A/b c")


if __name__ == "__main__":
    unittest.main()
