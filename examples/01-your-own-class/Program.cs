// Example 01: your own class.
// Shows:  validating a class of your own that has the shape of an ISO 20022 component; the validators are written for the interface.
// Needs:  only BeneficialStrategies.Iso20022.Messages.Validation (which brings Messages, Primitives and FluentValidation).
// Prints: whether a birth with a known and with an unknown country is valid, and the failure.
using BeneficialStrategies.Iso20022.Codesets;
using BeneficialStrategies.Iso20022.Components;
using BeneficialStrategies.Iso20022.Messages.Validation;
using BeneficialStrategies.Iso20022.SimpleTypes;
using FluentValidation;
using Microsoft.Extensions.DependencyInjection;
using MyCompany.Examples;

// <snippet validate>
// The acceptable country codes are yours to say; without a list nothing is rejected on that basis.
var countries = new InMemoryExternalCodeRegistry<CountryCode>();
countries.Add("US");

var services = new ServiceCollection();
services.AddIso20022Validators();
services.AddSingleton<IExternalCodeRegistry<CountryCode>>(countries);
using var provider = services.BuildServiceProvider();

var validator = provider.GetRequiredService<IValidator<IDateAndPlaceOfBirth1>>();

foreach (var country in new[] { "US", "ZZ" })
{
    var result = validator.Validate(new MyBirth(country));
    Console.WriteLine($"{country}: IsValid={result.IsValid}");
    foreach (var error in result.Errors)
        Console.WriteLine($"  {error.PropertyName}: {error.ErrorMessage}");
}
// </snippet>

namespace MyCompany.Examples
{
    // <snippet class>
    // A class of yours that has the shape of the ISO 20022 component
    public sealed class MyBirth(string country) : IDateAndPlaceOfBirth1
    {
        public ISODate BirthDate => new DateOnly(1990, 1, 1);
        public Max35Text? ProvinceOfBirth => null;
        public Max35Text CityOfBirth => "Springfield";
        public CountryCode CountryOfBirth => country;    // a code: two upper-case letters, and a country that exists
    }
    // </snippet>
}
