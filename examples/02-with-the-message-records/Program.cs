// Example 02: with the message records.
// Shows:  a rule across fields that no C# type can express, on a ready-made record of camt.056.
// Needs:  BeneficialStrategies.Iso20022.Messages.Validation and BeneficialStrategies.Iso20022.Messages.Records.
// Prints: a well-formed cancellation request is valid; the same with the case identified in two places is not.
using BeneficialStrategies.Iso20022.camt;
using BeneficialStrategies.Iso20022.Choices.Party40Choice;
using BeneficialStrategies.Iso20022.Components;
using BeneficialStrategies.Iso20022.Messages.Validation.camt;

var validator = new FIToFIPaymentCancellationRequestV10Validator();

// <snippet valid>
// A well-formed cancellation request.
var request = new FIToFIPaymentCancellationRequestV10
{
    Assignment = new CaseAssignment5
    {
        Identification = "CASE-2026-0001",
        Assigner = new Agent { FinancialInstitutionIdentification = new() { BICFI = "AAAAGB2L" } },
        Assignee = new Agent { FinancialInstitutionIdentification = new() { BICFI = "BBBBUS33" } },
        CreationDateTime = new DateTime(2026, 8, 17, 9, 0, 0),
    },
    Underlying = [new UnderlyingTransaction28 { TransactionInformation = [new PaymentTransaction137()] }],
};

Console.WriteLine($"IsValid={validator.Validate(request).IsValid}");   // IsValid=True
// </snippet>

// <snippet invalid>
// The same message with a case identification at the message level and at the transaction level: a rule of the specification
// (MessageOrGroupCaseRule) that no property type can enforce, since both places are optional on their own.
Case5 TheCase() => new()
{
    Identification = "CASE-2026-0001",
    Creator = new Agent { FinancialInstitutionIdentification = new() { BICFI = "AAAAGB2L" } },
};

var twice = request with
{
    Case = TheCase(),
    Underlying = [new UnderlyingTransaction28 { TransactionInformation = [new PaymentTransaction137 { Case = TheCase() }] }],
};

var result = validator.Validate(twice);
Console.WriteLine($"IsValid={result.IsValid}");                        // IsValid=False
foreach (var error in result.Errors)
    Console.WriteLine($"  {error.PropertyName}: {error.ErrorMessage}");
// </snippet>
