"""How many rules of the ISO 20022 standard the generator implements, and how many it does not (yet).

    python3 rule_coverage.py --census <folder of the pages> [--messages <clone>] [--primitives <clone>]

Counts the constraints of the specification (every message, component and choice, every version, as the MCP server serves them)
and sorts each one:

  guideline       advice of the specification, not a rule a message can break (not counted as a rule)
  expression      the specification gives a machine-readable expression and the generator reads it
  translated      the specification gives prose; a reading of it is in translations/ and the generator reads that
  prose           the specification gives prose only, and no reading has been written yet
  expression-*    the specification gives an expression the generator cannot use (see docs/KnownRuleChallenges.md)

The rules are counted as the validators meet them: one per type and version that carries the constraint. The same text on many types
counts once for each; the distinct texts are given as well.
"""
import argparse
import collections
import json
import os
import re
import sys

import generate_validators as gv


def classify(g, m, e, c):
    t = e["name"]
    ex = c.get("attributes", {}).get("expression")
    prose = re.sub(r"\s+", " ", c.get("definition") or "").strip()
    if not ex:
        if c["name"].endswith("Guideline"):
            return "guideline", prose
        tr = gv.load_translation(c["name"], prose)
        return ("translated" if tr and tr.get("rules") else "prose"), prose
    try:
        _, must, cond = gv.parse_rule(ex)
        g.section("x", "I" + t, must)
        if cond:
            g.section("x", "I" + t, cond)
        return "expression", prose
    except gv.Unsupported as u:
        s = str(u)
        if "phrase" in s:
            return "expression-phrase", prose
        if "no member" in s or "not a member" in s:
            return "expression-names-something-the-type-does-not-have", prose
        return "expression-other", prose
    except Exception:
        return "expression-not-a-rule-definition", prose


def reach(m, areas):
    """the types the messages of these business areas (all versions) reach, with the messages"""
    seen = {i for i, e in m.idx.items() for c in e.get("children", [])
            if c.get("xmlElementName") == "messageDefinitionIdentifier" and c["name"].split(".")[0] in areas}
    st = list(seen)
    while st:
        e = m.idx.get(st.pop())
        for c in (e or {}).get("children", []):
            for r in c.get("references", []):
                if r["relation"] in ("complexType", "type") and r["id"] not in seen:
                    seen.add(r["id"])
                    st.append(r["id"])
    return [m.idx[i] for i in seen if i in m.idx]


def members(m, entities):
    """how many members the types have, and how many of them the type system checks by itself"""
    total = by_type = 0
    simple = set()
    for e in entities:
        props = m.ifaces.get("I" + e["name"])
        for name, (t, nullable, coll) in (props or {}).items():
            total += 1
            if m.kind(t) in ("struct", "enum", "extcode", "class"):  # a simple type, a code set, an amount: its constructor checks the facets
                by_type += 1
                simple.add(t)
    return {"types": len(entities), "members": total, "by_type_system": by_type, "simple_types": len(simple)}


