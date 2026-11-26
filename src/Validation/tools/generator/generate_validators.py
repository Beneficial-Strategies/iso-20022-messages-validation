#!/usr/bin/env python3
"""
Prototype generator: C# FluentValidation validators for ISO 20022 interfaces, from the specification.

    python3 generate_validators.py --census DIR --message pacs.008.001.14 --out DIR
                                   [--messages PATH] [--primitives PATH] [--validators PATH]

Inputs: the pages of the specification (see README.md: the members of every type with their
multiplicities, and the constraints with their RuleDefinition expressions), and the interfaces of
iso-20022-messages (the names and types of the members, to write each path as C# that compiles).
Output: one .cs file per type in the reach of the message, RuleOps.cs and CodeLists.cs (the few
helpers the rules read through), and report.json (what was generated, what could not be).

Rule semantics (the reading of the RuleDefinition language used here, to be checked against the hand-written validators):
  * SimpleRule: mustBe always holds. ComplexRule: if onCondition holds, mustBe holds.
  * the connector (AND/OR) of a section joins its BooleanRules.
  * Presence / Absence of a path: the element (or, for a collection, any element) is there / is not.
  * a path with [*]: the BooleanRule must hold for every occurrence; [1]: the first occurrence.
  * the paths are the element names, as the interfaces name their members; @Currency is the Currency of an amount.
"""
import argparse
import glob
import hashlib
import json
import os
import re
import sys
import xml.etree.ElementTree as ET
from collections import OrderedDict

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
# Set by main(): the pages of the specification, and the repositories the model is read from.
CENSUS = None
MSGS = None
PRIM = None
RULES_DIRS = []  # where the hand-written rules (<Type>Validator.Rules.cs) are
VAL = os.path.join(REPO_ROOT, "src", "Validation", "Validators") + os.sep
XSI = "{http://www.w3.org/2001/XMLSchema-instance}type"


# ----------------------------------------------------------------------------- inputs
def load_census():
    idx = {}
    for p in ("msg", "cc", "mc"):
        for f in sorted(glob.glob(os.path.join(CENSUS, f"{p}_*.json"))):
            for e in json.load(open(f, encoding="utf-8"))["data"]["children"]:
                idx[e["id"]] = e
    return idx


def parse_props(text):
    """the members of an interface file: name -> (type text without ?, nullable, collection)"""
    props = OrderedDict()
    for line in text.splitlines():
        line = line.strip()
        pm = re.match(r"^([\w<>\.\?, ]+?)\s+(\w+)\s*\{\s*get;\s*\}$", line)
        if pm and not line.startswith("["):
            t, name = pm.group(1).strip(), pm.group(2)
            nullable = t.endswith("?")
            t = t.rstrip("?")
            coll = re.match(r"(?:IEnumerable|IReadOnlyList|IReadOnlyCollection|IList|ICollection)<(.+)>$", t)
            if coll:
                t, coll = coll.group(1).rstrip("?"), True
            props[name] = (t, nullable, bool(coll))
    return props


def load_interfaces():
    """interface name -> OrderedDict(member -> (type text without ?, nullable, collection))"""
    out = {}
    for f in glob.glob(MSGS + "**/I*.cs", recursive=True):
        s = open(f, encoding="utf-8").read()
        m = re.search(r"public interface (I\w+)", s)
        if not m:
            continue
        props = parse_props(s)
        out[m.group(1)] = props
    return out


def grep_names(root, pattern):
    import subprocess

    r = subprocess.run(f'grep -rhoE "{pattern}" {root}', shell=True, capture_output=True, text=True).stdout
    return set(re.findall(r"(?:struct|enum) (\w+)", r))


def enum_members(name):
    if PRIM is None:
        return None
    for f in glob.glob(PRIM + f"Codesets/{name}.cs"):
        with open(f, encoding="utf-8") as fh:
            s = fh.read()
        body = s[s.index("enum " + name):]
        return set(re.findall(r"^\s*(\w+)\s*(?:=|,)", body, re.M))
    return None


def enum_values(name):
    """the code (the value in the XML) -> the name of the member, for an enum of the primitives"""
    if PRIM is None:
        return {}
    for f in glob.glob(PRIM + f"Codesets/{name}.cs"):
        with open(f, encoding="utf-8") as fh:
            s = fh.read()
        body = s[s.index("enum " + name):]
        return dict(re.findall(r'\[EnumMember\(Value = "([^"]+)"\)\][\s\S]*?^\s*(\w+)\s*(?:=|,)', body, re.M))
    return {}


def open_codes():
    """The code types whose values come from outside the model (IIsoExternalCode): a value is checked against a registry."""
    out = set()
    for f in glob.glob(PRIM + "Codesets/*.cs"):
        with open(f, encoding="utf-8") as fh:
            if "IIsoExternalCode" in fh.read():
                out.add(os.path.basename(f)[:-3])
    return out


def hand_validators():
    """validated interface name -> (validator class, namespace folder)"""
    out = {}
    for f in glob.glob(VAL + "*/*.cs"):
        s = open(f, encoding="utf-8").read()
        m = re.search(r"class (\w+)\s*:\s*(?:ExternalCodeset)?AbstractValidator<([\w\.]+)>", s)
        if m:
            out[m.group(2).split(".")[-1]] = (m.group(1), os.path.basename(os.path.dirname(f)))
    return out


# ----------------------------------------------------------------------------- the model
class Model:
    def __init__(self):
        self.idx = load_census()
        self.ifaces = load_interfaces()
        self.structs = grep_names(PRIM + " " + MSGS, r"(readonly )?(partial )?struct \w+")
        self.enums = grep_names(PRIM, r"enum \w+")
        self.hand = hand_validators()
        self.ext_codes = open_codes()

    def kind(self, t):
        if t.startswith("V|"):
            return "class"  # a choice variant (see Gen.variant)
        if t in self.ext_codes:
            return "extcode"
        if t in self.ifaces:
            return "choice" if not self.ifaces[t] and self.is_choice(t) else "iface"
        if t in self.enums or t.endswith("Code") and t not in self.structs:
            return "enum" if t in self.enums else "struct"
        if t in self.structs:
            return "struct"
        if t == "bool":
            return "bool"
        return "class"  # amounts, rates (records)

    def is_choice(self, t):
        return os.path.exists(MSGS + f"Choices/{t}.cs")


