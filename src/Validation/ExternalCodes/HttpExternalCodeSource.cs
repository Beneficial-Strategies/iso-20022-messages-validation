// Copyright 2026 Jeff Ward, Beneficial Strategies. Usage subject to license of enclosing library.

using System.Net;
using System.Text.Json;

namespace BeneficialStrategies.Iso20022.Messages.Validation;

/// <summary>
/// Reads external code sets from a host that serves one JSON file per code set at <c>/{CodeSetName}</c>, such as
/// <c>https://iso-20022-external-codesets.beneficialstrategies.com</c> (or your own copy of it). The file has a <c>values</c> array whose
/// items have a <c>value</c>.
/// </summary>
public sealed class HttpExternalCodeSource : IExternalCodeSource
{
    /// <summary>The public host that follows ISO's external code sets nightly.</summary>
    public static readonly Uri DefaultBaseAddress = new("https://iso-20022-external-codesets.beneficialstrategies.com/");

    private readonly HttpClient _client;
    private readonly Uri _baseAddress;

    /// <summary>Creates the source.</summary>
    /// <param name="client">The client to read with. The caller owns it (and its timeout).</param>
    /// <param name="baseAddress">The address of the host; <see cref="DefaultBaseAddress"/> when <see langword="null"/>.</param>
    public HttpExternalCodeSource(HttpClient client, Uri? baseAddress = null)
    {
        _client = client ?? throw new ArgumentNullException(nameof(client));
        var b = baseAddress ?? DefaultBaseAddress;
        _baseAddress = b.AbsoluteUri.EndsWith("/", StringComparison.Ordinal) ? b : new Uri(b.AbsoluteUri + "/");
    }

    /// <inheritdoc />
    public async Task<IReadOnlyCollection<string>?> GetCodesAsync(string codeSetName, CancellationToken cancellationToken)
    {
        using var response = await _client.GetAsync(new Uri(_baseAddress, Uri.EscapeDataString(codeSetName)), cancellationToken).ConfigureAwait(false);
        if (response.StatusCode == HttpStatusCode.NotFound)
        {
            return null;
        }

        response.EnsureSuccessStatusCode();
        using var stream = await response.Content.ReadAsStreamAsync().ConfigureAwait(false);
        using var doc = await JsonDocument.ParseAsync(stream, cancellationToken: cancellationToken).ConfigureAwait(false);
        var codes = new List<string>();
        if (doc.RootElement.TryGetProperty("values", out var values) && values.ValueKind == JsonValueKind.Array)
        {
            foreach (var item in values.EnumerateArray())
            {
                if (item.TryGetProperty("value", out var v) && v.GetString() is { Length: > 0 } code)
                {
                    codes.Add(code);
                }
            }
        }

        return codes;
    }
}
