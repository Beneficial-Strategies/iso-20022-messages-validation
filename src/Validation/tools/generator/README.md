# The validator generator (prototype)

Writes the validators of the interfaces from the ISO 20022 specification, as plain C# that a reader can follow. This is the
prototype of #19: **no abbreviated validators; every interface has one, derived in full from the specification.**
Nothing here is used by the package yet.

## What it does

`generate_validators.py` takes a message (for example `pacs.008.001.14`), finds everything the message reaches, and writes one
validator per message and component:

* the structure: a required member is checked (`NotNull`, or `NotDefault` for a struct), a collection that needs an item is
  checked for one, each child gets its own validator (injected, with a constructor that builds the defaults);
* a member whose type is an open code (one of the 171 code types whose values come from outside the model, `IIsoExternalCode`) is
  checked by the validator of its code set, which is injected; the generator writes that validator too, unless one is hand-written. It
  reads the registry of the code set, so `AddIso20022LiveExternalCodes()` checks it against the live list. The code types that are
  enums are closed by the type and need nothing;
* a choice is validated alternative by alternative (`<Choice>_Validator`, an `InlineValidator` per alternative registered with
  `SetVariantValidators`), from the variant interfaces of the model: the `Value` of an alternative is required when the interface
  says so and is checked by its own validator, and so is any other member of it. The hand-written choice validators were mostly empty
  (46 of 62), so they are no longer reused;
* every constraint of the specification that has a machine-readable expression (a `RuleDefinition`), as a rule that carries the
  ISO name of the constraint, a reading of it in one line, and the specification's own text in the comment and the message;
* every constraint that has no expression (a rule in prose, or a guideline) as a comment with its text, and a line in
  `report.json`: it is **not** implemented, and the report says so. These are written by hand, once for each distinct text.

The output is a set of files meant to be **checked in**: a regeneration is a diff in git, one file per type, so that a change
for one message can be seen to touch another. The loop variables are numbered again in each file for that reason, and two runs
give identical files.

## Rules read from the prose

Most of the rules that the specification gives only in prose are plain: one element is present or absent depending on another, two
are not both present, an amount is the sum of the items, a currency is one in all items. Those are **read once** from their text, by
a person or an AI that understands the rule, and the reading is kept as data in `translations/<RuleName>.<hash>.json`: the rule
name and text, a one-line reading, and the rule in the same terms the specification's own expressions use (`Presence`,
`Absence`, `EqualToValue`, ... and one more of ours, `SameInAll`, for "the same in all occurrences"; `when` is the condition, `must`
the consequence). The generator turns it into C# like any other expression, and says in the generated file that the rule is
read from the prose and where.

The vocabulary of a reading is the specification's own (`Presence`, `Absence`, `EqualToValue`, `DifferentFromValue`, `EqualToNode`,
`DifferentFromNode`, `WithInList`) and three of ours: `SameInAll` (the same value, for example a currency, in all items), `CountEquals`
(a number of occurrences) and `IsBranchOf` (an institution is a branch of another, an error only when both carry the same kind of
identifier and they differ). A rule has `must` (the consequence) and optionally `when` (the condition); `each` names a collection,
and then `eachWhen` and `must` are read on the same item (so "in each transaction, if A then B" is not read across transactions).
Three flags settle what the specification's text does not: `alternatives` (the same rule where the element is elsewhere in another
version of the type), `lenient_codes` (the rule lists codes of the newest code set, and an older version of the type lacks some: a
code the type cannot hold is never the value), and `vacuous_without_condition_element` (the condition names an element the type
does not have, so the rule never applies). A file with `known_issue` is a rule that cannot be checked on the message (it is listed in
`docs/KnownRuleChallenges.md`, and is neither an error nor pending).

* The file name is the rule's name and a hash of its text, so **a change in the specification's text makes the reading stop
  applying** (the rule is pending again) instead of silently applying to a rule that has changed.
* The same text is read once, however many types carry it. If a reading does not fit a type (the text names an element that the
  type does not have, which is a mistake in the specification's text for that type), the rule stays pending for that type, with
  the reason, and is settled there by hand.
* A rule that cannot be a reading but can be checked is written in C# (next section; a file with `"hand": "why"` says so).
* **A new rule in prose** (a snapshot added a type, or changed a text) is pending. `generate_validators.py ... --scaffold DIR` writes
  one stub per such rule into `DIR`, already named as the generator looks for it: the exact text, the first type that has it (and
  `also_in`), that type's members with their cardinalities, and an empty `rules`. To settle it: write `reading` and `rules` (or
  `known_issue`, or `hand`), move the file into `translations/`, run the generator and the oracle, and add a test for the reading.
  `rule_coverage.py --list pending` shows what is left. The stub is not read until it is in `translations/`.