# ----------------------------------------------------------------------------- rules (IR)
class Unsupported(Exception):
    pass


def parse_rule(xml):
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


# Misspellings in the specification's own expressions (the member of the model is spelled correctly). Each is a mistake of the
# data, not a different element; the list is the whole of what the data has, found by generating every expression.
SPEC_TYPOS = {
    "ReversedInterbankSttlementAmount": "ReversedInterbankSettlementAmount",
    "ReturnedInterbankSttlementAmount": "ReturnedInterbankSettlementAmount",
}


def segs(path):
    parts = [p for p in path.strip("/").split("/") if p]
    out = []
    for p in parts:
        m = re.match(r"^(@?\w+)(?:\[(\*|\d+)\])?$", p)
        if not m:
            raise Unsupported(f"path segment '{p}'")
        out.append((SPEC_TYPOS.get(m.group(1), m.group(1)), m.group(2)))
    return out


class Gen:
    def __init__(self, model):
        self.m = model
        self.uid = 0
        self.lists = {}
        self.ext_used = set()
        self.vacuous_ok = False  # a rule whose condition names an element the type does not have never applies (see build())
        self.lenient_codes = False  # see boolean(): a translation may name codes that an older version of the type lacks

    def var(self):
        self.uid += 1
        return f"i{self.uid}"

    # ---- member access; returns (type, nullable, collection)
    def member(self, cur, itype, name):
        if itype.startswith("V|"):
            if itype.split("|")[2]:  # the alternative holds a Value: its members are the Value's
                itype = itype.split("|")[2]
            else:  # the alternative is a group of elements
                props = self.variant_props(itype)
                if name in props:
                    return props[name]
                raise Unsupported(f"{itype.split('|')[1]} has no member {name}")
        props = self.m.ifaces.get(itype)
        if props is not None and name in props:
            return props[name]
        v = self.variant(itype, name)
        if v is not None:
            return v
        raise Unsupported(f"{itype} has no member {name}")

    def variant(self, itype, name):
        """A choice is an interface with one variant interface per alternative (Choices/<Choice>/I<Name>.cs). An alternative has a
        `Value` (the thing the alternative holds) or, when the alternative is a group of elements, members of its own. The path of a
        rule names the alternative; it is `cur as Variant`."""
        if not self.m.is_choice(itype):
            return None
        f = MSGS + f"Choices/{itype[1:]}/I{name}.cs"
        if not os.path.exists(f):
            return None
        with open(f, encoding="utf-8") as fh:
            vm = re.search(r"^\s*([\w<>\.\?]+)\s+Value\s*\{\s*get;", fh.read(), re.M)
        return (f"V|{itype[1:]}.I{name}|{vm.group(1).rstrip('?') if vm else ''}", True, False)

    def variant_props(self, token):
        """the members of an alternative that has no Value"""
        choice, vname = token.split("|")[1].split(".")
        with open(MSGS + f"Choices/{choice}/{vname}.cs", encoding="utf-8") as fh:
            return parse_props(fh.read())

    def access(self, cur, ctype, name, t):
        """the C# expression of member `name` of `cur`"""
        if t.startswith("V|"):
            return f"({cur} as BeneficialStrategies.Iso20022.Choices.{t.split('|')[1]})"
        if ctype.startswith("V|"):
            return f"{cur}?.Value?.{name}" if ctype.split("|")[2] else f"{cur}?.{name}"
        return f"{cur}?.{name}"

    def unwrap(self, e, t):
        """a variant compared with a value is compared by its Value"""
        if t.startswith("V|") and t.split("|")[2]:
            return f"{e}?.Value", t.split("|")[2]
        return e, t

    def walk(self, root_var, root_type, path, leaf):
        """Writes `leaf(expr, type, collection)` over the path with [*] as all(...)."""
        ss = segs(path)

        def rec(cur, ctype, rest, first):
            if not rest:
                return leaf(cur, ctype, False)
            (name, idx), tail = rest[0], rest[1:]
            if name == "@Currency":
                return leaf(f"{cur}?.Currency", "ActiveCurrencyCode", False)
            if name.startswith("@"):
                raise Unsupported(f"attribute {name}")
            t, nullable, coll = self.member(cur, ctype, name)
            acc = self.access(cur, ctype, name, t)
            if coll:
                if idx == "*":
                    v = self.var()
                    inner = rec(v, t, tail, False)
                    return f"({acc} ?? []).All({v} => {inner})"
                if idx is not None:
                    v = self.var()
                    first_el = f"{acc}?.Skip({int(idx) - 1}).FirstOrDefault()"
                    if not tail:
                        return leaf(first_el, t, False)
                    return rec(first_el, t, tail, False)
                if not tail:
                    return leaf(acc, t, True)
                v = self.var()
                inner = rec(v, t, tail, False)
                return f"({acc} ?? []).Any({v} => {inner})"
            return rec(acc, t, tail, False)

        return rec(root_var, root_type, ss, True)

    def expr_of(self, root_var, root_type, path):
        """a single (unquantified) value expression and its type"""
        ss = segs(path)
        cur, ctype = root_var, root_type
        for name, idx in ss:
            if name == "@Currency":
                return f"{cur}?.Currency", "ActiveCurrencyCode"
            t, nullable, coll = self.member(cur, ctype, name)
            cur = self.access(cur, ctype, name, t)
            if coll:
                if idx is not None and idx.isdigit():
                    cur = f"{cur}?.Skip({int(idx) - 1}).FirstOrDefault()"  # the first item (or n-th)
                elif idx is not None:
                    raise Unsupported("every item on the right of a comparison")
            ctype = t
        return cur, ctype

    def present(self, e, t, coll):
        if coll:
            return f"({e}?.Any() ?? false)"
        if self.m.kind(t) in ("struct", "extcode") and re.match(r"^i\d+$", e):
            return f"RuleOps.Has({e})"  # an element of a collection of structs: it cannot be compared with null
        return f"{e} is not null"

    def every_item(self, x, itype, path):
        """the path with [*] on each collection that has no index"""
        out, ctype = [], itype
        for name, idx in segs(path):
            if name.startswith("@"):
                out.append(name)
                continue
            t, nullable, coll = self.member(x, ctype, name)
            out.append(f"{name}[*]" if coll and idx is None else name + (f"[{idx}]" if idx else ""))
            ctype = t
        return "/" + "/".join(out)

    def values_of(self, x, itype, path):
        """all the values at a path, as an IEnumerable<object?>: [*] (or a collection) spreads into its items"""
        cur, ctype, many = x, itype, False
        for name, idx in segs(path):
            if name == "@Currency":
                return f"{cur}.Select(v => (object?)v?.Currency)" if many else f"new object?[] {{ {cur}?.Currency }}"
            if name.startswith("@"):
                raise Unsupported(f"attribute {name}")
            t, nullable, coll = self.member(cur, ctype, name)
            if not many:
                acc = self.access(cur, ctype, name, t)
                cur, many = (f"({acc} ?? [])", True) if coll else (acc, False)
            else:
                v = self.var()
                inner = self.access(v, ctype, name, t)
                cur = f"{cur}.SelectMany({v} => {inner} ?? [])" if coll else f"{cur}.Select({v} => {inner})"
            ctype = t
        return cur if many else f"new object?[] {{ {cur} }}"

    # ---- BooleanRule -> bool expression over x
    def boolean(self, x, itype, typ, left, right):
        if typ in ("Presence", "Absence"):
            if typ == "Presence":
                every = self.walk(x, itype, left, lambda e, t, c: self.present(e, t, c))
                if "[*]" in left:
                    # "A[*]/B is present" is that every item has a B, and that there is an item: with none, B is not present
                    return f"({every}) && ({self.walk(x, itype, left.replace('[*]', ''), lambda e, t, c: self.present(e, t, c))})"
                return every
            # "absent" is that no occurrence has it: every collection on the way is read as [*] when the path does not say
            return self.walk(x, itype, self.every_item(x, itype, left), lambda e, t, c: f"!({self.present(e, t, c)})")
        if typ == "IsBranchOf":
            # (ours) the institution at the first path is a branch of the one at the second: see RuleOps.IsBranchOf
            return f"RuleOps.IsBranchOf({self.expr_of(x, itype, left)[0]}, {self.expr_of(x, itype, right)[0]})"
        if typ == "CountEquals":
            # (ours) the number of occurrences at the path is the number on the right
            return f"{self.values_of(x, itype, left)}.Count(v => v is not null) == {int(right)}"
        if typ == "SameInAll":
            # (not one of the specification's rule types) the values at the path, and at the second one if there is one, are one value
            both = self.values_of(x, itype, left) + (f".Concat({self.values_of(x, itype, right)})" if right else "")
            return f"RuleOps.AllSame({both})"
        if typ in ("EqualToNode", "DifferentFromNode"):
            rexpr, rtype = self.expr_of(x, itype, right)
            op = "==" if typ == "EqualToNode" else "!="
            return self.walk(x, itype, left, lambda e, t, c: f"{self.unwrap(e, t)[0]} {op} {self.unwrap(rexpr, rtype)[0]}")
        if typ in ("EqualToValue", "DifferentFromValue"):
            neg = typ == "DifferentFromValue"
            agg = re.match(r"^(sum of|number (?:of )?occurrences (?:of )?) ?(/?[\w/\[\]\*@]+)$", right or "", re.I)
            if agg:
                what, p = agg.groups()
                if what.lower().startswith("number"):
                    rhs = f"(({self.expr_of(x, itype, p)[0]}) ?? []).Count()"
                else:
                    ss = segs(p)
                    ct, _, coll = self.member(x, itype, ss[0][0])
                    if not coll or len(ss) != 2:
                        raise Unsupported(f"aggregate {right}")
                    et, _, _ = self.member("t", ct, ss[1][0])
                    sel = f"t?.{ss[1][0]}" + ("?.Amount" if self.m.kind(et) == "class" else "")
                    rhs = f"({x}?.{ss[0][0]} ?? []).Sum(t => (decimal?){sel})"
                lhs_body = self.walk(x, itype, left, lambda e, t, c: f"RuleOps.Number({e}) {'!=' if neg else '=='} {rhs}")
                return lhs_body
            lit = right
            sub = re.match(r"^substring\((.+),\s*(\d+),\s*(\d+)\)$", left)
            if sub and not re.search(r"\s", lit or ""):
                path, a, n = sub.groups()
                return self.walk(x, itype, path, lambda e, t, c: f"{'!' if neg else ''}RuleOps.IsText(RuleOps.Substring({self.unwrap(e, t)[0]}, {a}, {n}), \"{lit}\")")
            if re.search(r"\s", lit or ""):
                # The data has a few expressions whose "value" is a phrase ("Branch of DebtorAgent"): they describe a rule
                # instead of stating it, and compared literally they would refuse every message. Not generated; reported.
                raise Unsupported(f"the expression compares with a phrase, '{lit}', which describes the rule rather than expressing it")
            def cmp(e, t, c):
                e, t = self.unwrap(e, t)
                k = self.m.kind(t)
                if k == "enum":
                    mem = enum_members(t)
                    name = lit
                    if mem is not None and lit not in mem:
                        name = enum_values(t).get(lit)  # the data writes the code (ISSU), the model names the member
                        if name is None and self.lenient_codes:
                            # the rule lists codes of the newest code set; an older version of the type does not have all of them,
                            # and a code that the type cannot hold is never the value (so "equals" is false, "differs from" is true)
                            return "true" if neg else "false"
                        if name is None:
                            raise Unsupported(f"{lit} is not a member of {t}")
                    return f"{e} {'!=' if neg else '=='} {t}.{name}"
                return f"{'!' if neg else ''}RuleOps.IsText({e}, \"{lit}\")"
            return self.walk(x, itype, left, cmp)
        if typ in ("WithInList", "NotWithInList"):
            code = right
            members = enum_members(code)
            if members is None:
                raise Unsupported(f"list {code} is not an enum")
            self.lists[code] = sorted(members)
            body = self.walk(x, itype, left, lambda e, t, c: f"RuleOps.InList({self.unwrap(e, t)[0]}, CodeLists.{code})")
            return body if typ == "WithInList" else f"!({body})"
        raise Unsupported(f"rule type {typ}")

    def section(self, x, itype, sec):
        conn, brs = sec
        parts = [self.boolean(x, itype, t, l, r) for t, l, r in brs]
        if len(parts) == 1:
            return parts[0]
        j = " && " if conn == "AND" else " || "
        return j.join(f"({p})" for p in parts)

    def english(self, sec):
        conn, brs = sec
        w = {"Presence": "{} is present", "Absence": "{} is absent", "EqualToNode": "{} equals {r}", "DifferentFromNode": "{} differs from {r}",
             "IsBranchOf": "{} is a branch of {r}", "SameInAll": "{} is one value in all items (with {r})", "CountEquals": "{} occurs {r} time(s)", "EqualToValue": "{} equals {r}", "DifferentFromValue": "{} differs from {r}", "WithInList": "{} is in {r}", "NotWithInList": "{} is not in {r}"}
        s = [w[t].format(l.strip("/").replace("/", "."), r=(r or "")) for t, l, r in brs]
        return (" " + conn.lower() + " ").join(s)


