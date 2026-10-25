![Beneficial Strategies](https://raw.githubusercontent.com/Beneficial-Strategies/iso-20022-messages-validation/main/.beneficial/logo.png)

# BeneficialStrategies.Iso20022.Messages.Validation

FluentValidation validators for the interfaces of the ISO 20022 messages, components and choices: the rules the type system alone cannot express, such as cross-field rules and the check of a code against a registry.

**The rules the C# type system alone cannot express**: cross-field rules ("a case identification may appear in at most one of three possible locations") and the check of a code against a registry. 1,296 validators cover the messages, components and choices of the model.

The validators are written for the **interfaces** of the model (`IValidator<IGroupHeader131>`), not for any particular class, so they validate whatever implements the interface: a class of your own, the ready-made records, or an object built at run time. The format of each member is already enforced by its type; the validators add what a type cannot say. Three examples follow, each a step further.

## How to use

### Your own class

You do not need the message records. Take an interface of the model, `IDateAndPlaceOfBirth1`, and implement it in a class of your own:

<!-- snippet: examples/01-your-own-class/Program.cs#class -->
```csharp
// A class of yours that has the shape of the ISO 20022 component
public sealed class MyBirth(string country) : IDateAndPlaceOfBirth1
{
    public ISODate BirthDate => new DateOnly(1990, 1, 1);
    public Max35Text? ProvinceOfBirth => null;
    public Max35Text CityOfBirth => "Springfield";
    public CountryCode CountryOfBirth => country;    // a code: two upper-case letters, and a country that exists
}
```
<!-- /snippet -->

Register the validators, say which countries are acceptable, and validate:

<!-- snippet: examples/01-your-own-class/Program.cs#validate -->
```csharp
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
```
<!-- /snippet -->

```
US: IsValid=True
ZZ: IsValid=False
  CountryOfBirth.ExternalCodeRegistryRule: 'ZZ' is not an acceptable value for CountryCode (ExternalCodeRegistryRule).
```

Anything that implements the interface gets the same rules and the same messages. Try the [project](https://github.com/Beneficial-Strategies/iso-20022-messages-validation/tree/main/examples/01-your-own-class) yourself.

### With the message records

You would rather not write the classes: ISO 20022 has thousands of them. [BeneficialStrategies.Iso20022.Messages.Records](https://www.nuget.org/packages/BeneficialStrategies.Iso20022.Messages.Records) has every message, component and choice as a ready-made class, and they implement the interfaces, so the same validators work on them. This validates `camt.056.001.10`, first a well-formed request:

<!-- snippet: examples/02-with-the-message-records/Program.cs#valid -->
```csharp
// A well-formed cancellation request.
var request = new FIToFIPaymentCancellationRequestV10
{
    Assignment = new CaseAssignment5
    {
        Identification = "CASE-2026-0001",
        Assigner = new Agent { FinancialInstitutionIdentification = new() { BICFI = "AAAAGB2L" } },
        Assignee = new Agent { FinancialInstitutionIdentification = new() { BICFI = "BBBBUS33" } },
        CreationDateTime = new DateTime(2026, 8, 17, 9, 0, 0),
    },
    Underlying = [new UnderlyingTransaction28 { TransactionInformation = [new PaymentTransaction137()] }],
};

Console.WriteLine($"IsValid={validator.Validate(request).IsValid}");   // IsValid=True
```
<!-- /snippet -->

then the same with a case identification at the message level and at the transaction level, a rule of the specification that no C# type could express on its own:

<!-- snippet: examples/02-with-the-message-records/Program.cs#invalid -->
```csharp
// The same message with a case identification at the message level and at the transaction level: a rule of the specification
// (MessageOrGroupCaseRule) that no property type can enforce, since both places are optional on their own.
Case5 TheCase() => new()
{
    Identification = "CASE-2026-0001",
    Creator = new Agent { FinancialInstitutionIdentification = new() { BICFI = "AAAAGB2L" } },
};

var twice = request with
{
    Case = TheCase(),
    Underlying = [new UnderlyingTransaction28 { TransactionInformation = [new PaymentTransaction137 { Case = TheCase() }] }],
};

var result = validator.Validate(twice);
Console.WriteLine($"IsValid={result.IsValid}");                        // IsValid=False
foreach (var error in result.Errors)
    Console.WriteLine($"  {error.PropertyName}: {error.ErrorMessage}");
```
<!-- /snippet -->

```
IsValid=False
  MessageOrGroupCaseRule: Case identification must appear in at most one location: message-level Case, Underlying.OriginalGroupInformationAndCancellation.Case, or Underlying.TransactionInformation.Case (MessageOrGroupCaseRule / MessageOrTransactionCaseRule).
```

Try the [project](https://github.com/Beneficial-Strategies/iso-20022-messages-validation/tree/main/examples/02-with-the-message-records) yourself.

### Without the classes: the Factory

The records are large, and perhaps you do not want 3,339 messages' worth of classes in your application. The [Factory](https://www.nuget.org/packages/BeneficialStrategies.Iso20022.Factory) builds the class that implements an interface on the fly, the first time it is asked for, so you name the interface and write no implementation:

<!-- snippet: examples/03-without-the-classes/Program.cs#make -->
```csharp
// An object for the interface, with its members set: no class to write
var birth = IsoDataFactory.Make<IDateAndPlaceOfBirth1>(b => b
    .Set(x => x.BirthDate).To(new DateOnly(1990, 1, 1))
    .Set(x => x.CityOfBirth).To("Springfield")
    .Set(x => x.CountryOfBirth).To("ZZ"));

var result = validator.Validate(birth);
Console.WriteLine($"IsValid={result.IsValid}");                        // IsValid=False
foreach (var error in result.Errors)
    Console.WriteLine($"  {error.PropertyName}: {error.ErrorMessage}");
```
<!-- /snippet -->

The Factory also reads XML into the interfaces, so a document can be validated with no records at all: see [BeneficialStrategies.Iso20022.Validation.Xml](https://www.nuget.org/packages/BeneficialStrategies.Iso20022.Validation.Xml). Try the [project](https://github.com/Beneficial-Strategies/iso-20022-messages-validation/tree/main/examples/03-without-the-classes) yourself.

## More

* Documentation, release notes and issues: https://github.com/Beneficial-Strategies/iso-20022-messages-validation
* License: MIT. Status: stable.

### Registering the validators

`AddIso20022Validators()` registers all of them with a standard `IServiceCollection`; narrower overloads register one business area, the exact closure one message needs, or whatever a predicate selects. See [docs/RegisteringValidators.md](https://github.com/Beneficial-Strategies/iso-20022-messages-validation/blob/main/docs/RegisteringValidators.md).

### Code sets that live outside the library

Country codes, currency codes and ISO's own externally maintained code lists are checked for format by their type; which values are acceptable lives in a registry you can populate or replace. See [docs/ExternalCodeSets.md](https://github.com/Beneficial-Strategies/iso-20022-messages-validation/blob/main/docs/ExternalCodeSets.md).

### Raw XML or JSON off a queue

[BeneficialStrategies.Iso20022.Validation.Xml](https://www.nuget.org/packages/BeneficialStrategies.Iso20022.Validation.Xml) reads XML into an object and validates it in one call, and a payload package validates raw XML or JSON text as it arrives. They work with these validators because both use `IValidator<T>`; none of them depends on the others.

<!-- end of package readme -->

## Building and contributing

```
dotnet build -c Release
dotnet test -c Release --no-build
tools/run-examples.sh              # packs the package, then builds and runs every example against it
python3 tools/sync-readme.py       # fills the code blocks above from the examples
```

The .NET Framework 4.8 tests run on Windows only. A bug report or a change starts with an issue; a bug fix names the test that failed before it. How the validators are written and maintained: [docs/Validators.md](docs/Validators.md). See CONTRIBUTING.md.
