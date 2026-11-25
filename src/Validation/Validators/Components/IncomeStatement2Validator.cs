// Copyright 2026 Jeff Ward, Beneficial Strategies. Usage subject to license of enclosing library.

namespace BeneficialStrategies.Iso20022.Messages.Validation.Components;

/// <summary>
/// Validates <see cref="IIncomeStatement2"/> per the ISO 20022 specification.
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
///   <item><term>ClearingMemberFee</term><description>ValueList&lt;T&gt; = [] allows empty, spec requires Min=1..&#8734;</description></item>
/// </list>
/// </remarks>
public class IncomeStatement2Validator : AbstractValidator<IIncomeStatement2>
{
    /// <summary>
    /// Initializes a new instance of the validator for <see cref="IIncomeStatement2"/>.
    /// </summary>
    public IncomeStatement2Validator()
    {
        // Required members (1..1): the interface marks them only by type, so a null or default is refused here.
        RuleFor(x => x.OtherOperatingRevenue).NotNull().WithMessage("IncomeStatement2.OtherOperatingRevenue is required (1..1).");
        RuleFor(x => x.OperatingExpenses).NotNull().WithMessage("IncomeStatement2.OperatingExpenses is required (1..1).");
        RuleFor(x => x.OperatingProfitOrLoss).NotNull().WithMessage("IncomeStatement2.OperatingProfitOrLoss is required (1..1).");
        RuleFor(x => x.NetInterestIncome).NotNull().WithMessage("IncomeStatement2.NetInterestIncome is required (1..1).");
        RuleFor(x => x.OtherNonOperatingRevenue).NotNull().WithMessage("IncomeStatement2.OtherNonOperatingRevenue is required (1..1).");
        RuleFor(x => x.NonOperatingExpenses).NotNull().WithMessage("IncomeStatement2.NonOperatingExpenses is required (1..1).");
        RuleFor(x => x.PreTaxProfitOrLoss).NotNull().WithMessage("IncomeStatement2.PreTaxProfitOrLoss is required (1..1).");
        RuleFor(x => x.PostTaxProfitOrLoss).NotNull().WithMessage("IncomeStatement2.PostTaxProfitOrLoss is required (1..1).");

        RuleFor(x => x.ClearingMemberFee)
            .NotEmpty()
            .WithMessage("IncomeStatement2.ClearingMemberFee must contain at least one element (1..∞).");
    }
}
