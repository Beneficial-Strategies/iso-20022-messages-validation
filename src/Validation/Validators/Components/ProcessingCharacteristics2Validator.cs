// Copyright 2026 Jeff Ward, Beneficial Strategies. Usage subject to license of enclosing library.

namespace BeneficialStrategies.Iso20022.Messages.Validation.Components;

/// <summary>
/// Validates <see cref="IProcessingCharacteristics2"/> per the ISO 20022 specification.
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
///   <item><term>DealingCurrencyAccepted</term><description>ValueList&lt;T&gt; = [] allows empty, spec requires Min=1..&#8734;</description></item>
/// </list>
/// </remarks>
public class ProcessingCharacteristics2Validator : AbstractValidator<IProcessingCharacteristics2>
{
    /// <summary>
    /// Initializes a new instance of the validator for <see cref="IProcessingCharacteristics2"/>.
    /// </summary>
    public ProcessingCharacteristics2Validator()
    {
        // Required members (1..1): the interface marks them only by type, so a null or default is refused here.
        RuleFor(x => x.InitialInvestment).NotNull().WithMessage("ProcessingCharacteristics2.InitialInvestment is required (1..1).");
        RuleFor(x => x.SubsequentInvestment).NotNull().WithMessage("ProcessingCharacteristics2.SubsequentInvestment is required (1..1).");
        RuleFor(x => x.AmountIndicator).NotDefault().WithMessage("ProcessingCharacteristics2.AmountIndicator is required (1..1).");
        RuleFor(x => x.UnitsIndicator).NotDefault().WithMessage("ProcessingCharacteristics2.UnitsIndicator is required (1..1).");
        RuleFor(x => x.MainFundOrderDeskLocation).NotNull().WithMessage("ProcessingCharacteristics2.MainFundOrderDeskLocation is required (1..1).");
        RuleFor(x => x.DealingCutOffTime).NotDefault().WithMessage("ProcessingCharacteristics2.DealingCutOffTime is required (1..1).");
        RuleFor(x => x.DealingCutOffTimeFrame).NotNull().WithMessage("ProcessingCharacteristics2.DealingCutOffTimeFrame is required (1..1).");
        RuleFor(x => x.DealingFrequencyDescription).NotDefault().WithMessage("ProcessingCharacteristics2.DealingFrequencyDescription is required (1..1).");
        RuleFor(x => x.SettlementCycle).NotNull().WithMessage("ProcessingCharacteristics2.SettlementCycle is required (1..1).");

        RuleFor(x => x.DealingCurrencyAccepted)
            .NotEmpty()
            .WithMessage("ProcessingCharacteristics2.DealingCurrencyAccepted must contain at least one element (1..∞).");
    }
}
