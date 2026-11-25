// Copyright 2026 Jeff Ward, Beneficial Strategies. Usage subject to license of enclosing library.

using System.Reflection;

namespace BeneficialStrategies.Iso20022.Messages.Validation;

/// <summary>
/// A required member of an interface is one with a non-nullable type. An implementation can still
/// return null or <c>default</c> for it, so the validator must refuse that: the type system alone
/// no longer does (it did when the validators took records, whose members were C# <c>required</c>).
/// </summary>
/// <remarks>
/// For every validator of an interface, an object whose members all return null or <c>default</c>
/// is validated; each required member must then be named by an error.
/// </remarks>
public class RequiredMemberCoverageTests
{
    private static readonly NullabilityInfoContext Nullability = new();

    /// <summary>The required members, of each validator, that raise no error on a null or <c>default</c> value.</summary>
    internal static IEnumerable<(Type Validator, string Member, string Kind)> Gaps()
    {
        var assembly = typeof(Iso20022ServiceCollectionExtensions).Assembly;
        foreach (var validator in assembly.GetTypes().Where(t => !t.IsAbstract && t.IsClass))
        {
            var model = ModelOf(validator);
            if (model is null || validator.GetConstructor(Type.EmptyTypes) is null) continue;

            var required = RequiredMembers(model).ToList();
            if (required.Count == 0) continue;

            var proxy = typeof(DefaultProxy).GetMethod(nameof(DefaultProxy.Create))!
                .MakeGenericMethod(model).Invoke(null, null)!;
            var instance = (IValidator)Activator.CreateInstance(validator)!;
            HashSet<string>? named = null;
            try
            {
                named = instance.Validate(new ValidationContext<object>(proxy)).Errors
                    .Select(e => e.PropertyName.Split('.', '[')[0]).ToHashSet();
            }
            catch (Exception)
            {
                // A validator that throws on a missing member does not refuse it: a gap too.
            }
            if (named is null)
            {
                foreach (var (member, _) in required) yield return (validator, member, "throws");
                continue;
            }

            foreach (var (member, kind) in required)
                if (!named.Contains(member)) yield return (validator, member, kind);
        }
    }

    private static Type? ModelOf(Type validator)
    {
        for (var t = validator.BaseType; t is not null; t = t.BaseType)
            if (t.IsGenericType && t.GetGenericTypeDefinition() == typeof(AbstractValidator<>)
                && t.GetGenericArguments()[0] is { IsInterface: true } model)
                return model;
        return null;
    }

    private static IEnumerable<(string Member, string Kind)> RequiredMembers(Type model)
    {
        foreach (var property in model.GetProperties())
        {
            var type = property.PropertyType;
            if (type.IsEnum || type == typeof(bool) || type.IsPrimitive || type == typeof(decimal)) continue;
            if (Nullable.GetUnderlyingType(type) is not null) continue;
            if (type.IsValueType) { yield return (property.Name, "value"); continue; }
            if (type != typeof(string) && typeof(System.Collections.IEnumerable).IsAssignableFrom(type)) continue;
            if (Nullability.Create(property).ReadState == NullabilityState.NotNull)
                yield return (property.Name, "reference");
        }
    }

    /// <summary>An implementation of any interface whose members all return null or <c>default</c>.</summary>
    public class DefaultProxy : DispatchProxy
    {
        /// <summary>Makes the proxy.</summary>
        public static T Create<T>() where T : class => Create<T, DefaultProxy>();

        /// <inheritdoc/>
        protected override object? Invoke(MethodInfo? targetMethod, object?[]? args) =>
            targetMethod!.ReturnType is { IsValueType: true } t && t != typeof(void) ? Activator.CreateInstance(t) : null;
    }

    /// <summary>
    /// The namespaces not yet done (issue #17): their gaps are listed by <see cref="ListGaps"/>
    /// and are not yet an error. Remove a name here when its batch is merged.
    /// </summary>
    private static readonly string[] Pending = ["Components"];

    /// <summary>Every required member of a validator outside the pending namespaces is refused when null or <c>default</c>.</summary>
    [Fact]
    public void RequiredMembers_AreRefused_WhenNullOrDefault()
    {
        var gaps = Gaps()
            .Where(g => !Pending.Contains(g.Validator.Namespace!.Split('.')[^1]))
            .Select(g => $"{g.Validator.Name}.{g.Member} ({g.Kind})")
            .ToList();
        Assert.True(gaps.Count == 0, "Required members with no rule:\n" + string.Join("\n", gaps));
    }

    /// <summary>Writes the list of gaps to the file named by REQUIRED_GAPS_FILE, for the batches.</summary>
    [Fact]
    public void ListGaps()
    {
        var path = Environment.GetEnvironmentVariable("REQUIRED_GAPS_FILE");
        if (path is null) return;
        File.WriteAllLines(path, Gaps().Select(g => $"{g.Validator.Namespace}\t{g.Validator.Name}\t{g.Member}\t{g.Kind}"));
    }
}
