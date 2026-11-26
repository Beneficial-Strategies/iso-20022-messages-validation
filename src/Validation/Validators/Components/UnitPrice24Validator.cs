// Copyright 2026 Jeff Ward, Beneficial Strategies. Usage subject to license of enclosing library.

namespace BeneficialStrategies.Iso20022.Messages.Validation.Components;

/// <summary>
/// Validates <see cref="IUnitPrice24"/> per the ISO 20022 specification.
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
///   <item><term>ValueInInvestmentCurrency</term><description>ValueList&lt;T&gt; = [] allows empty, spec requires Min=1..&#8734;</description></item>
/// </list>
/// </remarks>
public class UnitPrice24Validator : AbstractValidator<IUnitPrice24>
{
    /// <summary>
    /// Initializes a new instance of the validator for <see cref="IUnitPrice24"/>.
    /// </summary>
    public UnitPrice24Validator()
    {
        // Required members (1..1): the interface marks them only by type, so a null or default is refused here.
        RuleFor(x => x.PriceType).NotNull().WithMessage("UnitPrice24.PriceType is required (1..1).");
        RuleFor(x => x.ForExecutionIndicator).NotDefault().WithMessage("UnitPrice24.ForExecutionIndicator is required (1..1).");
        RuleFor(x => x.CumDividendIndicator).NotDefault().WithMessage("UnitPrice24.CumDividendIndicator is required (1..1).");
        RuleFor(x => x.EstimatedPriceIndicator).NotDefault().WithMessage("UnitPrice24.EstimatedPriceIndicator is required (1..1).");

        RuleFor(x => x.ValueInInvestmentCurrency)
            .NotEmpty()
            .WithMessage("UnitPrice24.ValueInInvestmentCurrency must contain at least one element (1..∞).");
    }
}
