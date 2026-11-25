// Copyright 2026 Jeff Ward, Beneficial Strategies. Usage subject to license of enclosing library.

namespace BeneficialStrategies.Iso20022.Messages.Validation.Components;

/// <summary>
/// Validates <see cref="IFinancingAgreementList1"/> per the ISO 20022 specification.
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
///   <item><term>Item</term><description>ValueList&lt;T&gt; = [] allows empty, spec requires Min=1..&#8734;</description></item>
/// </list>
/// </remarks>
[Obsolete("Marked obsolete in the ISO 20022 2026-06-26 snapshot. Removal date: 2016-09-08.")]
public class FinancingAgreementList1Validator : AbstractValidator<IFinancingAgreementList1>
{
    /// <summary>
    /// Initializes a new instance of the validator for <see cref="IFinancingAgreementList1"/>.
    /// </summary>
    public FinancingAgreementList1Validator()
    {
        // Required members (1..1): the interface marks them only by type, so a null or default is refused here.
        RuleFor(x => x.Identifier).NotDefault().WithMessage("FinancingAgreementList1.Identifier is required (1..1).");
        RuleFor(x => x.Date).NotDefault().WithMessage("FinancingAgreementList1.Date is required (1..1).");
        RuleFor(x => x.AgreementRequestor).NotNull().WithMessage("FinancingAgreementList1.AgreementRequestor is required (1..1).");
        RuleFor(x => x.AgreementResponder).NotNull().WithMessage("FinancingAgreementList1.AgreementResponder is required (1..1).");
        RuleFor(x => x.GuaranteeApplicant).NotNull().WithMessage("FinancingAgreementList1.GuaranteeApplicant is required (1..1).");
        RuleFor(x => x.GuaranteeBeneficiary).NotNull().WithMessage("FinancingAgreementList1.GuaranteeBeneficiary is required (1..1).");
        RuleFor(x => x.GuaranteeIssuer).NotNull().WithMessage("FinancingAgreementList1.GuaranteeIssuer is required (1..1).");
        RuleFor(x => x.ItemCount).NotDefault().WithMessage("FinancingAgreementList1.ItemCount is required (1..1).");

        RuleFor(x => x.Item)
            .NotEmpty()
            .WithMessage("FinancingAgreementList1.Item must contain at least one element (1..∞).");
    }
}
