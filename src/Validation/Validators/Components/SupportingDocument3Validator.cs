// Copyright 2026 Jeff Ward, Beneficial Strategies. Usage subject to license of enclosing library.

namespace BeneficialStrategies.Iso20022.Messages.Validation.Components;

/// <summary>
/// Validates <see cref="ISupportingDocument3"/> per the ISO 20022 specification.
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
///   <item><term>Entry</term><description>ValueList&lt;T&gt; = [] allows empty, spec requires Min=1..&#8734;</description></item>
/// </list>
/// </remarks>
public class SupportingDocument3Validator : AbstractValidator<ISupportingDocument3>
{
    /// <summary>
    /// Initializes a new instance of the validator for <see cref="ISupportingDocument3"/>.
    /// </summary>
    public SupportingDocument3Validator()
    {
        // Required members (1..1): the interface marks them only by type, so a null or default is refused here.
        RuleFor(x => x.SupportingDocumentIdentification).NotDefault().WithMessage("SupportingDocument3.SupportingDocumentIdentification is required (1..1).");
        RuleFor(x => x.Certificate).NotNull().WithMessage("SupportingDocument3.Certificate is required (1..1).");
        RuleFor(x => x.AccountOwner).NotNull().WithMessage("SupportingDocument3.AccountOwner is required (1..1).");
        RuleFor(x => x.AccountServicer).NotNull().WithMessage("SupportingDocument3.AccountServicer is required (1..1).");
        RuleFor(x => x.ContractReference).NotNull().WithMessage("SupportingDocument3.ContractReference is required (1..1).");

        RuleFor(x => x.Entry)
            .NotEmpty()
            .WithMessage("SupportingDocument3.Entry must contain at least one element (1..∞).");
    }
}