def cs_str(s):
    return s.replace("\\", "\\\\").replace('"', '\\"')


def norm(s):
    return re.sub(r"\s+", " ", s or "").strip()


# ----------------------------------------------------------------------------- emitting
def code_validator_new(m, t):
    """`new XValidator()`: the hand-written one of the code set if there is one, else the generated one"""
    if t in m.hand and m.hand[t][1] == "Codesets":
        return f"new BeneficialStrategies.Iso20022.Messages.Validation.CodesetValidators.{m.hand[t][0]}()"
    return f"new {t}Validator()"


def emit_code_validator(t):
    return (
        "// Generated by tools/generator/generate_validators.py (prototype). Do not edit: regenerate.\n\nnamespace Gen;\n\n"
        f"/// <summary>Checks a <see cref=\"BeneficialStrategies.Iso20022.Codesets.{t}\"/> against the registry of its code set.</summary>\n"
        f"public class {t}Validator : BeneficialStrategies.Iso20022.Messages.Validation.ExternalCodesetAbstractValidator<BeneficialStrategies.Iso20022.Codesets.{t}>\n{{\n"
        f"    public {t}Validator(BeneficialStrategies.Iso20022.Messages.Validation.IExternalCodeRegistry<BeneficialStrategies.Iso20022.Codesets.{t}> registry)\n        : base(registry) {{ }}\n\n"
        f"    public {t}Validator() {{ }}\n}}\n"
    )


