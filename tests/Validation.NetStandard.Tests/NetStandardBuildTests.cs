// Copyright 2026 Jeff Ward, Beneficial Strategies. Usage subject to license of enclosing library.

namespace BeneficialStrategies.Iso20022.Messages.Validation;

/// <summary>
/// The netstandard2.0 build of the validators, run on .NET Framework 4.8 as well as on .NET 8 and 10, with classes of the tests' own
/// and no message record.
/// </summary>
public class NetStandardBuildTests
{
    private sealed class OwnBirth(string country) : IDateAndPlaceOfBirth1
    {
        public ISODate BirthDate => new DateOnly(1990, 1, 1);
        public Max35Text? ProvinceOfBirth => null;
        public Max35Text CityOfBirth => "Springfield";
        public CountryCode CountryOfBirth => country;
    }

    private sealed class OwnEquivalentAmount(string currency) : Choices.AmountType4Choice.IEquivalentAmount
    {
        public ActiveOrHistoricCurrencyAndAmount Amount => new() { Currency = "USD", Amount = 100m };
        public ActiveOrHistoricCurrencyCode CurrencyOfTransfer => currency;
    }

    private static InMemoryExternalCodeRegistry<T> RegistryOf<T>(string code)
        where T : struct, IIsoExternalCode
    {
        var registry = new InMemoryExternalCodeRegistry<T>();
        registry.Add(code);
        return registry;
    }

    [Fact]
    public void Component_OwnClass_IsValidatedByTheRules()
    {
        var sut = new DateAndPlaceOfBirth1Validator(new CountryCodeValidator(RegistryOf<CountryCode>("US")));

        Assert.True(sut.Validate(new OwnBirth("US")).IsValid);
        Assert.False(sut.Validate(new OwnBirth("ZZ")).IsValid);
    }

    [Fact]
    public void Choice_OwnVariantClass_IsValidatedByTheVariantValidator()
    {
        var sut = new AmountType4Choice_Validator(new ActiveOrHistoricCurrencyCodeValidator(RegistryOf<ActiveOrHistoricCurrencyCode>("EUR")));

        Assert.True(sut.Validate(new OwnEquivalentAmount("EUR")).IsValid);
        Assert.False(sut.Validate(new OwnEquivalentAmount("ZZZ")).IsValid);
    }

    [Fact]
    public void ValidatorsAreRegisteredAndResolvedFromTheContainer()
    {
        var services = new ServiceCollection();
        services.AddIso20022Validators(filter: t => t == typeof(DateAndPlaceOfBirth1Validator) || t == typeof(CountryCodeValidator));
        using var provider = services.BuildServiceProvider();

        var sut = provider.GetRequiredService<IValidator<IDateAndPlaceOfBirth1>>();

        Assert.True(sut.Validate(new OwnBirth("US")).IsValid);
    }
}
