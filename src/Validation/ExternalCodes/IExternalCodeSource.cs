// Copyright 2026 Jeff Ward, Beneficial Strategies. Usage subject to license of enclosing library.

namespace BeneficialStrategies.Iso20022.Messages.Validation;

/// <summary>
/// Where the live list of an external code set comes from: a host that serves ISO's external code sets (the default,
/// <see cref="HttpExternalCodeSource"/>), a database, a file, or a test double.
/// </summary>
public interface IExternalCodeSource
{
    /// <summary>
    /// Reads the codes of one external code set.
    /// </summary>
    /// <param name="codeSetName">ISO's name of the code set, for example <c>ExternalPurpose1Code</c>.</param>
    /// <param name="cancellationToken">Cancels the read.</param>
    /// <returns>
    /// The codes, which may be empty (ISO publishes no list: the field is free text); or <see langword="null"/> when the source does not
    /// have this code set at all. A source that cannot be reached throws.
    /// </returns>
    Task<IReadOnlyCollection<string>?> GetCodesAsync(string codeSetName, CancellationToken cancellationToken);
}
