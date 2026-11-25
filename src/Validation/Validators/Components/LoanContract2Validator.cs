// Copyright 2026 Jeff Ward, Beneficial Strategies. Usage subject to license of enclosing library.

namespace BeneficialStrategies.Iso20022.Messages.Validation.Components;

/// <summary>
/// Validates <see cref="ILoanContract2"/> per the ISO 20022 specification.
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
public class LoanContract2Validator : AbstractValidator<ILoanContract2>
{
    /// <summary>
    /// Initializes a new instance of the validator for <see cref="ILoanContract2"/>.
    /// </summary>
    public LoanContract2Validator()
    {
        // Required members (1..1): the interface marks them only by type, so a null or default is refused here.
        RuleFor(x => x.ContractDocumentIdentification).NotNull().WithMessage("LoanContract2.ContractDocumentIdentification is required (1..1).");
        RuleFor(x => x.Amount).NotNull().WithMessage("LoanContract2.Amount is required (1..1).");
        RuleFor(x => x.MaturityDate).NotDefault().WithMessage("LoanContract2.MaturityDate is required (1..1).");
        RuleFor(x => x.ProlongationFlag).NotDefault().WithMessage("LoanContract2.ProlongationFlag is required (1..1).");
        RuleFor(x => x.StartDate).NotDefault().WithMessage("LoanContract2.StartDate is required (1..1).");
        RuleFor(x => x.SettlementCurrency).NotDefault().WithMessage("LoanContract2.SettlementCurrency is required (1..1).");
        RuleFor(x => x.DurationCode).NotDefault().WithMessage("LoanContract2.DurationCode is required (1..1).");
        RuleFor(x => x.InterestRate).NotNull().WithMessage("LoanContract2.InterestRate is required (1..1).");
        RuleFor(x => x.InterestSchedule).NotNull().WithMessage("LoanContract2.InterestSchedule is required (1..1).");
        RuleFor(x => x.IntraCompanyLoan).NotDefault().WithMessage("LoanContract2.IntraCompanyLoan is required (1..1).");

        RuleFor(x => x.Buyer)
            .NotEmpty()
            .WithMessage("LoanContract2.Buyer must contain at least one element (1..∞).");

        RuleFor(x => x.Seller)
            .NotEmpty()
            .WithMessage("LoanContract2.Seller must contain at least one element (1..∞).");
    }
}
