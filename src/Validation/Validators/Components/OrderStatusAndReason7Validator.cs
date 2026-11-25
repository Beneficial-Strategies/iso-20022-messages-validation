// Copyright 2026 Jeff Ward, Beneficial Strategies. Usage subject to license of enclosing library.

namespace BeneficialStrategies.Iso20022.Messages.Validation.Components;

/// <summary>
/// Validates <see cref="IOrderStatusAndReason7"/> per the ISO 20022 specification.
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
///   <item><term>Rejected</term><description>ValueList&lt;T&gt; = [] allows empty, spec requires Min=1..10</description></item>
/// </list>
/// </remarks>
[Obsolete("Marked obsolete in the ISO 20022 2026-06-26 snapshot. Removal date: 2016-09-08.")]
public class OrderStatusAndReason7Validator : AbstractValidator<IOrderStatusAndReason7>
{
    /// <summary>
    /// Initializes a new instance of the validator for <see cref="IOrderStatusAndReason7"/>.
    /// </summary>
    public OrderStatusAndReason7Validator()
    {
        // Required members (1..1): the interface marks them only by type, so a null or default is refused here.
        RuleFor(x => x.Cancelled).NotNull().WithMessage("OrderStatusAndReason7.Cancelled is required (1..1).");
        RuleFor(x => x.ConditionallyAccepted).NotNull().WithMessage("OrderStatusAndReason7.ConditionallyAccepted is required (1..1).");
        RuleFor(x => x.Suspended).NotNull().WithMessage("OrderStatusAndReason7.Suspended is required (1..1).");
        RuleFor(x => x.PartiallySettled).NotNull().WithMessage("OrderStatusAndReason7.PartiallySettled is required (1..1).");

        RuleFor(x => x.Rejected)
            .NotEmpty()
            .WithMessage("OrderStatusAndReason7.Rejected must contain at least one element (1..10).");
    }
}
