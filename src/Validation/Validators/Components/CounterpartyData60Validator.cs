// Copyright 2026 Jeff Ward, Beneficial Strategies. Usage subject to license of enclosing library.

namespace BeneficialStrategies.Iso20022.Messages.Validation.Components;

/// <summary>
/// Validates <see cref="ICounterpartyData60"/> per the ISO 20022 specification.
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
///   <item><term>CounterpartyData</term><description>ValueList&lt;T&gt; = [] allows empty, spec requires Min=1..2</description></item>
/// </list>
/// </remarks>
public class CounterpartyData60Validator : AbstractValidator<ICounterpartyData60>
{
    /// <summary>
    /// Initializes a new instance of the validator for <see cref="ICounterpartyData60"/>.
    /// </summary>
    public CounterpartyData60Validator()
    {
        // Required members (1..1): the interface marks them only by type, so a null or default is refused here.
        RuleFor(x => x.ReportingDateTime).NotDefault().WithMessage("CounterpartyData60.ReportingDateTime is required (1..1).");
        RuleFor(x => x.ReportSubmittingEntity).NotNull().WithMessage("CounterpartyData60.ReportSubmittingEntity is required (1..1).");

        RuleFor(x => x.CounterpartyData)
            .NotEmpty()
            .WithMessage("CounterpartyData60.CounterpartyData must contain at least one element (1..2).");
    }
}