def accounting(m, g, entities):
    """what the generator does with each rule of these types (the same run as a real generation, nothing written)"""
    gv.RULES_DIRS = [gv.VAL]
    report = {k: [] for k in ("no_interface", "mismatch", "prose_only", "guidelines", "unsupported", "pending", "known_issues",
                              "generated_rules", "translated_rules", "generated_types", "reused_hand_validators")}
    for e in entities:
        gv.emit_type(g, e, report) if not m.is_choice("I" + e["name"]) else None
    return report


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--census", required=True)
    ap.add_argument("--messages", default=os.path.join(gv.REPO_ROOT, "..", "iso-20022-messages"))
    ap.add_argument("--primitives", default=os.path.join(gv.REPO_ROOT, "..", "iso-20022-primitives"))
    ap.add_argument("--areas", help="only what the messages of these business areas reach, for example pacs,pain (all versions)")
    ap.add_argument("--list", metavar="KIND", help="print the rules of this kind (for example prose), one distinct text per line")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    gv.CENSUS = os.path.abspath(args.census)
    gv.MSGS = os.path.join(os.path.abspath(args.messages), "src", "Messages") + os.sep
    gv.PRIM = os.path.join(os.path.abspath(args.primitives), "src", "Primitives") + os.sep
    m = gv.Model()
    g = gv.Gen(m)
    entities = list(m.idx.values())
    if args.areas:
        entities = reach(m, set(args.areas.split(",")))
    inst, dist, where = collections.Counter(), collections.defaultdict(set), collections.defaultdict(list)
    for e in entities:
        for c in e.get("children", []):
            if c.get("xmlElementName") == "constraint":
                k, prose = classify(g, m, e, c)
                inst[k] += 1
                dist[k].add((c["name"], prose))
                where[(k, c["name"], prose)].append(e["name"])
    if args.list:
        for (k, name, prose), types in sorted(where.items(), key=lambda kv: (-len(kv[1]), kv[0])):
            if k == args.list:
                print(f"{len(types)}\t{name}\t{prose}")
        return
    structure = members(m, entities)
    acct = accounting(m, g, entities) if args.areas else None
    rules = sum(v for k, v in inst.items() if k != "guideline")
    done = inst["expression"] + inst["translated"]
    if acct is not None:
        rules = len(acct["generated_rules"]) + len(acct["translated_rules"]) + len(acct["known_issues"]) + len(acct["pending"])
        done = len(acct["generated_rules"]) + len(acct["translated_rules"])
        out_scope = {
            "rules": rules,
            "implemented": done,
            "implemented_from_the_specifications_expression": len(acct["generated_rules"]),
            "implemented_read_from_prose": len(acct["translated_rules"]),
            "known_issues_not_checkable": len(acct["known_issues"]),
            "pending_still_to_do": len(acct["pending"]),
            "guidelines": inst["guideline"],
            "percent_implemented": round(100 * done / rules, 1),
        }
        if args.json:
            print(json.dumps({**out_scope, "members": structure}, indent=1))
        else:
            print(f"{out_scope['rules']:,} rules (guidelines, {out_scope['guidelines']:,}, not counted: the UI layer is presumed to follow them)")
            print(f"  implemented:                              {done:6,}  ({out_scope['percent_implemented']}%)")
            print(f"    from the specification's expression:    {len(acct['generated_rules']):6,}")
            print(f"    read from the specification's prose:    {len(acct['translated_rules']):6,}")
            print(f"  known issues (cannot be checked on the message, kept in docs/KnownRuleChallenges.md): {len(acct['known_issues']):,}")
            print(f"  still to do:                              {len(acct['pending']):6,}")
            print(f"the members of the {structure['types']:,} types: {structure['members']:,}")
            print(f"  checked by the type system (facets of a simple type, the codes of a code set, the amount's currency): {structure['by_type_system']:,} members, {structure['simple_types']} types")
        return
    out = {
        "constraints": sum(inst.values()),
        "guidelines": inst["guideline"],
        "rules": rules,
        "implemented": done,
        "not_yet": rules - done,
        "percent_implemented": round(100 * done / rules, 1),
        "by_kind": {k: {"instances": v, "distinct": len(dist[k])} for k, v in inst.most_common()},
        "members": structure,
    }
    if args.json:
        print(json.dumps(out, indent=1))
        return
    print(f"{out['constraints']:,} constraints, of which {out['guidelines']:,} are guidelines (advice, not rules)")
    print(f"{rules:,} rules; {done:,} implemented ({out['percent_implemented']}%); {rules - done:,} not yet\n")
    for k, v in inst.most_common():
        print(f"  {k:55} {v:6,} instances {len(dist[k]):5,} distinct")
    print(f"\nthe members of the {structure['types']:,} types: {structure['members']:,}")
    print(f"  checked by the type system (the facets of a simple type, the codes of a code set): {structure['by_type_system']:,} members, {structure['simple_types']} types")
    print(f"  checked by the validators (required, at least one item, at most n items, a validator of its own): the rest")


if __name__ == "__main__":
    main()
