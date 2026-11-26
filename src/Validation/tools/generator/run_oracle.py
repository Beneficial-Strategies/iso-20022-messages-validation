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
    ap.add_argument("--message", required=True)
    ap.add_argument("--messages", default=os.path.join(REPO, "..", "iso-20022-messages"))
    ap.add_argument("--primitives", default=os.path.join(REPO, "..", "iso-20022-primitives"))
    args = ap.parse_args()

    work = os.path.join(REPO, "artifacts", "generator-oracle")
    shutil.rmtree(work, ignore_errors=True)
    out = os.path.join(work, "out")
    os.makedirs(os.path.join(work, "oracle"))

    subprocess.run(
        [sys.executable, os.path.join(HERE, "generate_validators.py"), "--census", args.census, "--message", args.message,
         "--out", out, "--messages", args.messages, "--primitives", args.primitives],
        check=True,
    )
    types = json.load(open(os.path.join(out, "report.json")))["generated_types"]

    copied, no_test, needs_args = 0, [], []
    for t in types:
        found = glob.glob(os.path.join(TESTS, "Validators", "*", f"{t}ValidatorTests.cs"))
        if not found:
            no_test.append(t)
            continue
        s = open(found[0], encoding="utf-8").read()
        s = re.sub(r"(?<![\w.])" + t + r"Validator\b", "Gen." + t + "Validator", s)
        # The hand-written tests build a PaymentIdentification13 with only an EndToEndIdentification, which the
        # specification forbids (TransactionIdentificationPresenceRule: TransactionIdentification or UETR). The
        # data is made valid so that this one rule does not hide the others.
        s = re.sub(
            r'(Make<IPaymentIdentification13>\(b2 => b2\s*\.Set\(x2 => x2\.EndToEndIdentification\)\.To\("E2E-001"\))',
            r'\1.Set(x2 => x2.TransactionIdentification).To("TX-001")',
            s,
        )
        if re.search(r"Gen\." + t + r"Validator\(\s*[^)\s]", s):
            # the hand-written validator takes arguments (an external code set registry): not generated yet
            needs_args.append(t)
            continue
        open(os.path.join(work, "oracle", f"{t}ValidatorTests.cs"), "w", encoding="utf-8").write(s)
        copied += 1
    print(f"{copied} hand-written test files copied; {len(no_test)} generated types have none: {', '.join(no_test)}")
    print(f"skipped, their validator takes arguments (external code sets, not generated yet): {', '.join(needs_args) or 'none'}")

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

    subprocess.run(["dotnet", "test", "-c", "Release", "--logger", "trx;LogFileName=results.trx"], cwd=work, check=False)

    # the failures, against the list of known differences (known_differences/<message>.tsv: test<TAB>reason)
    ns = {"t": "http://microsoft.com/schemas/VisualStudio/TeamTest/2010"}
    root = ET.parse(os.path.join(work, "TestResults", "results.trx")).getroot()
    results = root.findall(".//t:UnitTestResult", ns)
    failed = sorted(r.get("testName") for r in results if r.get("outcome") == "Failed")
    known_file = os.path.join(HERE, "known_differences", args.message + ".tsv")
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