TRANSLATIONS_DIR = os.path.join(HERE, "translations")  # the readings of the rules that are in prose


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
    def rules_of(rs):
        return [
            (r.get("kind", "ComplexRule" if (r.get("when") or r.get("eachWhen")) else "SimpleRule"), section_of(r["must"]),
             section_of(r["when"]) if r.get("when") else None, r.get("each"), section_of(r["eachWhen"]) if r.get("eachWhen") else None)
            for r in rs
        ]

    t["lenient_codes"] = bool(t.get("lenient_codes"))
    t["vacuous"] = bool(t.get("vacuous_without_condition_element"))
    t["rules"] = rules_of(t.get("rules", []))
    # the same rule where the element is somewhere else in another version of the type: tried in order when the first does not fit
    t["alternatives"] = [rules_of(a["rules"]) for a in t.get("alternatives", [])]
    return t


def section_of(spec):
    """{"connector": "AND", "rules": [["Presence", "/A"], ["EqualToValue", "/B", "x"]]} -> (connector, [(type, left, right)])"""
    return (spec.get("connector", "AND"), [(r[0], r[1], r[2] if len(r) > 2 else None) for r in spec["rules"]])


def hand_rules_file(name):
    """the hand-written rules of a type (`<Type>Validator.Rules.cs`, next to the validator), or None"""
    for d in RULES_DIRS:
        for f in glob.glob(os.path.join(d, "**", f"{name}Validator.Rules.cs"), recursive=True):
            return f
    return None


