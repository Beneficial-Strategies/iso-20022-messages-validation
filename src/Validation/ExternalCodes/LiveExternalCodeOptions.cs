// Copyright 2026 Jeff Ward, Beneficial Strategies. Usage subject to license of enclosing library.

namespace BeneficialStrategies.Iso20022.Messages.Validation;

/// <summary>What <see cref="LiveExternalCodeRegistry{TCode}"/> does when it has no list to check against.</summary>
public enum ExternalCodeUnavailablePolicy
{
    /// <summary>Check against the values the library was built with (<see cref="InMemoryExternalCodeRegistry{TCode}"/>). The default.</summary>
    UseBuiltInValues,

    /// <summary>Accept every value: nothing can be said against it.</summary>
    Accept,

    /// <summary>Refuse every value: a value that cannot be checked is not valid.</summary>
    Reject,
}

/// <summary>Settings of <see cref="LiveExternalCodeRegistry{TCode}"/>.</summary>
public sealed class LiveExternalCodeOptions
{
    /// <summary>
    /// How long a list read from the source is used before it is read again. The expired list stays in use while the new one is read,
    /// so a validation never waits for a refresh (only the first read of a code set waits). Default one hour.
    /// </summary>
    public TimeSpan RefreshInterval { get; set; } = TimeSpan.FromHours(1);

    /// <summary>How long the first read of a code set may take before the unavailable policy applies. Default five seconds.</summary>
    public TimeSpan FirstReadTimeout { get; set; } = TimeSpan.FromSeconds(5);

    /// <summary>What to do while the source cannot be read, or does not have the code set, and no earlier list is held.</summary>
    public ExternalCodeUnavailablePolicy WhenUnavailable { get; set; } = ExternalCodeUnavailablePolicy.UseBuiltInValues;
}
