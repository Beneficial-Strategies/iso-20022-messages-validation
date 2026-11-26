"""Tests of build_coverage_checksums.py and check_message_coverage_gaps.py on a small fixture:
the layout of the model repositories (iso-20022-messages, iso-20022-primitives) and of this one,
so that the scripts cannot go stale silently when a folder moves.

    python3 -m unittest -q test_coverage_scripts        (from this folder)
"""
import json
import os
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
BUILD = os.path.join(HERE, "build_coverage_checksums.py")
GAPS = os.path.join(HERE, "check_message_coverage_gaps.py")
REPO_ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def run(script, *args):
    return subprocess.run([sys.executable, "-I", script, *args], capture_output=True, text=True)


class FixtureTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        t = self.tmp.name
        m = os.path.join(t, "messages", "src", "Messages")
        p = os.path.join(t, "primitives", "src", "Primitives")
        write(os.path.join(m, "Components", "IFoo1.cs"), '[IsoId("id-foo")]\npublic interface IFoo1 { }\n')
        write(os.path.join(m, "Choices", "IBarChoice.cs"), '[IsoId("id-bar")]\npublic interface IBarChoice { }\n')
        write(os.path.join(m, "MessageDefinitions", "pain", "IBazV01.cs"), '[IsoId("id-baz")]\npublic interface IBazV01 { }\n')
        write(os.path.join(m, "MessageDefinitions", "pain", "IBazV02.cs"), '[IsoId("id-baz2")]\npublic interface IBazV02 { }\n')
        write(os.path.join(p, "Codesets", "QuxCode.cs"), '[IsoId("id-qux")]\npublic enum QuxCode { }\n')
        v = os.path.join(t, "validators")
        write(os.path.join(v, "Components", "Foo1Validator.cs"), "public class Foo1Validator : AbstractValidator<IFoo1> { }\n")
        write(os.path.join(v, "Choices", "BarChoice_Validator.cs"), "public class BarChoice_Validator : AbstractValidator<IBarChoice> { }\n")
        write(os.path.join(v, "pain", "BazV01Validator.cs"), "public class BazV01Validator : AbstractValidator<IBazV01> { }\n")
        write(os.path.join(v, "Codesets", "QuxCodeValidator.cs"), "public class QuxCodeValidator : ExternalCodesetAbstractValidator<QuxCode> { }\n")
        write(os.path.join(v, "Components", "GoneValidator.cs"), "public class GoneValidator : AbstractValidator<IFoo1> { }\n")
        # MSGCOMP: type, name, id, status, removalDate, checksum, definition
        self.tsv = os.path.join(t, "snapshot.tsv")
        write(
            self.tsv,
            "MSGCOMP\tFoo1\tid-foo\tRegistered\t—\tchk-foo\tdef\n"
            "CHOICE\tBarChoice\tid-bar\tObsolete\t2027-01-01\tchk-bar\tdef\n"
            "MSGDEF\tBazV01\tid-baz\tpain\tRegistered\t—\tchk-baz\tdef\n"
            "MSGDEF\tBazV02\tid-baz2\tpain\tRegistered\t—\tchk-baz2\tdef\n"
            "CODESET\tQuxCode\tid-qux\tRegistered\tchk-qux\tdef\n",
        )
        self.m, self.p, self.v = (os.path.join(t, x) for x in ("messages", "primitives", "validators"))
        self.out = os.path.join(t, "out.json")

    def tearDown(self):
        self.tmp.cleanup()

    def build(self, *extra):
        return run(BUILD, self.tsv, "--messages", self.m, "--primitives", self.p, "--validators", self.v, "--out", self.out, *extra)

    def test_manifest_is_keyed_as_before_and_carries_the_checksums(self):
        r = self.build()
        self.assertEqual(r.returncode, 0, r.stderr)
        e = load(self.out)["entries"]
        self.assertEqual(set(e), {"Foo1", "BarChoice_", "BazV01", "QuxCode"})
        self.assertEqual(e["Foo1"]["checksum"], "chk-foo")
        self.assertEqual((e["BarChoice_"]["status"], e["BarChoice_"]["removalDate"]), ("Obsolete", "2027-01-01"))
        self.assertEqual(e["QuxCode"]["checksum"], "chk-qux")

    def test_a_type_absent_from_the_snapshot_is_a_deletion_candidate(self):
        write(self.tsv, "MSGCOMP\tOther\tid-other\tRegistered\t—\tchk\tdef\n")
        self.build()
        self.assertEqual(load(self.out)["entries"]["Foo1"]["status"], "NOT_FOUND_IN_CURRENT_SNAPSHOT")

    def test_strict_fails_when_a_validated_type_has_no_isoid(self):
        os.remove(os.path.join(self.m, "src", "Messages", "Components", "IFoo1.cs"))
        self.assertEqual(self.build().returncode, 0)
        self.assertEqual(self.build("--strict").returncode, 1)

    def test_a_missing_model_repository_is_an_error_not_an_empty_manifest(self):
        r = run(BUILD, self.tsv, "--messages", os.path.join(self.m, "nope"), "--primitives", self.p, "--out", self.out)
        self.assertEqual(r.returncode, 2)

    def test_a_superseding_message_in_a_claimed_area_is_found(self):
        tests = os.path.join(self.tmp.name, "CoverageCompletenessTests.cs")
        write(tests, "public static readonly Type[] FullySupportedMessages =\n[\n    typeof(IBazV01),\n];\n")
        r = run(GAPS, self.tsv, "--coverage-tests-file", tests, "--fully-covered-areas", "pain")
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn("BazV02", r.stdout)


class RepositoryLayoutTests(unittest.TestCase):
    def test_the_default_paths_exist(self):
        sys.path.insert(0, HERE)
        import check_message_coverage_gaps as gaps
        import build_coverage_checksums as build

        self.assertTrue(os.path.isfile(gaps.DEFAULT_COVERAGE_TESTS_FILE), gaps.DEFAULT_COVERAGE_TESTS_FILE)
        self.assertTrue(os.path.isdir(os.path.join(build.FV_ROOT, "Validators")))
        self.assertTrue(os.path.isfile(build.DEFAULT_OUT))
        self.assertEqual(os.path.abspath(build.REPO_ROOT), REPO_ROOT)


if __name__ == "__main__":
    unittest.main()