* Each reading is reviewed against its text before it is kept, and the validators that use it get tests when they replace the
  existing ones.

## What is written by hand

Some rules cannot be generated: the 1,000 or so whose only statement is prose, the 28 whose expression is a phrase, a few that
refer to an element the type does not have (the rule is of the message that contains it), and a few written as text instead of a
rule definition. They are **not left out**: each is written by hand, once, from what it means.

A type with such a rule is generated as a `partial` class that ends its constructor with `AddHandWrittenRules()`. The hand-written
rules are in `<Type>Validator.Rules.cs` next to it, which the generator never touches, so git shows what was generated and what
was written by a person, rule by rule. The rule keeps the ISO name (`.WithName("ChargesAccountAgentRule")`), and that name is how
the generator finds it: a rule it does not generate and does not find there is **pending**, listed in `report.json` and marked
`NOT IMPLEMENTED` in the generated file. A validator with a pending rule is not complete, and is not put in the package.

A rule that cannot be checked on the message at all is not an error and not a warning: it is a `known_issue`, listed in `docs/KnownRuleChallenges.md`.

A component can be generated on its own (`--type PostalAddress27`, with what it reaches), for finishing a validator that already exists.

## The reading of the rule language

The 7,500 expressions of the specification use eight rule types (`Presence`, `Absence`, `EqualToValue`, `EqualToNode`,
`DifferentFromValue`, `DifferentFromNode`, `WithInList`, `NotWithInList`) in two shapes. The reading used:

* `SimpleRule`: `mustBe` always holds. `ComplexRule`: if `onCondition` holds, `mustBe` holds. The connector (`AND`, `OR`) of a
  section joins its rules.
* `Presence` / `Absence`: the element is there / is not (for a collection, any item / no item).
* A path with `[*]`: the rule holds for **every** item (`Absence` of `A[*]/B` is "no item has a `B`"); `[1]`: the first item.
* `sum of` and `number of occurrences of` on the right of `EqualToValue`; `@Currency` is the currency of an amount.
* `WithInList`: the code is one of the codes of the named code set.

Three phrasings of a count (`number of occurrences of X`, `Number Occurrences X`) are read as the number of items. An expression that
compares with a **phrase** (`Branch of DebtorAgent`, 28 times in the data) describes the rule instead of stating it; compared
literally it would refuse every message, so it is not generated, and the report lists it as unsupported (a rule to write by hand).

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

For `pacs.008.001.14`: 232 tests, 218 pass, 14 are known differences. Eleven are rules of the specification the hand-written
validators do not have (and whose tests use data that breaks them); two are a rule the hand-written validator adds that the
specification's constraints do not state (an amount of zero is refused).

For `pain.001.001.13` (a second message; 67 generated validators): 195 tests, 190 pass, 5 are known differences, all one rule of the
specification (`NonChequePaymentMethodRule`) that the hand-written validator lacks.

`pain.008.001.12`: 178 tests, 177 pass, 1 known difference. All 214 messages of `pacs` and `pain` (1,095 types) generate and compile together: 814 tests (6 of them of the helpers in `oracle_tests/`), 706 pass, 108 are known differences (`known_differences/pacs,pain.tsv`, each with its reason). `head.001.001.02` (the business application header, which has no
hand-written validators at all) generates and compiles, including the validators of four open codes that were generated.

Of the 7,525 expressions in the specification, 7,438 (98.8%) generate. The rest are the hand-written group above.

A rule that names an alternative of a choice (`DeliveryMethod/Code`) is read as the variant interface of the choice
(`DeliveryMethod as Choices.ChequeDeliveryMethod1Choice.ICode`) and, when compared with a value, by its `Value`.

```
python3 run_oracle.py --census <folder of the pages> --message pacs.008.001.14 \
    [--messages <clone of iso-20022-messages>] [--primitives <clone of iso-20022-primitives>]
python3 -m unittest -q test_generator
```

## Not done

* The constraints with no expression (about half), and the facets of the simple types (not in the data).
* More than one message at a time (each message is generated and checked on its own so far), the choices' own constraints (none seen), the hand-written rules themselves (none written yet), and the index that lets the DI load a family of messages (or one component) with what it needs.

## How much is implemented

`python3 rule_coverage.py --census <pages> --areas pacs,pain` counts the rules of the messages of those areas (all versions) and what
the generator does with each: generated from the specification's expression, read from its prose, a known issue, or still to do. It
also counts the members that the types check by themselves. `--list prose` lists the rules still in prose, one text per line.
The reading of the results is in `docs/KnownRuleChallenges.md`.
