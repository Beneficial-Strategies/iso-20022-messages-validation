// Example 03: without the classes.
// Shows:  an object made by the Factory for an interface, validated by the validators of that interface.
// Needs:  BeneficialStrategies.Iso20022.Messages.Validation and BeneficialStrategies.Iso20022.Factory.
// Prints: whether a birth made by the Factory is valid.
using BeneficialStrategies.Iso20022.Codesets;
using BeneficialStrategies.Iso20022.Components;
using BeneficialStrategies.Iso20022.Factory;
using BeneficialStrategies.Iso20022.Messages.Validation;
using FluentValidation;
using Microsoft.Extensions.DependencyInjection;

var countries = new InMemoryExternalCodeRegistry<CountryCode>();
countries.Add("US");
var services = new ServiceCollection();
services.AddIso20022Validators();
services.AddSingleton<IExternalCodeRegistry<CountryCode>>(countries);
using var provider = services.BuildServiceProvider();
var validator = provider.GetRequiredService<IValidator<IDateAndPlaceOfBirth1>>();

// <snippet make>
// An object for the interface, with its members set: no class to write
var birth = IsoDataFactory.Make<IDateAndPlaceOfBirth1>(b => b
    .Set(x => x.BirthDate).To(new DateOnly(1990, 1, 1))
    .Set(x => x.CityOfBirth).To("Springfield")
    .Set(x => x.CountryOfBirth).To("ZZ"));

var result = validator.Validate(birth);
Console.WriteLine($"IsValid={result.IsValid}");                        // IsValid=False
foreach (var error in result.Errors)
    Console.WriteLine($"  {error.PropertyName}: {error.ErrorMessage}");
// </snippet>
