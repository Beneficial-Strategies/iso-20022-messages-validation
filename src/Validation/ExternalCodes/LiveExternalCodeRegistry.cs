// Copyright 2026 Jeff Ward, Beneficial Strategies. Usage subject to license of enclosing library.

namespace BeneficialStrategies.Iso20022.Messages.Validation;

/// <summary>
/// Checks a code against the current list of its external code set, read from an <see cref="IExternalCodeSource"/>.
/// </summary>
/// <remarks>
/// The list is read on first use and read again after <see cref="LiveExternalCodeOptions.RefreshInterval"/>; a list that has expired is
/// still used while the new one is read in the background, and a failed read keeps the last list. When there is no list at all (the
/// source is down at the first read, or does not have the code set, or publishes an empty list) the
/// <see cref="LiveExternalCodeOptions.WhenUnavailable"/> policy applies; an empty list means the field is free text and accepts any value.
/// </remarks>
/// <typeparam name="TCode">The external code set type this registry answers for. Its name is the name of the code set.</typeparam>
public class LiveExternalCodeRegistry<TCode> : IExternalCodeRegistry<TCode>
    where TCode : IIsoExternalCode
{
    private readonly IExternalCodeSource _source;
    private readonly LiveExternalCodeOptions _options;
    private readonly Func<DateTimeOffset> _now;
    private readonly InMemoryExternalCodeRegistry<TCode> _builtIn = new();
    private readonly object _gate = new();
    private static readonly TimeSpan RetryDelay = TimeSpan.FromMinutes(1);
    private Snapshot? _snapshot;
    private Task? _refresh;
    private DateTimeOffset _retryAfter = DateTimeOffset.MinValue;

    /// <summary>Creates the registry.</summary>
    /// <param name="source">Where the lists come from.</param>
    /// <param name="options">The settings; the defaults when <see langword="null"/>.</param>
    /// <param name="now">The clock, for tests.</param>
    public LiveExternalCodeRegistry(IExternalCodeSource source, LiveExternalCodeOptions? options = null, Func<DateTimeOffset>? now = null)
    {
        _source = source ?? throw new ArgumentNullException(nameof(source));
        _options = options ?? new LiveExternalCodeOptions();
        _now = now ?? (() => DateTimeOffset.UtcNow);
    }

    /// <inheritdoc />
    public virtual bool IsAcceptable(TCode value)
    {
        var snapshot = Current();
        if (snapshot is null)
        {
            return _options.WhenUnavailable switch
            {
                ExternalCodeUnavailablePolicy.Accept => true,
                ExternalCodeUnavailablePolicy.Reject => false,
                _ => _builtIn.IsAcceptable(value),
            };
        }

        return snapshot.Codes.Count == 0 || snapshot.Codes.Contains(value.Value);
    }

    /// <summary>Reads the list now (for a start-up check, or a scheduled refresh).</summary>
    /// <param name="cancellationToken">Cancels the read.</param>
    /// <returns><see langword="true"/> when the source has the list and it was read.</returns>
    public async Task<bool> RefreshAsync(CancellationToken cancellationToken = default)
    {
        var codes = await _source.GetCodesAsync(typeof(TCode).Name, cancellationToken).ConfigureAwait(false);
        if (codes is null)
        {
            lock (_gate)
            {
                _retryAfter = _now() + RetryDelay;
            }

            return false;
        }

        var snapshot = new Snapshot(new HashSet<string>(codes, StringComparer.Ordinal), _now() + _options.RefreshInterval);
        lock (_gate)
        {
            _snapshot = snapshot;
        }

        return true;
    }

    private Snapshot? Current()
    {
        Snapshot? snapshot;
        lock (_gate)
        {
            snapshot = _snapshot;
        }

        if (snapshot is null)
        {
            lock (_gate)
            {
                if (_now() < _retryAfter)
                {
                    return null; // it failed a moment ago: do not make every validation wait again
                }
            }

            // The first read waits (up to the timeout); nothing is known before it.
            var first = StartRefresh();
            try
            {
                first.Wait(_options.FirstReadTimeout);
            }
            catch (AggregateException)
            {
                // the source could not be read: the policy applies
            }

            lock (_gate)
            {
                return _snapshot;
            }
        }

        if (snapshot.Expires <= _now())
        {
            _ = StartRefresh(); // the expired list is used meanwhile
        }

        return snapshot;
    }

    private Task StartRefresh()
    {
        lock (_gate)
        {
            if (_refresh is { IsCompleted: false })
            {
                return _refresh;
            }

            _refresh = Task.Run(async () =>
            {
                try
                {
                    await RefreshAsync().ConfigureAwait(false);
                }
                catch (Exception)
                {
                    // keep the last list; a later validation tries again
                    lock (_gate)
                    {
                        _retryAfter = _now() + RetryDelay;
                    }
                }
            });
            return _refresh;
        }
    }

    private sealed record Snapshot(HashSet<string> Codes, DateTimeOffset Expires);
}
