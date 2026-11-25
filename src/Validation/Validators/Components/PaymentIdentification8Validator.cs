// Copyright 2026 Jeff Ward, Beneficial Strategies. Usage subject to license of enclosing library.

namespace BeneficialStrategies.Iso20022.Messages.Validation.Components;

/// <summary>
/// Validates <see cref="IPaymentIdentification8"/> per the ISO 20022 specification.
/// </summary>
/// <remarks>
/// ISO ID: _rf468HrhEeidVZmeoasaWQ
/// Spec source: queried via ISO 20022 MCP server (2026-08-20).
///
/// Set of elements used to provide further means of referencing a payment transaction.
/// <list type="table">
///   <item><term>InstructionIdentification</term><description>Max35Text — optional (0..1)</description></item>
///   <item><term>EndToEndIdentification</term><description>Max35Text — required (1..1)</description></item>
///   <item><term>TransactionIdentification</term><description>Max35Text — optional (0..1)</description></item>
///   <item><term>UETR</term><description>UUIDv4Identifier — optional (0..1)</description></item>
/// </list>
///
/// No constraints are declared on this component in the spec. Every field is already fully
/// enforced at the struct level — there is no additional cross-field or business rule to add at
/// the FluentValidation layer, so this validator has no rules. It still exists as a first-class
/// type so the coverage-scoping policy (see the FluentValidation project's own <c>CLAUDE.md</c>)
/// can record this type as reviewed rather than silently skipped.
/// </remarks>
public class PaymentIdentification8Validator : AbstractValidator<IPaymentIdentification8>
{
    /// <summary>Initializes a new instance.</summary>
    public PaymentIdentification8Validator()
    {
        // Required members (1..1): the interface marks them only by type, so a null or default is refused here.
        RuleFor(x => x.EndToEndIdentification).NotDefault().WithMessage("PaymentIdentification8.EndToEndIdentification is required (1..1).");

    }
}
