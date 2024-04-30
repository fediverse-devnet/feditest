# Feditest: test federated protocols such as those in the Fediverse

This repo contains:

* the FediTest test framework

which allows you to define and run test plans that involve constellations of servers (like Fediverse instances) whose communication you want to test.

The actual tests for the Fediverse are in their own [repository](https://github.com/fediverse-devnet/feditest-tests-fediverse).

For more details, check out [feditest.org](https://feditest.org/) and find us on Matrix in [#fediverse-testing:matrix.org](https://matrix.to/#/%23fediverse-testing:matrix.org).

> [!WARNING]
> Early work in progress.



## Usage scenarios

### QA and CI

```
> feditest run --testplan ci-touch-automated.json
> feditest run --testplan qa-full-partially-manual.json
```

To create the plans:

```
> feditest generate-settion-template --testsdir tests --all --out full-partially-automated-template.json
> feditest generate-testplan --constellations all-supported-constellations.json --session-template full-partially-automated-template.json --out qa-full-partially-manual.json
```

etc.

### When debugging

```
> feditest run --testplan debug-issue-123.json --interactive
```

with

```
> feditest generate-testplan --constellation ours-and-theirs.json --test tests/protocol/test-17-2-8.json --out debug-issue-123.json
```
