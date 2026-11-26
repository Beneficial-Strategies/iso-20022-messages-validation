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


def segs(path):
    parts = [p for p in path.strip("/").split("/") if p]
    out = []
    for p in parts:
        m = re.match(r"^(@?\w+)(?:\[(\*|\d+)\])?$", p)
        if not m:
            raise Unsupported(f"path segment '{p}'")
        out.append((m.group(1), m.group(2)))
    return out


class Gen:
    def __init__(self, model):
        self.m = model
        self.uid = 0
        self.lists = {}
        self.ext_used = set()

    def var(self):
        self.uid += 1
        return f"i{self.uid}"

    # ---- member access; returns (type, nullable, collection)
    def member(self, cur, itype, name):
        if itype.startswith("V|"):  # the value of a choice variant: its own type
            itype = itype.split("|")[2]
        props = self.m.ifaces.get(itype)
        if props is not None and name in props:
            return props[name]
        v = self.variant(itype, name)
        if v is not None:
            return v
        raise Unsupported(f"{itype} has no member {name}")

    def variant(self, itype, name):
        """A choice is an interface with one variant interface per alternative (Choices/<Choice>/I<Name>.cs), whose
        `Value` is the alternative. The path of a rule names the alternative; it is `cur as Variant`."""
        if not self.m.is_choice(itype):
            return None
        f = MSGS + f"Choices/{itype[1:]}/I{name}.cs"
        if not os.path.exists(f):
            return None
        vm = re.search(r"^\s*([\w<>\.\?]+)\s+Value\s*\{\s*get;", open(f, encoding="utf-8").read(), re.M)
        if vm is None:
            return None
        return (f"V|{itype[1:]}.I{name}|{vm.group(1).rstrip('?')}", True, False)

    def access(self, cur, ctype, name, t):
        """the C# expression of member `name` of `cur`"""
        if t.startswith("V|"):
            return f"({cur} as BeneficialStrategies.Iso20022.Choices.{t.split('|')[1]})"
        if ctype.startswith("V|"):
            return f"{cur}?.Value?.{name}"
        return f"{cur}?.{name}"

    def unwrap(self, e, t):
        """a variant compared with a value is compared by its Value"""
        if t.startswith("V|"):
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
                if idx not in (None,):
                    raise Unsupported("indexed collection on the right of a comparison")
            ctype = t
        return cur, ctype

    def present(self, e, t, coll):
        if coll:
            return f"({e}?.Any() ?? false)"
        if self.m.kind(t) in ("struct", "extcode") and re.match(r"^i\d+$", e):
            return f"RuleOps.Has({e})"  # an element of a collection of structs: it cannot be compared with null
        return f"{e} is not null"

    # ---- BooleanRule -> bool expression over x
    def boolean(self, x, itype, typ, left, right):
        if typ in ("Presence", "Absence"):
            if typ == "Presence":
                return self.walk(x, itype, left, lambda e, t, c: self.present(e, t, c))
            return self.walk(x, itype, left, lambda e, t, c: f"!({self.present(e, t, c)})")
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
                    sel = f"t.{ss[1][0]}" + (".Amount" if self.m.kind(et) == "class" else "")
                    rhs = f"({x}.{ss[0][0]} ?? []).Sum(t => {sel})"
                lhs_body = self.walk(x, itype, left, lambda e, t, c: f"RuleOps.Number({e}) {'!=' if neg else '=='} {rhs}")
                return lhs_body
            lit = right
            if re.search(r"\s", lit or ""):
                # The data has a few expressions whose "value" is a phrase ("Branch of DebtorAgent"): they describe a rule
                # instead of stating it, and compared literally they would refuse every message. Not generated; reported.
                raise Unsupported(f"the expression compares with a phrase, '{lit}', which describes the rule rather than expressing it")
            def cmp(e, t, c):
                e, t = self.unwrap(e, t)
                k = self.m.kind(t)
                if k == "enum":
                    mem = enum_members(t)
                    if mem is not None and lit not in mem:
                        raise Unsupported(f"{lit} is not a member of {t}")
                    return f"{e} {'!=' if neg else '=='} {t}.{lit}"
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
             "EqualToValue": "{} equals {r}", "DifferentFromValue": "{} differs from {r}", "WithInList": "{} is in {r}", "NotWithInList": "{} is not in {r}"}
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


