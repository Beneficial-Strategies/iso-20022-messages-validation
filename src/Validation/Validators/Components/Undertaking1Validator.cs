// Copyright 2026 Jeff Ward, Beneficial Strategies. Usage subject to license of enclosing library.

namespace BeneficialStrategies.Iso20022.Messages.Validation.Components;

/// <summary>
/// Validates <see cref="IUndertaking1"/> per the ISO 20022 specification.
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
///   <item><term>Beneficiary</term><description>ValueList&lt;T&gt; = [] allows empty, spec requires Min=1..&#8734;</description></item>
/// </list>
/// </remarks>
[Obsolete("Marked obsolete in the ISO 20022 2026-06-26 snapshot. Removal date: 2017-09-08.")]
public class Undertaking1Validator : AbstractValidator<IUndertaking1>
{
    /// <summary>
    /// Initializes a new instance of the validator for <see cref="IUndertaking1"/>.
    /// </summary>
    public Undertaking1Validator()
    {
        // Required members (1..1): the interface marks them only by type, so a null or default is refused here.
        RuleFor(x => x.ApplicantReferenceNumber).NotDefault().WithMessage("Undertaking1.ApplicantReferenceNumber is required (1..1).");
        RuleFor(x => x.Purpose).NotDefault().WithMessage("Undertaking1.Purpose is required (1..1).");
        RuleFor(x => x.Type).NotNull().WithMessage("Undertaking1.Type is required (1..1).");
        RuleFor(x => x.Obligor).NotNull().WithMessage("Undertaking1.Obligor is required (1..1).");
        RuleFor(x => x.Issuer).NotNull().WithMessage("Undertaking1.Issuer is required (1..1).");
        RuleFor(x => x.CounterUndertakingIndicator).NotDefault().WithMessage("Undertaking1.CounterUndertakingIndicator is required (1..1).");
        RuleFor(x => x.UndertakingAmount).NotNull().WithMessage("Undertaking1.UndertakingAmount is required (1..1).");
        RuleFor(x => x.ExpiryDetails).NotNull().WithMessage("Undertaking1.ExpiryDetails is required (1..1).");
        RuleFor(x => x.GovernanceRulesAndLaw).NotNull().WithMessage("Undertaking1.GovernanceRulesAndLaw is required (1..1).");
        RuleFor(x => x.UndertakingWording).NotNull().WithMessage("Undertaking1.UndertakingWording is required (1..1).");
        RuleFor(x => x.DeliveryChannel).NotNull().WithMessage("Undertaking1.DeliveryChannel is required (1..1).");

        RuleFor(x => x.Beneficiary)
            .NotEmpty()
            .WithMessage("Undertaking1.Beneficiary must contain at least one element (1..∞).");
    }
}
