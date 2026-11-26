// Copyright 2026 Jeff Ward, Beneficial Strategies. Usage subject to license of enclosing library.

using System.Net;
using System.Text;
using Microsoft.Extensions.DependencyInjection;

namespace BeneficialStrategies.Iso20022.Messages.Validation;

public class LiveExternalCodeRegistryTests
{
    private sealed class FakeSource(Func<string, IReadOnlyCollection<string>?> read) : IExternalCodeSource
    {
        public int Reads { get; private set; }

        public Task<IReadOnlyCollection<string>?> GetCodesAsync(string name, CancellationToken ct)
        {
            Reads++;
            return Task.FromResult(read(name));
        }
    }

    private sealed class Handler(Func<HttpRequestMessage, HttpResponseMessage> respond) : HttpMessageHandler
    {
        public List<Uri> Requests { get; } = [];

        protected override Task<HttpResponseMessage> SendAsync(HttpRequestMessage request, CancellationToken ct)
        {
            Requests.Add(request.RequestUri!);
            return Task.FromResult(respond(request));
        }
    }

    private static HttpResponseMessage Json(string body) =>
        new(HttpStatusCode.OK) { Content = new StringContent(body, Encoding.UTF8, "application/json") };

    [Fact]
    public void ValueOnTheLiveList_IsAcceptable_AndOthersAreNot()
    {
        var sut = new LiveExternalCodeRegistry<CountryCode>(new FakeSource(_ => ["US", "CA"]));

        Assert.True(sut.IsAcceptable("US"));
        Assert.False(sut.IsAcceptable("FR"));
    }

    [Fact]
    public void LiveList_IsReadOnce_WhileItIsFresh()
    {
        var source = new FakeSource(_ => ["US"]);
        var sut = new LiveExternalCodeRegistry<CountryCode>(source);

        sut.IsAcceptable("US");
        sut.IsAcceptable("US");

        Assert.Equal(1, source.Reads);
    }

    [Fact]
    public void ExpiredList_IsStillUsed_AndReadAgainInTheBackground()
    {
        var now = DateTimeOffset.UtcNow;
        var list = new[] { "US" };
        var source = new FakeSource(_ => list);
        var sut = new LiveExternalCodeRegistry<CountryCode>(
            source,
            new LiveExternalCodeOptions { RefreshInterval = TimeSpan.FromMinutes(10) },
            () => now
        );
        Assert.True(sut.IsAcceptable("US"));

        list = ["CA"];
        now += TimeSpan.FromMinutes(11);
        Assert.True(sut.IsAcceptable("US")); // the expired list answers while the new one is read

        SpinWait.SpinUntil(() => source.Reads == 2, TimeSpan.FromSeconds(5));
        Assert.True(SpinWait.SpinUntil(() => sut.IsAcceptable("CA"), TimeSpan.FromSeconds(5)));
        Assert.False(sut.IsAcceptable("US"));
    }

    [Fact]
    public void EmptyList_MeansFreeText_AndAcceptsAnything()
    {
        var sut = new LiveExternalCodeRegistry<CountryCode>(new FakeSource(_ => []));

        Assert.True(sut.IsAcceptable("ZZ"));
    }

    [Theory]
    [InlineData(ExternalCodeUnavailablePolicy.Accept, true)]
    [InlineData(ExternalCodeUnavailablePolicy.Reject, false)]
    public void SourceDown_FollowsThePolicy(ExternalCodeUnavailablePolicy policy, bool expected)
    {
        var sut = new LiveExternalCodeRegistry<CountryCode>(
            new FakeSource(_ => throw new HttpRequestException("down")),
            new LiveExternalCodeOptions { WhenUnavailable = policy }
        );

        Assert.Equal(expected, sut.IsAcceptable("US"));
    }

    [Fact]
    public void SourceDown_ByDefault_UsesTheBuiltInValues()
    {
        var sut = new LiveExternalCodeRegistry<ExternalAuthenticationMethod1Code>(
            new FakeSource(_ => throw new HttpRequestException("down"))
        );

        Assert.True(sut.IsAcceptable(ExternalAuthenticationMethod1Code.AcceptorCertificateSerialNumber));
        Assert.False(sut.IsAcceptable(new ExternalAuthenticationMethod1Code("ZZZZ")));
    }

    [Fact]
    public void SourceDown_IsNotRetriedByEveryValidation()
    {
        var source = new FakeSource(_ => throw new HttpRequestException("down"));
        var sut = new LiveExternalCodeRegistry<CountryCode>(source);

        sut.IsAcceptable("US");
        sut.IsAcceptable("US");
        sut.IsAcceptable("US");

        Assert.Equal(1, source.Reads);
    }

    [Fact]
    public void CodeSetTheSourceDoesNotHave_FollowsThePolicy()
    {
        var sut = new LiveExternalCodeRegistry<CountryCode>(
            new FakeSource(_ => null),
            new LiveExternalCodeOptions { WhenUnavailable = ExternalCodeUnavailablePolicy.Reject }
        );

        Assert.False(sut.IsAcceptable("US"));
    }

    [Fact]
    public async Task HttpSource_ReadsTheValuesOfTheCodeSet_FromItsAddress()
    {
        var handler = new Handler(_ => Json("""{"type":"CountryCode","values":[{"value":"US","text":"x"},{"value":"CA","text":"y"}],"release":"r"}"""));
        var source = new HttpExternalCodeSource(new HttpClient(handler), new Uri("https://example.test/codes"));

        var codes = await source.GetCodesAsync("CountryCode", default);

        Assert.Equal(["US", "CA"], codes);
        Assert.Equal("https://example.test/codes/CountryCode", handler.Requests.Single().AbsoluteUri);
    }

    [Fact]
    public async Task HttpSource_NotFound_IsACodeSetItDoesNotHave()
    {
        var source = new HttpExternalCodeSource(new HttpClient(new Handler(_ => new HttpResponseMessage(HttpStatusCode.NotFound))));

        Assert.Null(await source.GetCodesAsync("Nope", default));
    }

    [Fact]
    public async Task HttpSource_ServerError_Throws()
    {
        var source = new HttpExternalCodeSource(new HttpClient(new Handler(_ => new HttpResponseMessage(HttpStatusCode.InternalServerError))));

        await Assert.ThrowsAsync<HttpRequestException>(() => source.GetCodesAsync("CountryCode", default));
    }

    [Fact]
    public void AddIso20022LiveExternalCodes_ReplacesTheDefaultRegistry()
    {
        var handler = new Handler(_ => Json("""{"values":[{"value":"US"}]}"""));
        var services = new ServiceCollection();
        services.AddIso20022Validators();
        services.AddIso20022LiveExternalCodes(client: new HttpClient(handler));
        using var provider = services.BuildServiceProvider();

        var validator = provider.GetRequiredService<IValidator<CountryCode>>();

        Assert.True(validator.Validate((CountryCode)"US").IsValid);
        Assert.False(validator.Validate((CountryCode)"FR").IsValid);
        Assert.Equal(
            "https://iso-20022-external-codesets.beneficialstrategies.com/CountryCode",
            handler.Requests.Single().AbsoluteUri
        );
    }
}
