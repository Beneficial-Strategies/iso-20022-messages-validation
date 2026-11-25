// Copyright 2026 Jeff Ward, Beneficial Strategies. Usage subject to license of enclosing library.

namespace BeneficialStrategies.Iso20022.Messages.Validation;

/// <summary>
/// Rules for a required (1..1) member of an interface. The interfaces mark such a member only by a
/// non-nullable type, so an implementation can still return null, or <c>default</c> for a struct.
/// </summary>
internal static class RequiredMemberExtensions
{
    /// <summary>Refuses the <c>default</c> value of a struct, which no constructor checked.</summary>
    internal static IRuleBuilderOptions<T, TProperty> NotDefault<T, TProperty>(
        this IRuleBuilder<T, TProperty> ruleBuilder
    )
        where TProperty : struct =>
        ruleBuilder.Must(value => !EqualityComparer<TProperty>.Default.Equals(value, default));
}