def emit_type(g, e, report):
    m = g.m
    name = e["name"]
    g.uid = 0  # the names of the loop variables start again in each type, so a change elsewhere does not touch this file
    itype = "I" + name
    props = m.ifaces.get(itype)
    if props is None:
        report["no_interface"].append(name)
        return None
    # a few messages of the same name are in two business areas (PaymentStatusReportV02 is in pacs and in pain): the interface is
    # named with its area, and the validator is in the namespace of the area
    area = next((c["name"].split(".")[0] for c in e.get("children", []) if c.get("xmlElementName") == "messageDefinitionIdentifier"), None)
    ns, itype_cs = "Gen", itype
    if area and len(glob.glob(MSGS + f"MessageDefinitions/*/{itype}.cs")) > 1:
        itype_cs = f"BeneficialStrategies.Iso20022.{area}.{itype}"
        ns = f"Gen.{area}"
    # children of kind messageElement / messageBuildingBlock
    elems = [c for c in e.get("children", []) if c.get("xmlElementName") in ("messageElement", "messageBuildingBlock")]
    consts = [c for c in e.get("children", []) if c.get("xmlElementName") == "constraint"]
    child_vals = OrderedDict()  # interface -> param name
    code_vals = OrderedDict()  # external code type -> param name
    lines = []
    mism = report["mismatch"]

    def pname(t):
        return t[1:][0].lower() + t[2:] + "Validator"

    for c in elems:
        mem = c["name"]
        if mem not in props:
            mism.append(f"{name}.{mem}: in the spec, not on the interface")
            continue
        t, nullable, coll = props[mem]
        mn = int(c.get("minOccurs", "1"))
        mxs = c.get("maxOccurs")
        mx = int(mxs) if mxs and mxs.isdigit() else None
        # unbounded collections have no maxOccurs attribute in the census; single ones have "1"
        is_coll_spec = mxs is None or (mx is not None and mx > 1)
        if is_coll_spec != coll:
            mism.append(f"{name}.{mem}: spec collection={is_coll_spec} (max {mxs}), interface collection={coll}")
        if not coll and (mn == 0) != nullable:
            mism.append(f"{name}.{mem}: spec min {mn}, interface nullable={nullable} collection={coll}")
        k = m.kind(t)
        w = f'"{name}.{mem}'
        if coll:
            if mn == 1:
                lines.append(f'RuleFor(x => x.{mem}).NotEmpty().WithMessage({w} must have at least {mn} item(s) ({mn}..{mxs or "n"})."); ')
            elif mn > 1:
                lines.append(f'RuleFor(x => x.{mem}).Must(c => c is not null && c.Count() >= {mn}).WithMessage({w} must have at least {mn} item(s) ({mn}..{mxs or "n"})."); ')
            if mx is not None and mx > 1:
                lines.append(f'RuleFor(x => x.{mem}).Must(c => c is null || c.Count() <= {mx}).WithMessage({w} may have at most {mx} items."); ')
        else:
            if mn >= 1:
                if k in ("iface", "class", "choice"):
                    lines.append(f'RuleFor(x => x.{mem}).NotNull().WithMessage({w} is required (1..1)."); ')
                elif k in ("struct", "extcode"):
                    lines.append(f'RuleFor(x => x.{mem}).NotDefaultValue().WithMessage({w} is required (1..1)."); ')
        if k == "class" and t.endswith("Amount") and not coll:
            lines.append(f'When(x => x.{mem} is not null, () => RuleFor(x => (string)x.{mem}!.Currency).NotEmpty().WithMessage({w}.Currency is required.")); ')
        if k in ("iface", "choice"):
            if t not in child_vals:
                child_vals[t] = pname(t)
            if coll:
                lines.append(f"RuleForEach(x => x.{mem}).SetValidator({child_vals[t]}!);")
            else:
                lines.append(f"RuleFor(x => x.{mem}).SetValidator({child_vals[t]}!);")
        elif k == "extcode":
            # the value is checked against the registry of its code set (live, when the consumer asks for it)
            g.ext_used.add(t)
            code_vals.setdefault(t, t[0].lower() + t[1:] + "Validator")
            v = code_vals[t]
            if coll:
                lines.append(f"RuleForEach(x => x.{mem}).SetValidator({v}!);")
            elif nullable:
                lines.append(f"When(x => x.{mem} is not null, () => RuleFor(x => x.{mem}!.Value).SetValidator({v}!));")
            else:
                lines.append(f"RuleFor(x => x.{mem}).SetValidator({v}!);")

    # constraints
    rule_lines = []
    hand_file = hand_rules_file(name)
    hand_text = ""
    if hand_file:
        with open(hand_file, encoding="utf-8") as fh:
            hand_text = fh.read()
    needs_hand = False  # a rule that is not generated: it is written by hand, in <Type>Validator.Rules.cs

    def by_hand(cname, why, prose):
        """the comment of a rule that is not generated: written by hand (and found there), or not implemented yet"""
        nonlocal needs_hand
        needs_hand = True
        if f'WithName("{cname}")' in hand_text:
            rule_lines.append(f"// {cname}: implemented by hand in {name}Validator.Rules.cs ({why}).")
        else:
            report["pending"].append(f"{name}.{cname}")
            rule_lines.append(f"// {cname}: NOT IMPLEMENTED, to be written by hand in {name}Validator.Rules.cs ({why}).")
        rule_lines.append(f"//   {prose}")
        rule_lines.append("")

    def build(rules):
        """the C# expression of one or more rules, all of which must hold. A rule is (kind, mustBe, onCondition) or, when it is
        about each item of a collection, (kind, mustBe, onCondition, collection, itemCondition): the collection is walked once and
        the condition and the consequence of the item are both read on the same item."""
        parts = []
        g.uid = 0  # the names of the loop variables start again in each rule: a rule reads the same wherever it is
        for r in rules:
            kind, must, cond = r[:3]
            each, each_cond = (r[3], r[4]) if len(r) > 3 else (None, None)
            if g.vacuous_ok and cond is not None:
                try:
                    g.section("x", itype, cond)
                except Unsupported as u:
                    if "has no member" in str(u):
                        continue  # "if X is present then ...", and the type has no X: the rule never applies
                    raise
            if each:
                (name_, idx_), = segs(each)
                ct, _, is_coll = g.member("x", itype, name_)
                v = g.var()
                inner = g.section(v, ct, must)
                if each_cond is not None:
                    inner = f"!({g.section(v, ct, each_cond)}) || ({inner})"
                body = f"(x?.{name_} ?? []).All({v} => {inner})"
                parts.append(body if cond is None else f"!({g.section('x', itype, cond)}) || ({body})")
                continue
            body_must = g.section("x", itype, must)
            parts.append(body_must if (kind == "SimpleRule" or cond is None) else f"!({g.section('x', itype, cond)}) || ({body_must})")
        if not parts:
            return None
        return parts[0] if len(parts) == 1 else " && ".join(f"({p})" for p in parts)

    def reading(rules):
        out = []
        for r in rules:
            kind, must, cond = r[:3]
            each, each_cond = (r[3], r[4]) if len(r) > 3 else (None, None)
            pre = ("if " + g.english(cond) + ": " if cond is not None else "")
            if each:
                pre += f"in each {each.strip('/')}" + (": if " + g.english(each_cond) + ": " if each_cond is not None else ": ")
                out.append(f"{pre}{g.english(must)}")
            else:
                out.append(f"{pre if kind != 'SimpleRule' else ''}{g.english(must)}")
        return "; and ".join(out)

    for c in consts:
        cname = c["name"]
        ex = c.get("attributes", {}).get("expression")
        prose = norm(c.get("definition"))
        tr = load_translation(cname, prose)
        source, rules, why = "the specification's expression", None, None
        if ex:
            try:
                rules = [parse_rule(ex)]
                build(rules)
            except (Unsupported, ET.ParseError) as u:
                rules, why = None, ("the expression is text, not a rule definition" if isinstance(u, ET.ParseError) else str(u))
                report["unsupported"].append(f"{name}.{cname}: {why}")
        else:
            if cname.endswith("Guideline"):
                report["guidelines"].append(f"{name}.{cname}")
                rule_lines.append(f"// {cname}: a guideline of the specification, not a rule to check:")
                rule_lines.append(f"//   {prose}")
                rule_lines.append("")
                continue
            report["prose_only"].append(f"{name}.{cname}")
            why = "the specification gives the rule in prose only"
        if rules is None and tr is not None and tr.get("rules"):
            # written once from the prose, reviewed, and kept in translations/ (see the README)
            first_error = None
            g.lenient_codes = tr["lenient_codes"]
            g.vacuous_ok = tr["vacuous"]
            for candidate in [tr["rules"]] + tr["alternatives"]:
                try:
                    build(candidate)
                    rules, source = candidate, f"read from the prose (translations/{tr['file']})"
                    break
                except Unsupported as u:
                    first_error = first_error or u
            if rules is None:
                g.lenient_codes = g.vacuous_ok = False
                report["unsupported"].append(f"{name}.{cname}: translation {tr['file']}: {first_error}")
                why = f"translation {tr['file']} does not fit this type: {first_error}"
        if rules is None and tr is not None and tr.get("known_issue"):
            # a rule that cannot be checked on the message (it is about meaning, or about another message): not an error, not pending;
            # kept in docs/KnownRuleChallenges.md
            report["known_issues"].append(f"{name}.{cname}")
            rule_lines.append(f"// {cname}: a known issue (docs/KnownRuleChallenges.md), not checked: {tr['known_issue']}")
            rule_lines.append(f"//   {prose}")
            rule_lines.append("")
            continue
        if rules is None and tr is not None and tr.get("hand"):
            why = tr["hand"]  # a rule that is to be written in C#, and why it cannot be a reading
        if rules is None:
            by_hand(cname, why, prose)
            continue
        expr = build(rules)
        g.lenient_codes = g.vacuous_ok = False
        if expr is None:
            report["known_issues"].append(f"{name}.{cname}")
            rule_lines.append(f"// {cname}: never applies to this type: its condition is about an element the type does not have (docs/KnownRuleChallenges.md).")
            rule_lines.append(f"//   {prose}")
            rule_lines.append("")
            continue
        report["generated_rules" if source.startswith("the spec") else "translated_rules"].append(f"{name}.{cname}")
        rule_lines.append(f"// ── {cname} ── {reading(rules)}")
        rule_lines.append(f"// {prose}")
        if not source.startswith("the spec"):
            rule_lines.append(f"// (the rule is {source})")
        rule_lines.append("RuleFor(x => x)")
        rule_lines.append(f"    .Must(x => {expr})")
        rule_lines.append(f'    .WithName("{cname}")')
        rule_lines.append(f'    .WithMessage("{name}: {cs_str(prose)} ({cname}).");')
        rule_lines.append("")

    # class
    cls = f"{name}Validator"
    all_vals = list(child_vals.items()) + list(code_vals.items())
    params = ",\n        ".join(f"IValidator<{t}> {p}" for t, p in all_vals)
    def default_for(t):
        if t in code_vals:
            return code_validator_new(m, t)
        return f"new {t[1:]}{'_' if m.kind(t) == 'choice' else ''}Validator()"

    out = []
    out.append("// Generated by tools/generator/generate_validators.py from the ISO 20022 specification (prototype). Do not edit: regenerate.")
    out.append("")
    out.append(f"namespace {ns};")
    out.append("")
    out.append(f"/// <summary>Validates <see cref=\"{itype_cs}\"/> per the ISO 20022 specification.</summary>")
    out.append(f"public {'partial ' if needs_hand else ''}class {cls} : AbstractValidator<{itype_cs}>")
    out.append("{")
    if all_vals:
        out.append(f"    public {cls}(\n        {params}\n    )")
    else:
        out.append(f"    public {cls}()")
    out.append("    {")
    for l in lines + ([""] if lines and rule_lines else []) + rule_lines:
        out.append(("        " + l) if l else "")
    if needs_hand:
        out.append("        AddHandWrittenRules();")
    out.append("    }")
    if needs_hand:
        out.append("")
        out.append("    /// <summary>The rules of the specification that are written by hand, in <c>" + cls + ".Rules.cs</c>.</summary>")
        out.append("    partial void AddHandWrittenRules();")
    if all_vals:
        out.append("")
        out.append(f"    public {cls}()\n        : this({', '.join(default_for(t) for t, _ in all_vals)}) {{ }}")
    out.append("}")
    return (cls if ns == "Gen" else f"{area}.{cls}"), "\n".join(out) + "\n", list(child_vals)


