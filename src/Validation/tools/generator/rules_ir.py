"""
The front end of the generator: what the specification says about the rules of a type, in terms that do not depend on a
programming language. A back end (the C# one is generate_validators.py) turns this into code; another language needs only its own.

    type_rules(entity) -> [record]    one record per constraint of a type (a message, component or choice of the census)

A record is plain data (dicts, lists, strings: it is what `--ir DIR` writes as JSON):

    {"name": "SomeRule", "text": "the rule as the specification words it",
     "guideline": false,                      a guideline is not a rule to check (it is credited to the layer that shows the data)
     "expression": null                       the specification gives no expression (the rule is in prose)
                 | {"rule": R}                the specification's expression, as a rule R
                 | {"error": "why"},          the expression is not a rule definition at all (it is text)
     "translation": null | T}                 the reading of the prose, kept in translations/ (see the README)

A rule R is {"kind": "SimpleRule" | "ComplexRule", "must": S, "when": S | null, "each": "/Collection" | null, "eachWhen": S | null}
with S = {"connector": "AND" | "OR", "rules": [[operator, left, right?], ...]}. The operators are those of the specification
(Presence, Absence, EqualToValue, DifferentFromValue, EqualToNode, DifferentFromNode, WithInList, NotWithInList) and ours
(SameInAll, CountEquals, IsBranchOf); their meaning is in the README. A translation T is the file of translations/ as it is:
{"file", "rule", "text", "reading", "rules": [R], "alternatives": [{"rules": [R]}], "lenient_codes", "vacuous_without_condition_element",
"known_issue", "hand"}. Which of several readings fits a type (an alternative where the element is elsewhere) is for the back end to
decide, as it depends on how the type is laid out in the language.
"""
import hashlib
import json
import os
import re
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
XSI = "{http://www.w3.org/2001/XMLSchema-instance}type"
TRANSLATIONS_DIR = os.path.join(HERE, "translations")  # the readings of the rules that are in prose
SCAFFOLD_DIR = None  # --scaffold: where the stubs of the rules that have no translation are written


def norm(s):
    return re.sub(r"\s+", " ", s or "").strip()


def parse_rule(xml):
    """the specification's expression: (kind, (connector, [(operator, left, right)]), the same for the condition or None)"""
    root = ET.fromstring(xml)
    rule = root[0]
    kind = rule.get(XSI) or rule.tag

    def section(tag):
        s = rule.find(tag)
        if s is None:
            return None
        conn = (s.findtext("connector") or "AND").strip()
        brs = []
        for br in s.findall("BooleanRule"):
            brs.append((br.get(XSI), (br.findtext("leftOperand") or "").strip(), (br.findtext("rightOperand") or "").strip() or None))
        return conn, brs

    return kind, section("mustBe"), section("onCondition")


def rule_of_expression(xml):
    """the expression as a rule R of the record"""
    kind, must, cond = parse_rule(xml)
    def sec(s):
        return None if s is None else {"connector": s[0], "rules": [[t, l, r] for t, l, r in s[1]]}
    return {"kind": kind, "must": sec(must), "when": sec(cond), "each": None, "eachWhen": None}


def text_key(name, prose):
    return f"{name}.{hashlib.sha1(prose.encode('utf-8')).hexdigest()[:8]}"


def load_translation(name, prose):
    """The reading of a rule that the specification gives in prose, written once from its text (translations/<Rule>.<hash>.json).
    The key is the name and the text of the rule, so a change in the specification's text makes the translation not apply
    (the rule is pending again) instead of silently applying to a rule that has changed."""
    f = os.path.join(TRANSLATIONS_DIR, text_key(name, prose) + ".json")
    if not os.path.exists(f):
        return None
    with open(f, encoding="utf-8") as fh:
        t = json.load(fh)
    t["file"] = os.path.basename(f)
    return t


def scaffold(outdir, rule, prose, type_name, elems):
    """Writes the stub of a translation for a rule that is in prose and has none (<Rule>.<hash>.json, the name the generator looks for).
    The stub has the exact text and the members of the type to read it against, and an empty `rules`: it is filled in by a person
    (see the README), reviewed, and moved to translations/. The members are of the first type found; the same text in another type
    is listed under `also_in`, and one file serves them all."""
    os.makedirs(outdir, exist_ok=True)
    f = os.path.join(outdir, text_key(rule, prose) + ".json")
    members = [{"name": c["name"], "min": c.get("minOccurs", "1"), "max": c.get("maxOccurs", "n")} for c in elems]
    if os.path.exists(f):
        with open(f, encoding="utf-8") as fh:
            stub = json.load(fh)
        if type_name not in stub["also_in"] and type_name != stub["first_seen_in"]:
            stub["also_in"].append(type_name)
    else:
        stub = {"rule": rule, "text": prose, "reading": "", "first_seen_in": type_name, "also_in": [], "members": members, "rules": []}
    with open(f, "w", encoding="utf-8") as fh:
        json.dump(stub, fh, indent=1)
        fh.write("\n")


def type_rules(e):
    """the records of the constraints of a type (see the top of this file)"""
    elems = [c for c in e.get("children", []) if c.get("xmlElementName") in ("messageElement", "messageBuildingBlock")]
    out = []
    for c in e.get("children", []):
        if c.get("xmlElementName") != "constraint":
            continue
        name = c["name"]
        ex = c.get("attributes", {}).get("expression")
        prose = norm(c.get("definition"))
        rec = {"name": name, "text": prose, "guideline": False, "expression": None, "translation": None}
        if ex:
            try:
                rec["expression"] = {"rule": rule_of_expression(ex)}
            except ET.ParseError:
                rec["expression"] = {"error": "the expression is text, not a rule definition"}
        elif name.endswith("Guideline"):
            rec["guideline"] = True
            out.append(rec)
            continue
        rec["translation"] = load_translation(name, prose)
        if not ex and rec["translation"] is None and SCAFFOLD_DIR:
            scaffold(SCAFFOLD_DIR, name, prose, e["name"], elems)
        out.append(rec)
    return out
