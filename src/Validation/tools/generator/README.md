# The validator generator (prototype)

Writes the validators of the interfaces from the ISO 20022 specification, as plain C# that a reader can follow. This is the
prototype of #19: **no abbreviated validators; every interface has one, derived in full from the specification.**
Nothing here is used by the package yet.

## What it does

`generate_validators.py` takes a message (for example `pacs.008.001.14`), finds everything the message reaches, and writes one
validator per message and component:

* the structure: a required member is checked (`NotNull`, or `NotDefault` for a struct), a collection that needs an item is
  checked for one, each child gets its own validator (injected, with a constructor that builds the defaults);
* every constraint of the specification that has a machine-readable expression (a `RuleDefinition`), as a rule that carries the
  ISO name of the constraint, a reading of it in one line, and the specification's own text in the comment and the message;
* every constraint that has no expression (a rule in prose, or a guideline) as a comment with its text, and a line in
  `report.json`: it is **not** implemented, and the report says so. These are written by hand, once for each distinct text.

The output is a set of files meant to be **checked in**: a regeneration is a diff in git, one file per type, so that a change
for one message can be seen to touch another. The loop variables are numbered again in each file for that reason, and two runs
give identical files.

## The reading of the rule language

The 7,500 expressions of the specification use eight rule types (`Presence`, `Absence`, `EqualToValue`, `EqualToNode`,
`DifferentFromValue`, `DifferentFromNode`, `WithInList`, `NotWithInList`) in two shapes. The reading used:

* `SimpleRule`: `mustBe` always holds. `ComplexRule`: if `onCondition` holds, `mustBe` holds. The connector (`AND`, `OR`) of a
  section joins its rules.
* `Presence` / `Absence`: the element is there / is not (for a collection, any item / no item).
* A path with `[*]`: the rule holds for **every** item (`Absence` of `A[*]/B` is "no item has a `B`"); `[1]`: the first item.
* `sum of` and `number of occurrences of` on the right of `EqualToValue`; `@Currency` is the currency of an amount.
* `WithInList`: the code is one of the codes of the named code set.

This is a reading, checked against the hand-written validators below; it is not confirmed by the authors of the specification.

## The data

The generator reads the pages of the specification that the ISO 20022 MCP server serves as resources:
`iso20022://dictionary/<MessageComponent|ChoiceComponent>/details?take=2000&includeDefinition=true` (following `page.nextUri`)
and `iso20022://element/<business area id>/details?take=2000&includeDefinition=true` for the messages of each area. The pages
over 100 KB are saved to a file by the client; `save_census_page.py <file> <name>` copies one into the folder given as
`--census` and prints the address of the next page. The pages are not in this repository.

## Checking it

`run_oracle.py` runs the **hand-written tests** of `tests/Validation.Tests` against the generated validators, in a scratch
project under `artifacts/`. A test that fails is a difference between a hand-written validator and the specification (or a
generator bug), and each has to be read. `known_differences/<message>.tsv` lists, with the reason, the ones that are understood;
the run fails on any other, and on a listed one that stops failing.

For `pacs.008.001.14`: 166 tests, 153 pass, 13 are known differences. Eleven are rules of the specification the hand-written
validators do not have (and whose tests use data that breaks them); two are a rule the hand-written validator adds that the
specification's constraints do not state (an amount of zero is refused).

For `pain.001.001.13` (67 generated validators): 121 tests, 117 pass, 4 are known differences, all one rule of the
specification (`NonChequePaymentMethodRule`) that the hand-written validator lacks.

A rule that names an alternative of a choice (`DeliveryMethod/Code`) is read as the variant interface of the choice
(`DeliveryMethod as Choices.ChequeDeliveryMethod1Choice.ICode`) and, when compared with a value, by its `Value`.

```
python3 run_oracle.py --census <folder of the pages> --message pacs.008.001.14 \
    [--messages <clone of iso-20022-messages>] [--primitives <clone of iso-20022-primitives>]
python3 -m unittest -q test_generator
```

## Not done

* Code sets from outside ISO (the registry validators): the hand-written tests of `RegulatoryAuthority2` take a registry and
  are skipped.
* The constraints with no expression (about half), and the facets of the simple types (not in the data).
* Choices: the validators of the hand-written package are reused.
* More than one message at a time (each message is generated and checked on its own so far), and the index that lets the DI load a family of messages (or one component) with what it needs.
