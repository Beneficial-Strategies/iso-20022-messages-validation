// Copyright 2026 Jeff Ward, Beneficial Strategies. Usage subject to license of enclosing library.

namespace BeneficialStrategies.Iso20022.Messages.Validation.Components;

/// <summary>
/// Validates <see cref="IPaymentInstructionInformation4"/> per the ISO 20022 specification.
/// </summary>
/// <remarks>
/// TODO: Abbreviated validator — only enforces the known Defect 2 minimum-collection-size gap(s)
/// below. NOT yet reviewed for full spec compliance (other field-level constraints, cross-field
/// rules) or covered by a test file. Full treatment is being done first for CAMT-reachable
/// components; this one was not in that reachable set as of 2026-08-13. See
/// docs/multiplicity-audit-2026-08.md and docs/multiplicity-defect2-2026-08.tsv.
///
/// Known model defect(s):
/// <list type="table">
///   <item><term>DirectDebitTransactionInformation</term><description>ValueList&lt;T&gt; = [] allows empty, spec requires Min=1..&#8734;</description></item>
/// </list>
/// </remarks>
[Obsolete("Marked obsolete in the ISO 20022 2026-06-26 snapshot. Removal date: 2018-08-07.")]
public class PaymentInstructionInformation4Validator : AbstractValidator<IPaymentInstructionInformation4>
{
    /// <summary>
    /// Initializes a new instance of the validator for <see cref="IPaymentInstructionInformation4"/>.
    /// </summary>
    public PaymentInstructionInformation4Validator()
    {
        // Required members (1..1): the interface marks them only by type, so a null or default is refused here.
        RuleFor(x => x.PaymentInformationIdentification).NotDefault().WithMessage("PaymentInstructionInformation4.PaymentInformationIdentification is required (1..1).");
        RuleFor(x => x.RequestedCollectionDate).NotDefault().WithMessage("PaymentInstructionInformation4.RequestedCollectionDate is required (1..1).");
        RuleFor(x => x.Creditor).NotNull().WithMessage("PaymentInstructionInformation4.Creditor is required (1..1).");
        RuleFor(x => x.CreditorAccount).NotNull().WithMessage("PaymentInstructionInformation4.CreditorAccount is required (1..1).");
        RuleFor(x => x.CreditorAgent).NotNull().WithMessage("PaymentInstructionInformation4.CreditorAgent is required (1..1).");

        RuleFor(x => x.DirectDebitTransactionInformation)
            .NotEmpty()
            .WithMessage("PaymentInstructionInformation4.DirectDebitTransactionInformation must contain at least one element (1..∞).");
    }
}
