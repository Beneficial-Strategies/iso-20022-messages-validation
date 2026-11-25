// Copyright 2026 Jeff Ward, Beneficial Strategies. Usage subject to license of enclosing library.

namespace BeneficialStrategies.Iso20022.Messages.Validation.Components;

/// <summary>
/// Validates <see cref="ILoanContract1"/> per the ISO 20022 specification.
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
///   <item><term>Buyer</term><description>ValueList&lt;T&gt; = [] allows empty, spec requires Min=1..&#8734;</description></item>
///   <item><term>Seller</term><description>ValueList&lt;T&gt; = [] allows empty, spec requires Min=1..&#8734;</description></item>
/// </list>
/// </remarks>
[Obsolete("Marked obsolete in the ISO 20022 2026-06-26 snapshot. Removal date: 2018-09-08.")]
public class LoanContract1Validator : AbstractValidator<ILoanContract1>
{
    /// <summary>
    /// Initializes a new instance of the validator for <see cref="ILoanContract1"/>.
    /// </summary>
    public LoanContract1Validator()
    {
        // Required members (1..1): the interface marks them only by type, so a null or default is refused here.
        RuleFor(x => x.ContractDocumentIdentification).NotNull().WithMessage("LoanContract1.ContractDocumentIdentification is required (1..1).");
        RuleFor(x => x.Amount).NotNull().WithMessage("LoanContract1.Amount is required (1..1).");
        RuleFor(x => x.MaturityDate).NotDefault().WithMessage("LoanContract1.MaturityDate is required (1..1).");
        RuleFor(x => x.ProlongationFlag).NotDefault().WithMessage("LoanContract1.ProlongationFlag is required (1..1).");
        RuleFor(x => x.StartDate).NotDefault().WithMessage("LoanContract1.StartDate is required (1..1).");
        RuleFor(x => x.SettlementCurrency).NotDefault().WithMessage("LoanContract1.SettlementCurrency is required (1..1).");
        RuleFor(x => x.DurationCode).NotDefault().WithMessage("LoanContract1.DurationCode is required (1..1).");
        RuleFor(x => x.InterestRate).NotNull().WithMessage("LoanContract1.InterestRate is required (1..1).");
        RuleFor(x => x.InterestSchedule).NotNull().WithMessage("LoanContract1.InterestSchedule is required (1..1).");
        RuleFor(x => x.IntraCompanyLoan).NotDefault().WithMessage("LoanContract1.IntraCompanyLoan is required (1..1).");

        RuleFor(x => x.Buyer)
            .NotEmpty()
            .WithMessage("LoanContract1.Buyer must contain at least one element (1..∞).");

        RuleFor(x => x.Seller)
            .NotEmpty()
            .WithMessage("LoanContract1.Seller must contain at least one element (1..∞).");
    }
}
