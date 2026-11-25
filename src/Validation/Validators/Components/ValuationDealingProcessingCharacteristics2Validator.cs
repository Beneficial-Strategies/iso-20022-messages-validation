// Copyright 2026 Jeff Ward, Beneficial Strategies. Usage subject to license of enclosing library.

namespace BeneficialStrategies.Iso20022.Messages.Validation.Components;

/// <summary>
/// Validates <see cref="IValuationDealingProcessingCharacteristics2"/> per the ISO 20022 specification.
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
///   <item><term>PriceCurrency</term><description>ValueList&lt;T&gt; = [] allows empty, spec requires Min=1..&#8734;</description></item>
/// </list>
/// </remarks>
public class ValuationDealingProcessingCharacteristics2Validator : AbstractValidator<IValuationDealingProcessingCharacteristics2>
{
    /// <summary>
    /// Initializes a new instance of the validator for <see cref="IValuationDealingProcessingCharacteristics2"/>.
    /// </summary>
    public ValuationDealingProcessingCharacteristics2Validator()
    {
        // Required members (1..1): the interface marks them only by type, so a null or default is refused here.
        RuleFor(x => x.ValuationFrequencyDescription).NotDefault().WithMessage("ValuationDealingProcessingCharacteristics2.ValuationFrequencyDescription is required (1..1).");
        RuleFor(x => x.DecimalisationUnits).NotDefault().WithMessage("ValuationDealingProcessingCharacteristics2.DecimalisationUnits is required (1..1).");
        RuleFor(x => x.DecimalisationPrice).NotDefault().WithMessage("ValuationDealingProcessingCharacteristics2.DecimalisationPrice is required (1..1).");
        RuleFor(x => x.DualFundIndicator).NotDefault().WithMessage("ValuationDealingProcessingCharacteristics2.DualFundIndicator is required (1..1).");

        RuleFor(x => x.PriceCurrency)
            .NotEmpty()
            .WithMessage("ValuationDealingProcessingCharacteristics2.PriceCurrency must contain at least one element (1..∞).");
    }
}
