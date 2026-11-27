# Rules of the standard that are hard to implement

What we know about the rules of ISO 20022 that this package cannot yet check completely, and why. It is the source of the
"known issues": when every validator has been generated, each entry below that is still open becomes an issue, one per rule or one
per group of rules with the same profile.

The numbers are produced by `src/Validation/tools/generator/rule_coverage.py` from the specification as the ISO 20022 MCP server
serves it (snapshot of 2026-09-04). Run it again before a release; do not edit the numbers by hand.

## Scope of the first release: pacs and pain

Every message of the business areas `pacs` and `pain`, in every version the model has (98 and 116 message definitions, 214 in all),
and every component and choice they reach: **1,092 types**. The rest of the standard follows.

## What is counted

* A **constraint** is anything the specification attaches to a message, component or choice as a rule. A **guideline** is advice,
  not a rule a message can break (the name ends in `Guideline`). The UI layer is presumed to follow the guidelines, so they are
  credited and not counted as rules (468 in this scope).
* A **rule** is a constraint that is not a guideline. It is counted once for each type and version that carries it, because that is
  what a validator checks.
* The **facets of the simple types** (length, pattern, range, the codes of a code set, the currency of an amount) are checked by the
  types themselves, by their constructors, and are credited as their own line.
* Everything else in the structure (a member is required, a collection has at least or at most n items, a member is validated by
  its own validator) is checked by the generated validators.

| | |
|---|---:|
| **Rules of the specification** (guidelines excluded) | **2,549** |
| Implemented, from the specification's expression | 2,104 |
| Implemented, read from the specification's prose (`translations/`) | 264 |
| **Implemented** | **2,368 (92.9%)** |
| Not checkable on the message: the known issues of this file | 178 (7.0%) |
| Still to do | 3 (0.1%) |
| | |
| Guidelines, credited to the UI layer | 468 |
| Members checked by the type system (facets, codes, currencies), over 101 simple types | 3,241 |
| Members checked by the validators (required, multiplicity, validator of their own) | 6,182 |

Run `rule_coverage.py --areas pacs,pain` for the figures; do not edit them by hand. For the whole standard (15,747 rules) the same
script says 49.2% are implemented so far.

## The sentence for the release

> Of the **2,549** rules specified in the standard for payments (pacs and pain), **181** cannot easily be implemented because of
> interpretive or derivative challenges. This represents **7.1%** of the rules. The type system enforces a further 3,241 members
> (the formats, lengths and code sets of the standard), and 468 guidelines are left to the user interface. The rules for these will
> be tightened over time, with 100% the eventual goal.

The 181 are the 178 known issues and the 3 still to do, below. The numbers are the script's, at the snapshot date.

## The rule for a known issue

**A rule we cannot check on the message does not produce an error, or a warning.** A message that the standard would accept must not
be refused for a rule we do not understand. A rule we can only check in part is checked only where it can be decided (a branch of
an agent is an error only when both carry the same kind of identifier and they differ). Everything we do not check is written in
this file, and as a comment in the validator.

A reading that we have written ourselves (`translations/`) is held to the same standard: reviewed against the text, tested, and
when it is doubtful moved here and relaxed, not kept as an error.

## The known issues of pacs and pain (178)

| Rule | Where | Why it cannot be checked |
|---|---:|---|
| `SupplementaryDataRule` "the building block at message level must not be used to provide additional information about a transaction" | 168 | Whether text or data is about a transaction is a matter of meaning. |
| `SupplementaryDataRule` "may not be used without the explicit approval of a SEG" | 1 | Governance, not data. |
| `UnderlyingCustomerCreditTransferRule`, `UnderlyingFinancialInstitutionCreditTransferRule` "can only be present if present in the original transaction being returned" | 7 | Needs the original transaction, which is not in the message. |
| `Grouping1Rule` | 2 | Never applies: its condition is about `GroupHeader/Grouping`, which the later versions of the type do not have. |

## Still to do (3)

`Grouping2Rule` in two versions of the creditor payment activation request, and `SettlementMethodRule` in `FIToFIPaymentReversalV01`:
the text names an element (`CreditTransferTransactionInformation`, `OriginalGroupInformation`) that the type does not have. Settled by
hand once the right element is decided.

## Defects of the specification

These are mistakes in the specification's own data, found while reading every expression. Each needs a ruling, and some should be
reported to the maintainers.