def emit_choice(g, e, report):
    """A choice is validated variant by variant: the Value of each alternative (and any other member of it) by its own validator."""
    m = g.m
    name = e["name"]
    itype = "I" + name
    g.uid = 0
    folder = MSGS + f"Choices/{name}/"
    variants = sorted(glob.glob(folder + "I*.cs"))
    if not variants:
        report["mismatch"].append(f"{name}: a choice whose alternatives are not on the model")
    vals = OrderedDict()  # interface -> param
    code_vals = OrderedDict()
    blocks = []
    for f in variants:
        vname = os.path.basename(f)[:-3]  # IFinancialInstitutionIdentification
        with open(f, encoding="utf-8") as fh:
            props = parse_props(fh.read())
        var = f"{vname[1:][0].lower()}{vname[2:]}VariantValidator"
        full = f"BeneficialStrategies.Iso20022.Choices.{name}.{vname}"
        rules = []
        for mem, (t, nullable, coll) in props.items():
            k = m.kind(t)
            w = f'"{name}.{vname[1:]}.{mem}'
            if k in ("iface", "choice"):
                vals.setdefault(t, t[1:][0].lower() + t[2:] + "Validator")
                v = vals[t]
                if coll:
                    rules.append(f"{var}.RuleForEach(x => x.{mem}).SetValidator({v}!);")
                elif nullable:
                    rules.append(f"{var}.When(x => x.{mem} is not null, () => {var}.RuleFor(x => x.{mem}).SetValidator({v}!));")
                else:
                    rules.append(f'{var}.RuleFor(x => x.{mem}).NotNull().WithMessage({w} is required (1..1)."); ')
                    rules.append(f"{var}.RuleFor(x => x.{mem}).SetValidator({v}!);")
            elif k == "extcode":
                g.ext_used.add(t)
                code_vals.setdefault(t, t[0].lower() + t[1:] + "Validator")
                v = code_vals[t]
                if coll:
                    rules.append(f"{var}.RuleForEach(x => x.{mem}).SetValidator({v}!);")
                elif nullable:
                    rules.append(f"{var}.When(x => x.{mem} is not null, () => {var}.RuleFor(x => x.{mem}!.Value).SetValidator({v}!));")
                else:
                    rules.append(f'{var}.RuleFor(x => x.{mem}).NotDefaultValue().WithMessage({w} is required (1..1)."); ')
                    rules.append(f"{var}.RuleFor(x => x.{mem}).SetValidator({v}!);")
            elif not nullable and not coll:
                if k == "struct":
                    rules.append(f'{var}.RuleFor(x => x.{mem}).NotDefaultValue().WithMessage({w} is required (1..1)."); ')
                elif k == "class":
                    rules.append(f'{var}.RuleFor(x => x.{mem}).NotNull().WithMessage({w} is required (1..1)."); ')
        blocks.append((var, full, rules))
    all_vals = list(vals.items()) + list(code_vals.items())
    params = ",\n        ".join(f"IValidator<{t}> {p}" for t, p in all_vals)

    def default_for(t):
        if t in code_vals:
            return code_validator_new(m, t)
        return f"new {t[1:]}{'_' if m.kind(t) == 'choice' else ''}Validator()"

    cls = f"{name}_Validator"
    out = ["// Generated by tools/generator/generate_validators.py from the ISO 20022 specification (prototype). Do not edit: regenerate.", "",
           "namespace Gen;", "", f"/// <summary>Validates each alternative of <see cref=\"{itype}\"/>.</summary>",
           f"public class {cls} : AbstractValidator<{itype}>", "{"]
    if all_vals:
        out.append(f"    public {cls}(\n        {params}\n    )")
    else:
        out.append(f"    public {cls}()")
    out.append("    {")
    for var, full, rules in blocks:
        out.append(f"        var {var} = new InlineValidator<{full}>();")
        out.extend("        " + r for r in rules)
        out.append("")
    if blocks:
        out.append("        this.SetVariantValidators(v =>")
        out.append("        {")
        out.extend(f"            v.Add({var});" for var, _, _ in blocks)
        out.append("        });")
    out.append("    }")
    if all_vals:
        out.append("")
        out.append(f"    public {cls}()\n        : this({', '.join(default_for(t) for t, _ in all_vals)}) {{ }}")
    out.append("}")
    return cls, "\n".join(out) + "\n"


