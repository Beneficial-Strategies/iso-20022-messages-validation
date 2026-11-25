// Copyright 2026 Jeff Ward, Beneficial Strategies. Usage subject to license of enclosing library.

namespace BeneficialStrategies.Iso20022.Messages.Validation.Components;

/// <summary>
/// Validates <see cref="IDetailedStatisticsPerCounterparty19"/> per the ISO 20022 specification.
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
///   <item><term>RejectionStatistics</term><description>ValueList&lt;T&gt; = [] allows empty, spec requires Min=1..&#8734;</description></item>
/// </list>
/// </remarks>
public class DetailedStatisticsPerCounterparty19Validator : AbstractValidator<IDetailedStatisticsPerCounterparty19>
{
    /// <summary>
    /// Initializes a new instance of the validator for <see cref="IDetailedStatisticsPerCounterparty19"/>.
    /// </summary>
    public DetailedStatisticsPerCounterparty19Validator()
    {
        // Required members (1..1): the interface marks them only by type, so a null or default is refused here.
        RuleFor(x => x.ReferenceDate).NotDefault().WithMessage("DetailedStatisticsPerCounterparty19.ReferenceDate is required (1..1).");
        RuleFor(x => x.TotalNumberOfReports).NotDefault().WithMessage("DetailedStatisticsPerCounterparty19.TotalNumberOfReports is required (1..1).");
        RuleFor(x => x.TotalNumberOfReportsAccepted).NotDefault().WithMessage("DetailedStatisticsPerCounterparty19.TotalNumberOfReportsAccepted is required (1..1).");
        RuleFor(x => x.TotalNumberOfReportsRejected).NotDefault().WithMessage("DetailedStatisticsPerCounterparty19.TotalNumberOfReportsRejected is required (1..1).");
        RuleFor(x => x.TotalNumberOfTransactions).NotDefault().WithMessage("DetailedStatisticsPerCounterparty19.TotalNumberOfTransactions is required (1..1).");
        RuleFor(x => x.TotalNumberOfTransactionsAccepted).NotDefault().WithMessage("DetailedStatisticsPerCounterparty19.TotalNumberOfTransactionsAccepted is required (1..1).");
        RuleFor(x => x.TotalNumberOfTransactionsRejected).NotDefault().WithMessage("DetailedStatisticsPerCounterparty19.TotalNumberOfTransactionsRejected is required (1..1).");

        RuleFor(x => x.RejectionStatistics)
            .NotEmpty()
            .WithMessage("DetailedStatisticsPerCounterparty19.RejectionStatistics must contain at least one element (1..∞).");
    }
}
