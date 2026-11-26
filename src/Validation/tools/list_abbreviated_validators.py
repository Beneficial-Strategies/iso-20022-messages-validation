#!/usr/bin/env python3
"""
Lists the validators that are still abbreviated (issue #19): not yet derived in full from the
ISO 20022 specification. A validator is abbreviated when its remarks carry the TODO marker
"Abbreviated validator", or any of the weaker signs below (a rule left out with a comment, a nested
type left unvalidated).

    python3 list_abbreviated_validators.py [--tsv PATH] [--summary]

Prints one line per validator: folder, validator, markers, whether the validator has a test file of
its own. With --tsv the same as tab-separated columns. Exit code 1 if any validator carries the
TODO marker (the one sure sign), so that a test or CI step can key off it; 0 otherwise.
"""
import argparse
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
VALIDATORS = os.path.abspath(os.path.join(HERE, "..", "Validators"))
TESTS = os.path.abspath(os.path.join(HERE, "..", "..", "..", "tests", "Validation.Tests", "Validators"))

# name -> pattern. "abbreviated" is the marker; the rest are weaker signs that a rule is missing.
MARKERS = {
    "abbreviated": re.compile(r"Abbreviated validator"),
    "not-reviewed": re.compile(r"not yet reviewed", re.I),
    "deferred": re.compile(r"deferred|out of scope for this", re.I),
    "unvalidated-nested": re.compile(r"no validator exists|nested fields unvalidated|unvalidated", re.I),
    "required-comment": re.compile(r"already (?:a )?(?:`|<c>)?required", re.I),
}


def scan():
    rows = []
    for folder in sorted(os.listdir(VALIDATORS)):
        d = os.path.join(VALIDATORS, folder)
        if not os.path.isdir(d):
            continue
        for fn in sorted(os.listdir(d)):
            if not fn.endswith(".cs"):
                continue
            with open(os.path.join(d, fn), encoding="utf-8") as f:
                text = f.read()
            found = [name for name, rx in MARKERS.items() if rx.search(text)]
            has_test = os.path.isfile(os.path.join(TESTS, folder, fn[:-3] + "Tests.cs"))
            rows.append((folder, fn[:-3], found, has_test))
    return rows


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--tsv", default=None, help="also write the list as tab-separated values to this path")
    ap.add_argument("--summary", action="store_true", help="print counts only")
    args = ap.parse_args()
    rows = scan()
    if args.tsv:
        with open(args.tsv, "w", encoding="utf-8") as f:
            f.write("folder\tvalidator\tmarkers\thasTest\n")
            for folder, name, found, has_test in rows:
                f.write(f"{folder}\t{name}\t{','.join(found)}\t{'yes' if has_test else 'no'}\n")
    flagged = [r for r in rows if r[2]]
    if args.summary:
        print(f"validators: {len(rows)}")
        for name in MARKERS:
            print(f"  {name}: {sum(1 for r in rows if name in r[2])}")
        print(f"  with a test file of their own: {sum(1 for r in rows if r[3])}")
        print(f"  abbreviated and without a test file: {sum(1 for r in rows if 'abbreviated' in r[2] and not r[3])}")
    else:
        for folder, name, found, has_test in flagged:
            print(f"{folder}\t{name}\t{','.join(found)}\t{'test' if has_test else 'no-test'}")
    return 1 if any("abbreviated" in r[2] for r in rows) else 0


if __name__ == "__main__":
    sys.exit(main())
