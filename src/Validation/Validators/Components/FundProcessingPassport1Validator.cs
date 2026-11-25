// Copyright 2026 Jeff Ward, Beneficial Strategies. Usage subject to license of enclosing library.

namespace BeneficialStrategies.Iso20022.Messages.Validation.Components;

/// <summary>
/// Validates <see cref="IFundProcessingPassport1"/> per the ISO 20022 specification.
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
///   <item><term>SettlementDetails</term><description>ValueList&lt;T&gt; = [] allows empty, spec requires Min=1..&#8734;</description></item>
/// </list>
/// </remarks>
[Obsolete("Marked obsolete in the ISO 20022 2026-06-26 snapshot. Removal date: 2016-09-08.")]
public class FundProcessingPassport1Validator : AbstractValidator<IFundProcessingPassport1>
{
    /// <summary>
    /// Initializes a new instance of the validator for <see cref="IFundProcessingPassport1"/>.
    /// </summary>
    public FundProcessingPassport1Validator()
    {
        // Required members (1..1): the interface marks them only by type, so a null or default is refused here.
        RuleFor(x => x.UpdatedDate).NotNull().WithMessage("FundProcessingPassport1.UpdatedDate is required (1..1).");
        RuleFor(x => x.SecurityIdentification).NotNull().WithMessage("FundProcessingPassport1.SecurityIdentification is required (1..1).");
        RuleFor(x => x.MainFundOrderDesk).NotNull().WithMessage("FundProcessingPassport1.MainFundOrderDesk is required (1..1).");
        RuleFor(x => x.FundManagementCompany).NotNull().WithMessage("FundProcessingPassport1.FundManagementCompany is required (1..1).");
        RuleFor(x => x.FundDetails).NotNull().WithMessage("FundProcessingPassport1.FundDetails is required (1..1).");
        RuleFor(x => x.ValuationDealingCharacteristics).NotNull().WithMessage("FundProcessingPassport1.ValuationDealingCharacteristics is required (1..1).");
        RuleFor(x => x.InvestmentRestrictions).NotNull().WithMessage("FundProcessingPassport1.InvestmentRestrictions is required (1..1).");
        RuleFor(x => x.SubscriptionProcessingCharacteristics).NotNull().WithMessage("FundProcessingPassport1.SubscriptionProcessingCharacteristics is required (1..1).");
        RuleFor(x => x.RedemptionProcessingCharacteristics).NotNull().WithMessage("FundProcessingPassport1.RedemptionProcessingCharacteristics is required (1..1).");

        RuleFor(x => x.SettlementDetails)
            .NotEmpty()
            .WithMessage("FundProcessingPassport1.SettlementDetails must contain at least one element (1..∞).");
    }
}
