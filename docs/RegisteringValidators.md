# Registering validators with dependency injection

Constructing one validator with `new` is fine for a quick check, but every validator in this
package composes its children via constructor injection — the two-constructor pattern you'll see
throughout the source (a DI constructor taking `IValidator<T>` for each child, and a parameterless
convenience constructor for exactly the kind of one-off use above). `AddIso20022Validators()`
registers all of them at once with a standard `IServiceCollection`.

The examples below construct a `ServiceCollection` directly, which needs one more package in a
plain console app (ASP.NET Core and other hosts already bring this in for you):

```bash
dotnet add package Microsoft.Extensions.DependencyInjection --version 8.0.0
```

```C#
using BeneficialStrategies.Iso20022.camt;
using BeneficialStrategies.Iso20022.Messages.Validation;
using BeneficialStrategies.Iso20022.Messages.Validation.camt;
using FluentValidation;
using Microsoft.Extensions.DependencyInjection;

var services = new ServiceCollection();
services.AddIso20022Validators();
using var provider = services.BuildServiceProvider();

var validator = provider.GetRequiredService<IValidator<CancelCaseAssignmentV05>>();
```

Registering every validator in the assembly is the simplest option, but not always the leanest —
three narrower overloads are available when you know your scope up front:

```C#
// Only validators for a specific ISO 20022 business area (plus whatever shared
// component/choice validators those messages actually depend on — never fewer, so
// nothing breaks).
services.AddIso20022Validators(businessAreas: ["camt", "pain"]);

// The exact transitive closure one specific message needs — nothing more, nothing
// approximated. Computed via reflection over the validators' own constructors, not
// a namespace guess.
services.AddIso20022Validators(rootTypes: [typeof(CancelCaseAssignmentV05)]);

// A raw predicate over each concrete validator type, for anything the two above
// don't cover.
services.AddIso20022Validators(
    filter: validatorType => validatorType.Namespace!.EndsWith(".camt")
);
```

`rootTypes` is the tightest of the three — it registers precisely what the given message(s) need,
computed by walking each validator's own dependency-injection constructor. It's the one to reach
for if you're only ever validating a known, fixed set of message types and want to avoid
registering the other 1,000+ validators in the assembly you'll never resolve.