RULE_OPS = '''// Generated by tools/generator/generate_validators.py (prototype). The few helpers the generated rules read through.

namespace Gen;

internal static class RuleOps
{
    /// <summary>The value as a number: an amount (its Amount), numeric text, or a number.</summary>
    internal static decimal? Number(object? v) => v switch
    {
        null => null,
        decimal d => d,
        int i => i,
        _ when v.GetType().GetProperty("Amount") is { } p && p.GetValue(v) is decimal a => a,
        _ => decimal.TryParse(v.ToString(), System.Globalization.NumberStyles.Number, System.Globalization.CultureInfo.InvariantCulture, out var n) ? n : null,
    };

    /// <summary>The value, as text, is the literal (case-insensitive: the specification writes booleans in lower case).</summary>
    internal static bool IsText(object? v, string literal) =>
        v is not null && string.Equals(v.ToString(), literal, StringComparison.OrdinalIgnoreCase);

    /// <summary>The value (a code) is one of the codes of another code set, by name.</summary>
    internal static IRuleBuilderOptions<T, TProperty> NotDefaultValue<T, TProperty>(this IRuleBuilder<T, TProperty> rb) where TProperty : struct =>
        rb.Must(v => !EqualityComparer<TProperty>.Default.Equals(v, default));

    /// <summary>The part of the text of the value that starts at position <c>start</c> (the first is 1) and is at most <c>length</c> long.</summary>
    internal static string? Substring(object? v, int start, int length)
    {
        var s = v?.ToString();
        return s is null || start > s.Length ? null : s.Substring(start - 1, Math.Min(length, s.Length - start + 1));
    }

    /// <summary>The values that are there are all one value (an absent value is not a different one).</summary>
    internal static bool AllSame(IEnumerable<object?> values) =>
        values.Where(v => v is not null).Select(v => v!.ToString()).Distinct().Count() <= 1;

    /// <summary>
    /// Whether a financial institution is a branch of another: it is not, only when the two carry the same kind of identifier and the
    /// identifiers differ (a BIC is compared by its first eight characters, its institution; a branch is the rest). With no kind in
    /// common nothing can be said against it, so it is accepted.
    /// </summary>
    internal static bool IsBranchOf(object? branch, object? agent)
    {
        var a = Identifiers(branch);
        var b = Identifiers(agent);
        foreach (var kv in a)
        {
            if (b.TryGetValue(kv.Key, out var other) && !string.Equals(kv.Value, other, StringComparison.OrdinalIgnoreCase))
            {
                return false;
            }
        }

        return true;
    }

    private static Dictionary<string, string> Identifiers(object? agent)
    {
        var d = new Dictionary<string, string>();
        var fi = Get(agent, "FinancialInstitutionIdentification");
        var bic = Get(fi, "BICFI")?.ToString();
        if (bic is { Length: >= 8 })
        {
            d["BIC"] = bic.Substring(0, 8);
        }

        var lei = Get(fi, "LEI")?.ToString();
        if (!string.IsNullOrEmpty(lei))
        {
            d["LEI"] = lei!;
        }

        var member = Get(fi, "ClearingSystemMemberIdentification");
        var memberId = Get(member, "MemberIdentification")?.ToString();
        if (!string.IsNullOrEmpty(memberId))
        {
            var system = Get(member, "ClearingSystemIdentification");
            d["CLR:" + (Get(system, "Value") ?? system)?.ToString()] = memberId!;
        }

        return d;
    }

    // A member by name, whether the object is a class or a proxy of the interface.
    private static object? Get(object? o, string name)
    {
        if (o is null)
        {
            return null;
        }

        var p = o.GetType().GetProperty(name);
        if (p is null)
        {
            foreach (var i in o.GetType().GetInterfaces())
            {
                p = i.GetProperty(name);
                if (p is not null)
                {
                    break;
                }
            }
        }

        return p?.GetValue(o);
    }

    internal static bool Has(object? v) => v is not null;

    internal static bool InList(object? v, IReadOnlySet<string> names) => v is not null && names.Contains(v.ToString()!);
}
'''

