#!/usr/bin/env python3
"""
Runs the hand-written tests of the validators against the generated ones, as an oracle.

    python3 run_oracle.py --census DIR --message pacs.008.001.14 [--messages PATH] [--primitives PATH]

1. generates the validators of the message and of everything it reaches (generate_validators.py),
2. copies the hand-written test file of each generated type into a scratch project, with the
   validator under test replaced by the generated one (namespace Gen),
3. builds the project and runs the tests.

Everything is written under artifacts/generator-oracle/ (not tracked). The tests are those of
tests/Validation.Tests; a test that fails is a difference between a hand-written validator and the
specification (or a generator bug): each has to be read, not just counted.
"""
import argparse
import glob
import xml.etree.ElementTree as ET
import json
import os
import re
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
TESTS = os.path.join(REPO, "tests", "Validation.Tests")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--census", required=True)
    what = ap.add_mutually_exclusive_group(required=True)
    what.add_argument("--message", help="for example pacs.008.001.14")
    what.add_argument("--type", help="a component or choice on its own, for example PostalAddress27")
    ap.add_argument("--rules", action="append", help="folder of the hand-written rules (<Type>Validator.Rules.cs); the validators folder by default")
    ap.add_argument("--messages", default=os.path.join(REPO, "..", "iso-20022-messages"))
    ap.add_argument("--primitives", default=os.path.join(REPO, "..", "iso-20022-primitives"))
    args = ap.parse_args()

    work = os.path.join(REPO, "artifacts", "generator-oracle")
    shutil.rmtree(work, ignore_errors=True)
    out = os.path.join(work, "out")
    os.makedirs(os.path.join(work, "oracle"))

    subprocess.run(
        [sys.executable, os.path.join(HERE, "generate_validators.py"), "--census", args.census,
         *(["--message", args.message] if args.message else ["--type", args.type]),
         *[a for d in (args.rules or []) for a in ("--rules", d)],
         "--out", out, "--messages", args.messages, "--primitives", args.primitives],
        check=True,
    )
    types = json.load(open(os.path.join(out, "report.json")))["generated_types"]

    # the hand-written rules of the generated types (<Type>Validator.Rules.cs), in the namespace of the generated files
    for d in args.rules or [os.path.join(REPO, "src", "Validation", "Validators")]:
        for f in glob.glob(os.path.join(d, "**", "*Validator.Rules.cs"), recursive=True):
            t = os.path.basename(f)[: -len("Validator.Rules.cs")]
            if t in types:
                text = re.sub(r"^namespace [\w.]+;", "namespace Gen;", open(f, encoding="utf-8").read(), flags=re.M)
                open(os.path.join(out, os.path.basename(f)), "w", encoding="utf-8").write(text)

    copied, no_test = 0, []
    for t in types:
        # the validator of a choice is named X_Validator, the others XValidator
        suf = next((x for x in ("", "_") if glob.glob(os.path.join(TESTS, "Validators", "*", f"{t}{x}ValidatorTests.cs"))), "")
        found = glob.glob(os.path.join(TESTS, "Validators", "*", f"{t}{suf}ValidatorTests.cs"))
        if not found:
            no_test.append(t)
            continue
        s = open(found[0], encoding="utf-8").read()
        s = re.sub(r"(?<![\w.])" + t + suf + r"Validator\b", "Gen." + t + suf + "Validator", s)
        # The hand-written tests build a PaymentIdentification13 with only an EndToEndIdentification, which the
        # specification forbids (TransactionIdentificationPresenceRule: TransactionIdentification or UETR). The
        # data is made valid so that this one rule does not hide the others.
        s = re.sub(
            r'(Make<IPaymentIdentification13>\(b2 => b2\s*\.Set\(x2 => x2\.EndToEndIdentification\)\.To\("E2E-001"\))',
            r'\1.Set(x2 => x2.TransactionIdentification).To("TX-001")',
            s,
        )
        open(os.path.join(work, "oracle", f"{t}{suf}ValidatorTests.cs"), "w", encoding="utf-8").write(s)
        copied += 1
    print(f"{copied} hand-written test files copied; {len(no_test)} generated types have none: {', '.join(no_test)}")

    tests_csproj = open(glob.glob(os.path.join(TESTS, "*.csproj"))[0], encoding="utf-8").read()
    packages = [
        f'<PackageReference Include="{i}" Version="{v}" />'
        for i, v in re.findall(r'<PackageReference Include="([^"]+)" Version="([^"]+)"', tests_csproj)
    ]
    validation = os.path.join(REPO, "src", "Validation", "BeneficialStrategies.Iso20022.Messages.Validation.csproj")
    csproj = f"""<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup>
    <TargetFramework>net10.0</TargetFramework>
    <Nullable>enable</Nullable>
    <ImplicitUsings>enable</ImplicitUsings>
    <IsPackable>false</IsPackable>
    <TreatWarningsAsErrors>false</TreatWarningsAsErrors>
    <NoWarn>CS8604;CS8602;CS8600;CS8620;CS8619;CS8625;CS1591;CS8601;CS8603</NoWarn>
  </PropertyGroup>
  <ItemGroup>
    {chr(10).join("    " + p for p in packages).strip()}
    <ProjectReference Include="{validation}" />
  </ItemGroup>
</Project>
"""
    open(os.path.join(work, "Oracle.csproj"), "w", encoding="utf-8").write(csproj)
    shutil.copy(os.path.join(TESTS, "GlobalUsings.cs"), os.path.join(work, "GlobalUsings.cs"))
    # the namespace of the message's business area (the tests' own usings name only camt, pacs and pain)
    areas = [os.path.basename(d) for d in glob.glob(os.path.join(args.messages, "src", "Messages", "MessageDefinitions", "*")) if os.path.isdir(d)]
    with open(os.path.join(work, "GlobalUsings.cs"), "a", encoding="utf-8") as fh:
        for area in sorted(set(areas) - {"camt", "pacs", "pain"}):
            fh.write(f"global using BeneficialStrategies.Iso20022.{area};\n")

    subprocess.run(["dotnet", "test", "-c", "Release", "--logger", "trx;LogFileName=results.trx"], cwd=work, check=False)

    # the failures, against the list of known differences (known_differences/<message>.tsv: test<TAB>reason)
    ns = {"t": "http://microsoft.com/schemas/VisualStudio/TeamTest/2010"}
    root = ET.parse(os.path.join(work, "TestResults", "results.trx")).getroot()
    results = root.findall(".//t:UnitTestResult", ns)
    failed = sorted(r.get("testName") for r in results if r.get("outcome") == "Failed")
    known_file = os.path.join(HERE, "known_differences", (args.message or args.type) + ".tsv")
    known = {}
    if os.path.exists(known_file):
        for line in open(known_file, encoding="utf-8"):
            if line.strip() and not line.startswith("#"):
                name, _, reason = line.rstrip("\n").partition("\t")
                known[name] = reason
    unexpected = [f for f in failed if f not in known]
    fixed = [k for k in known if k not in failed]
    print(f"\n{len(results)} tests, {len(failed)} failed: {len(failed) - len(unexpected)} known differences, {len(unexpected)} unexpected.")
    for f in unexpected:
        print("  UNEXPECTED", f)
    for f in fixed:
        print("  known difference that no longer fails (remove it from the list):", f)
    sys.exit(1 if unexpected or fixed else 0)


if __name__ == "__main__":
    main()