def emit_type(g, e, report):
    m = g.m
    name = e["name"]
    g.uid = 0  # the names of the loop variables start again in each type, so a change elsewhere does not touch this file
    itype = "I" + name
    props = m.ifaces.get(itype)
    if props is None:
        report["no_interface"].append(name)
        return None
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
            if mn >= 1:
                lines.append(f'RuleFor(x => x.{mem}).NotEmpty().WithMessage({w} must have at least {mn} item(s) ({mn}..{mxs or "n"})."); ')
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
    for c in consts:
        cname = c["name"]
        ex = c.get("attributes", {}).get("expression")
        prose = norm(c.get("definition"))
        if not ex:
            kind = "guideline" if cname.endswith("Guideline") else "prose"
            report["prose_only" if kind == "prose" else "guidelines"].append(f"{name}.{cname}")
            rule_lines.append(f"// {cname}: not implemented, the specification gives no expression ({'guideline' if kind == 'guideline' else 'prose only'}):")
            rule_lines.append(f"//   {prose}")
            continue
        try:
            kind, must, cond = parse_rule(ex)
            body_must = g.section("x", itype, must)
            expr = body_must if (kind == "SimpleRule" or cond is None) else f"!({g.section('x', itype, cond)}) || ({body_must})"
        except Unsupported as u:
            report["unsupported"].append(f"{name}.{cname}: {u}")
            rule_lines.append(f"// {cname}: not generated ({u}). {prose}")
            continue
        report["generated_rules"].append(f"{name}.{cname}")
        cond_t = ("if " + g.english(cond) + ": " if cond is not None and kind != "SimpleRule" else "")
        rule_lines.append(f"// ── {cname} ── {cond_t}{g.english(must)}")
        rule_lines.append(f"// {prose}")
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
    out.append("namespace Gen;")
    out.append("")
    out.append(f"/// <summary>Validates <see cref=\"{itype}\"/> per the ISO 20022 specification.</summary>")
    out.append(f"public class {cls} : AbstractValidator<{itype}>")
    out.append("{")
    if all_vals:
        out.append(f"    public {cls}(\n        {params}\n    )")
    else:
        out.append(f"    public {cls}()")
    out.append("    {")
    for l in lines + ([""] if lines and rule_lines else []) + rule_lines:
        out.append(("        " + l) if l else "")
    out.append("    }")
    if all_vals:
        out.append("")
        out.append(f"    public {cls}()\n        : this({', '.join(default_for(t) for t, _ in all_vals)}) {{ }}")
    out.append("}")
    return cls, "\n".join(out) + "\n", list(child_vals)


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

    internal static bool Has(object? v) => v is not null;

    internal static bool InList(object? v, IReadOnlySet<string> names) => v is not null && names.Contains(v.ToString()!);
}
'''

def find_message(idx, identifier):
    """The id of the message definition with this identifier, for example pacs.008.001.14."""
    for i, e in idx.items():
        for c in e.get("children", []):
            if c.get("xmlElementName") == "messageDefinitionIdentifier" and c.get("name") == identifier:
                return i
    sys.exit(f"no message {identifier} in the pages of the specification")


def main():
    global CENSUS, MSGS, PRIM, VAL
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--census", required=True, help="folder of the saved pages of the specification")
    ap.add_argument("--message", required=True, help="identifier of the message, for example pacs.008.001.14")
    ap.add_argument("--out", required=True, help="folder to write the validators to")
    ap.add_argument("--messages", default=os.path.join(REPO_ROOT, "..", "iso-20022-messages"), help="clone of iso-20022-messages")
    ap.add_argument("--primitives", default=os.path.join(REPO_ROOT, "..", "iso-20022-primitives"), help="clone of iso-20022-primitives")
    ap.add_argument("--validators", default=VAL, help="folder of the hand-written validators (to reuse those of choices)")
    args = ap.parse_args()
    CENSUS = os.path.abspath(args.census)
    MSGS = os.path.join(os.path.abspath(args.messages), "src", "Messages") + os.sep
    PRIM = os.path.join(os.path.abspath(args.primitives), "src", "Primitives") + os.sep
    VAL = os.path.abspath(args.validators) + os.sep
    outdir = args.out
    os.makedirs(outdir, exist_ok=True)
    model = Model()
    msg_id = find_message(model.idx, args.message)
    g = Gen(model)
    report = {k: [] for k in ("no_interface", "mismatch", "prose_only", "guidelines", "unsupported", "generated_rules", "generated_types", "reused_hand_validators")}
    seen, st = {msg_id}, [msg_id]
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
