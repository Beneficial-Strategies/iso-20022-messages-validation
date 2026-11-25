// Copyright 2026 Jeff Ward, Beneficial Strategies. Usage subject to license of enclosing library.

namespace BeneficialStrategies.Iso20022.Messages.Validation.Components;

/// <summary>
/// Validates <see cref="IBaseline5"/> per the ISO 20022 specification.
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
///   <item><term>PaymentTerms</term><description>ValueList&lt;T&gt; = [] allows empty, spec requires Min=1..&#8734;</description></item>
/// </list>
/// </remarks>
[Obsolete("Marked obsolete in the ISO 20022 2026-06-26 snapshot. Removal date: 2016-09-08.")]
public class Baseline5Validator : AbstractValidator<IBaseline5>
{
    /// <summary>
    /// Initializes a new instance of the validator for <see cref="IBaseline5"/>.
    /// </summary>
    public Baseline5Validator()
    {
        // Required members (1..1): the interface marks them only by type, so a null or default is refused here.
        RuleFor(x => x.SubmitterBaselineIdentification).NotNull().WithMessage("Baseline5.SubmitterBaselineIdentification is required (1..1).");
        RuleFor(x => x.PurchaseOrderReference).NotNull().WithMessage("Baseline5.PurchaseOrderReference is required (1..1).");
        RuleFor(x => x.Buyer).NotNull().WithMessage("Baseline5.Buyer is required (1..1).");
        RuleFor(x => x.Seller).NotNull().WithMessage("Baseline5.Seller is required (1..1).");
        RuleFor(x => x.BuyerBank).NotNull().WithMessage("Baseline5.BuyerBank is required (1..1).");
        RuleFor(x => x.SellerBank).NotNull().WithMessage("Baseline5.SellerBank is required (1..1).");
        RuleFor(x => x.Goods).NotNull().WithMessage("Baseline5.Goods is required (1..1).");
        RuleFor(x => x.CommercialDataSetRequired).NotNull().WithMessage("Baseline5.CommercialDataSetRequired is required (1..1).");
        RuleFor(x => x.IntentToPayExpected).NotDefault().WithMessage("Baseline5.IntentToPayExpected is required (1..1).");

        RuleFor(x => x.PaymentTerms)
            .NotEmpty()
            .WithMessage("Baseline5.PaymentTerms must contain at least one element (1..∞).");
    }
}