| What | Count | State |
|---|---:|---|
| The expression compares a value with a **phrase** that describes the rule (`Branch of DebtorAgent`, in `ChargesAccountAgentRule`) | 28 | open: a rule about two agents (see below) |
| An expression names a member with a **misspelling** (`ReversedInterbankSttlementAmount`, `ReturnedInterbankSttlementAmount`) | 27 | read as the real member, by an explicit list in the generator |
| The `expression` field is **text or blank**, not a rule definition | 34 | open: read from the text |
| The text or expression names an **element the type does not have** (the text is copied from another version: `Cancellation(*)` in a type that has `Modification`) | 25 | open: settled type by type |
| `CashAccountServicerRule` names `AccountOwner` where `CashAccountServicer` is meant | 2 texts | needs a ruling |
| A rule of the containing message is on a **component** (`TransactionInformation` in `UnderlyingTransaction1`) | 12 | open: belongs at the message |
| The code of a rule is **not in the model's code set** (`CRQB`, `QRQC` of `IssuanceType1Code`) | a few | open |
| An expression's path goes **through a code** (`TransferStatus/Status/Status`) | 4 | open |
| The **expression and the text of a rule disagree** (`GroupReturnAndReturnReasonRule`: the expression adds a condition, "AdditionalInformation present", that the text does not have; the generated rule follows the expression and so never fires) | 1 found | open: found only where a hand-written test caught it |
| A **guideline reads as a rule** ("must equal the number of occurrences", "must not be repeated") | 10 (2 texts) | credited to the UI layer, as for all guidelines; to raise with the maintainers |
| `[*]` in an expression is read as "every item" (and, for presence, "there is an item"); **not confirmed** with the authors of the standard | all | to confirm |

## Interpretive challenges

Rules whose satisfaction cannot (or cannot completely) be measured on the message.

* **Bilateral agreement.** "Unless bilaterally agreed between the Sender and Receiver, ... must not contain information that can be
  provided in a structured field" (`HoldingAdditionalDetailsRule`, `AdditionalInformationRule`, 24 + 6 + 1 types, and more in the
  unread texts). Whether anything was agreed is outside the message; whether the free text "could be provided in a structured
  field" is a judgment about meaning. Known issue, relaxed.
* **A branch of the same agent.** `ChargesAccountAgentRule` (26 types): the charges account agent "must contain a branch of the
  debtor (creditor) agent". Measurable when both agents carry the same kind of identifier (BIC, clearing member, LEI) and partly
  when not. **Done in part**: an error only when both carry the same kind of identifier and the institutions differ (a BIC by its first eight characters; an LEI; a clearing member of the same system); silent otherwise.
* **References "in line with" something else** (`ReferenceRule`, 13 types): depends on the message the reference points to.
* **Governance, not data.** "May not be used without the explicit approval of a SEG", "SMPG has published market practice
  recommendations": not measurable. Known issue, silent.
* **A live register.** "The market identification code must be an active market at the time of reporting" (`ValidMICRule`): needs
  the register of MICs as an external source (the mechanism exists, `AddIso20022LiveExternalCodes`; the host does not serve that list).
* **ISO 15022 coexistence.** "During ISO 15022 - 20022 coexistence, Amount length must not be greater than 15" and the character-set
  rules: measurable, but they apply only to messages in a coexistence with the older standard, which the message does not say.
  Plan: not applied unless the consumer asks for them.
* **Interdependence across occurrences** ("one and only one BalanceType may be ELIG in all occurrences of HoldingBalance",
  "present in one or in all, not both"): measurable; wait for the reading.

## Derivative challenges

Rules that need something other than the message in front of the validator: another message of the same exchange (the original of a
status report, the payment a reversal reverses), the state of an account, or the date the message is processed. Not measurable by
a validator of one message. Known issue, silent; some can be offered as separate checks that take the other message.

## What changes against the validators that exist today

Replacing the hand-written validators with the complete ones changes what is accepted (see the list in
`known_differences/pacs,pain.tsv`, 108 tests of the old validators, each with its reason):

* **Refused now, was accepted:** the rules of the specification the old validators lacked (for example a `ChargesInformation` needs an
  `InstructedAmount`; an `IntermediaryAgent2` needs an `IntermediaryAgent1`; a collection that the specification requires at least
  once, such as `UnderlyingAcceptanceDetails` of a mandate report, now needs an item).
* **Accepted now, was refused:** an amount of zero (the specification has no such constraint), and what the old validators enforced
  from a guideline (an ultimate debtor that is the same as the debtor).

## Where each rule is kept

* `src/Validation/tools/generator/translations/` the readings of the prose rules, one file per distinct text.
* `<Type>Validator.Rules.cs` the rules written in C#, next to the validator.
* `report.json` of a generator run: `pending` lists the rules that are neither generated nor written.
* This file: why a rule is hard, and what we decided about it.

## Open decisions

1. How a warning is told from an error (`Severity.Warning` still makes `IsValid` false).
2. When a warning is raised (only when the rule's elements are present, not on every message).
3. Whether coexistence rules are opt-in.
4. The ruling on each defect above, and which are reported to the maintainers of the standard.