def find_type(idx, name):
    """The id of the message component or choice of this name, for example PostalAddress27."""
    for i, e in idx.items():
        if e["name"] == name and e.get("xmlElementName") == "topLevelDictionaryEntry":
            return i
    sys.exit(f"no component {name} in the pages of the specification")


def find_message(idx, identifier):
    """The id of the message definition with this identifier, for example pacs.008.001.14."""
    for i, e in idx.items():
        for c in e.get("children", []):
            if c.get("xmlElementName") == "messageDefinitionIdentifier" and c.get("name") == identifier:
                return i
    sys.exit(f"no message {identifier} in the pages of the specification")


def main():
    global CENSUS, MSGS, PRIM, VAL, RULES_DIRS
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--census", required=True, help="folder of the saved pages of the specification")
    what = ap.add_mutually_exclusive_group(required=True)
    what.add_argument("--message", action="append", help="identifier of the message, for example pacs.008.001.14; repeat it for several")
    what.add_argument("--areas", help="every message of these business areas, all versions, for example pacs,pain")
    what.add_argument("--type", action="append", help="a message component or choice on its own, for example PostalAddress27 (with what it reaches); repeat it for several")
    ap.add_argument("--rules", action="append", help="folder of the hand-written rules (<Type>Validator.Rules.cs); the validators folder by default")
    ap.add_argument("--out", required=True, help="folder to write the validators to")
    ap.add_argument("--messages", default=os.path.join(REPO_ROOT, "..", "iso-20022-messages"), help="clone of iso-20022-messages")
    ap.add_argument("--primitives", default=os.path.join(REPO_ROOT, "..", "iso-20022-primitives"), help="clone of iso-20022-primitives")
    ap.add_argument("--validators", default=VAL, help="folder of the hand-written validators (to reuse those of choices)")
    args = ap.parse_args()
    CENSUS = os.path.abspath(args.census)
    MSGS = os.path.join(os.path.abspath(args.messages), "src", "Messages") + os.sep
    PRIM = os.path.join(os.path.abspath(args.primitives), "src", "Primitives") + os.sep
    VAL = os.path.abspath(args.validators) + os.sep
    RULES_DIRS = [os.path.abspath(d) for d in (args.rules or [VAL])]
    outdir = args.out
    os.makedirs(outdir, exist_ok=True)
    model = Model()
    if args.areas:
        areas = set(args.areas.split(","))
        roots = [i for i, e in model.idx.items() for c in e.get("children", [])
                 if c.get("xmlElementName") == "messageDefinitionIdentifier" and c["name"].split(".")[0] in areas]
    elif args.message:
        roots = [find_message(model.idx, m_) for m_ in args.message]
    else:
        roots = [find_type(model.idx, t) for t in args.type]
    g = Gen(model)
    report = {k: [] for k in ("no_interface", "mismatch", "prose_only", "guidelines", "unsupported", "pending", "known_issues", "generated_rules", "translated_rules", "generated_types", "reused_hand_validators")}
    seen, st = set(roots), list(roots)
    order = []
    while st:
        i = st.pop()
        e = model.idx.get(i)
        if e is None:
            report["no_interface"].append(f"{i}: not in the census")
            continue
        order.append(e)
        for c in e.get("children", []):
            for r in c.get("references", []):
                if r["relation"] in ("complexType", "type") and r["id"] not in seen:
                    seen.add(r["id"])
                    st.append(r["id"])
    for e in order:
        isch = e["id"] in model.idx and model.is_choice("I" + e["name"])
        if isch:
            cls, code = emit_choice(g, e, report)
            open(os.path.join(outdir, cls + ".cs"), "w", encoding="utf-8").write(code)
            report["generated_types"].append(e["name"])
            continue
        res = emit_type(g, e, report)
        if res is None:
            continue
        cls, code, _ = res
        open(os.path.join(outdir, cls + ".cs"), "w", encoding="utf-8").write(code)
        report["generated_types"].append(e["name"])
    for t in sorted(g.ext_used):
        if not (t in model.hand and model.hand[t][1] == "Codesets"):
            open(os.path.join(outdir, t + "Validator.cs"), "w", encoding="utf-8").write(emit_code_validator(t))
            report["generated_types"].append(t)
    report["external_codes_wired"] = sorted(g.ext_used)
    open(os.path.join(outdir, "RuleOps.cs"), "w", encoding="utf-8").write(RULE_OPS)
    cl = ["// Generated by tools/generator/generate_validators.py (prototype). The codes of the code sets that rules list.", "", "namespace Gen;", "", "internal static class CodeLists", "{"]
    for code, names in sorted(g.lists.items()):
        cl.append(f"    internal static readonly IReadOnlySet<string> {code} = new HashSet<string> {{ " + ", ".join(f'"{n}"' for n in names) + " };")
    cl.append("}")
    open(os.path.join(outdir, "CodeLists.cs"), "w", encoding="utf-8").write("\n".join(cl) + "\n")
    json.dump(report, open(os.path.join(outdir, "report.json"), "w"), indent=1)
    print({k: len(v) for k, v in report.items()})


if __name__ == "__main__":
    main()
