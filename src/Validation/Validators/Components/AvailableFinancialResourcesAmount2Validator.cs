// Copyright 2026 Jeff Ward, Beneficial Strategies. Usage subject to license of enclosing library.

namespace BeneficialStrategies.Iso20022.Messages.Validation.Components;

/// <summary>
/// Validates <see cref="IAvailableFinancialResourcesAmount2"/> per the ISO 20022 specification.
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
///   <item><term>CCPSkinInTheGame</term><description>ValueList&lt;T&gt; = [] allows empty, spec requires Min=1..&#8734;</description></item>
/// </list>
/// </remarks>
public class AvailableFinancialResourcesAmount2Validator : AbstractValidator<IAvailableFinancialResourcesAmount2>
{
    /// <summary>
    /// Initializes a new instance of the validator for <see cref="IAvailableFinancialResourcesAmount2"/>.
    /// </summary>
    public AvailableFinancialResourcesAmount2Validator()
    {
        // Required members (1..1): the interface marks them only by type, so a null or default is refused here.
        RuleFor(x => x.TotalInitialMargin).NotNull().WithMessage("AvailableFinancialResourcesAmount2.TotalInitialMargin is required (1..1).");
        RuleFor(x => x.TotalPrefundedDefaultFund).NotNull().WithMessage("AvailableFinancialResourcesAmount2.TotalPrefundedDefaultFund is required (1..1).");
        RuleFor(x => x.OtherDefaultFundContribution).NotNull().WithMessage("AvailableFinancialResourcesAmount2.OtherDefaultFundContribution is required (1..1).");
        RuleFor(x => x.UnfundedMemberCommitment).NotNull().WithMessage("AvailableFinancialResourcesAmount2.UnfundedMemberCommitment is required (1..1).");
        RuleFor(x => x.UnfundedThirdPartyCommitment).NotNull().WithMessage("AvailableFinancialResourcesAmount2.UnfundedThirdPartyCommitment is required (1..1).");

        RuleFor(x => x.CCPSkinInTheGame)
            .NotEmpty()
            .WithMessage("AvailableFinancialResourcesAmount2.CCPSkinInTheGame must contain at least one element (1..∞).");
    }
}
