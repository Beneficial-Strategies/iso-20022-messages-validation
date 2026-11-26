// Copyright 2026 Jeff Ward, Beneficial Strategies. Usage subject to license of enclosing library.

namespace BeneficialStrategies.Iso20022.Messages.Validation.Components;

/// <summary>
/// Validates <see cref="ISwitchExecution3"/> per the ISO 20022 specification.
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
///   <item><term>RedemptionLegDetails</term><description>ValueList&lt;T&gt; = [] allows empty, spec requires Min=1..&#8734;</description></item>
///   <item><term>SubscriptionLegDetails</term><description>ValueList&lt;T&gt; = [] allows empty, spec requires Min=1..&#8734;</description></item>
/// </list>
/// </remarks>
[Obsolete("Marked obsolete in the ISO 20022 2026-06-26 snapshot. Removal date: 2016-09-08.")]
public class SwitchExecution3Validator : AbstractValidator<ISwitchExecution3>
{
    /// <summary>
    /// Initializes a new instance of the validator for <see cref="ISwitchExecution3"/>.
    /// </summary>
    public SwitchExecution3Validator()
    {
        // Required members (1..1): the interface marks them only by type, so a null or default is refused here.
        RuleFor(x => x.DealReference).NotDefault().WithMessage("SwitchExecution3.DealReference is required (1..1).");
        RuleFor(x => x.OrderReference).NotDefault().WithMessage("SwitchExecution3.OrderReference is required (1..1).");
        RuleFor(x => x.InvestmentAccountDetails).NotNull().WithMessage("SwitchExecution3.InvestmentAccountDetails is required (1..1).");

        RuleFor(x => x.RedemptionLegDetails)
            .NotEmpty()
            .WithMessage("SwitchExecution3.RedemptionLegDetails must contain at least one element (1..∞).");

        RuleFor(x => x.SubscriptionLegDetails)
            .NotEmpty()
            .WithMessage("SwitchExecution3.SubscriptionLegDetails must contain at least one element (1..∞).");
    }
}
