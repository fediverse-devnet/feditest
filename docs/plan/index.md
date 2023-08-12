# Planning the Fediverse test suite

## The problem

Core premise of the Fediverse is that users can use any app they chose (say “App A”)
to interact with others on the Fediverse, even if they use a different “App B”, and
when they do so, the interaction “will work”. Technically, this means that any two apps
A and B must implement the same Fediverse protocol stack in compatible ways.

In practice, this is difficult, for the following reasons:

1. The relevant protocol stack (centered around
   [ActivityPub](https://www.w3.org/TR/activitypub/), but also including
   [WebFinger](https://datatracker.ietf.org/doc/html/rfc7033),
   [HTTP signatures](https://datatracker.ietf.org/doc/html/draft-cavage-http-signatures)
   and more) is complex; implementation errors are easily made.

1. Many new implementations are being created by development teams with great
   ideas but that are under-resourced; detailed protocol testing against many other apps
   often falls by the wayside due to resource constraints. This creates bad experiences
   for users, diminishing the value of the Fediverse.

1. Several of the relevant standards comprising the technical protocol stack can be
   implemented in a variety of different ways, that – even while staying within the
   boundaries that the standards permit — nevertheless lead to incompatible implementations.

1. As different Fediverse apps tend to have different feature sets (sometimes dramatically
   so; e.g. from microblogging to video sharing and reading list management), different
   apps often implement extensions or conventions for their particular domain, all of
   which need to be at least tolerated by all other Fediverse apps. Without systematically
   testing this, app users may be in for a (bad) surprise.

1. There is a rich set of official and less official Fediverse extensions being created by
   many developers; implementations of those need to at least not conflict with others.

1. The number of Fediverse apps keeps rising from the current several dozen, and is
   expected to continue to rise for the foreseeable future. It is practically impossible for
   developers to manually test their own app against dozens of other apps even today, much
   less in the future.

1. New app releases are frequent; in theory, every app should be tested in all of its
   versions against all versions of all other apps, as it may encounter any of them
   on the Fediverse. In the current state of affairs – manual testing – this is completely
   impossible as the costs in time and effort would be astronomical.

1. There is widespread concern in the community that Fediverse apps with an outsized
   user base will not pay close attention to the underlying standards, under the
   assumption that smaller apps will have to interoperate with them regardless;
   a Fediverse test suite could at least make their non-compliance explicit.

1. Similarly, technology history is full of examples where large commercial interests
   paid lip service to supporting an open protocol and instead used a strategy of subtle
   incompatibilities and extensions to subvert the open standard, and ultimately break
   the promise of interoperability across the respective network. While automated tests
   can only do so much to make this less likely, a Fediverse test suite would make this
   strategy less likely to succeed in the Fediverse due to the resulting, immediate negative
   publicity for the entity embarking on that strategy.

A Fediverse test suite with good coverage could thus significantly contribute to:

* better user experiences, and higher utility due to higher quality of interoperability
  across the Fediverse;

* a stronger appeal and utility of the overall network to more users, and more use cases,
  without being beholden to unaccountable commercial interests;

* higher developer productivity and lower cost, leading to more value for users at
  a lower effort/cost of development;

* a well-tested foundation enables higher-level innovation, while subtle interop
  problems largely prevent it.

This has been proven true and successful for
[other formats and protocol stacks](https://www.w3.org/QA/Test/), from test suites
for markup languages like HTML and SVG to those for protocols like
[WebMention](https://www.w3.org/TR/webmention/), which, like ActivityPub, is also
maintained by the W3C.

## Prior work

No comprehensive Fediverse test suite is known to us at this time. There are some
partial implementations available under open-source licenses parts of which we may be
able to reuse. (Know some? File an issue with a pointer.)

The "ActivityPub Test Suite" originally created by Christine Lemmer-Webber in 2017
([link](https://gitlab.com/dustyweb/pubstrate/-/blob/master/pubstrate/aptestsuite.scm))
and recently ported to Python by Steve Bate
([link](https://github.com/steve-bate/rocks-testsuite)), is somewhat misnamed: a better
name for it might be a self-assessment questionnaire. While potentially useful, it
does not address the requirements addressed here.

## Intended uses of the test suite

Developers and testers run tests for many reasons. Depending on their goals, the
nature and scope of tests tend to differ. We would like to address the following
scenarios:

* A developer newly implementing Fediverse support in their app should be able to
  use the test suite to determine whether they correctly implemented the entirety of
  the relevant protocol stack, and with which other Fediverse apps their app is now
  interoperable in a manner that is consistent with what users are likely to expect.

* The community associated with the maintenance and potential evolution of a relevant
  standard (e.g. ActivityPub) should be able to use the test suite to determine
  which apps implement their respective standard correctly, and which apps have which
  deficiencies in their standard support.

* A developer about to release a new version of their Fediverse-enabled app should
  be able to integrate the test suite into their development and release process, such
  as in an automated Continuous Integration workflow, to be able to detect potential
  regressions prior to release.

## Scope for this project

In the longer term, the test suite should cover all aspects that need testing to ensure
interoperability between the Fediverse apps used in the Fediverse today, and future ones
as they are being developed. Ultimately, the best judge of whether interoperability
between two apps is satisfactory is the user and their interop expectations.

We initially focus on:

* ActivityPub server-to-server interoperability for commonly implemented activities and
  object types (list is tbd);

* Use of `@user@host` identifiers;

* Use of Webfinger to resolve identifiers into ActivityPub actor documents;

* Use of HTTP signatures to authenticate senders;

* Behavior of receiving apps consistent with the intent of the sending app (e.g.
  does the app indeed delete a note, or block a user, if requested; list tbd).

As more implementations become available, we may add support later for:

* ActivityPub client-to-server interoperability.

## Technical approach

### Basic approach

The basic technical approach is to develop a Fediverse test suite:

* That can, in principle, be used with all Fediverse apps;

* That is a single framework from which all tests can be run;

* That contains **“single-app tests”**, meaning tests that run against a single Fediverse app
  (e.g. to check whether the app publishes ActivityPub Actor files correctly);

* That contains **“interop tests”**, meaning tests in which two apps are tested against each
  other (e.g. to check whether a post made in app A will appear in the timeline of a
  follower using app B without corruption in the payload);

* Where tests are typically defined independently of the tested app (e.g. does a post
  made in app A appear in the timeline of a follower using app B, where the test can
  be run with any Fediverse apps in the roles of A and B);

* But where it is also possible to add tests that apply only to specific apps, or
  specific combinations of specific apps;

* That has facilities to limit the tests being run on any run to what is currently of
  interest to the tester;

* That can run “all tests against all known Fediverse apps and all combinations of them”
  at the limit; while it is unlikely that anybody ever would want to do that in one run
  (the effort to do so grows quadratically with the number of apps/app versions), this
  theoretical ability guarantees that the test suite architecture can accommodate any
  subset (such as testing one app against the top-10 others) a tester may be interested in.

* That produces easy-to-understand test reports.

It should be based on, or at least be informed by widely used test frameworks such as
jUnit or the Python unittest framework. This would allow us to reuse test tooling as well.

It should be implemented in an easy-to-use, widely known programming language (e.g. Python).

### Architecture overview

![Architecture](test-suite-arch.png)

### Addressing the challenges of app provisioning, observability and controllability: App Drivers

There are several practical challenges for the test framework in the interaction with specific apps:

**App provisioning:** Ideally, to run a series of tests against app A, a new instance of app
A should be provisioned for the duration of the test run, and taken down afterwards. This would:

* Keep test data and test-related load away from production servers;

* Avoid that tests run simultaneously by two different developers can interfere with each
  other if they were to run on the same test instance;

* Enable developers to debug apps while running tests, to determine the source of an error
  (e.g. to set breakpoints, or add debug logging code).

**Observability:** automated tests need to have the ability to observe whether the state
of an app instance indeed changed in response to a test as intended. Such state changes
may not always be observable on publicly accessible HTTP endpoints, and even if observable,
the location of the change may differ dramatically by app, creating observability
challenges for the test framework. (E.g. did a private message arrive?)

**Controllability:** automated tests need to have the ability to make an app “do something”,
such as make a particular post with a particular media attachment. What actions are
possible and how they can be taken also depends highly on the app, creating controllability
challenges for the test framework.

We propose to address those challenges with the notion of an **“App Driver”**.

The App Driver is an abstract programming interface that is implemented once for each
covered app. It defines methods for the above functionality, such as:

* Provisioning-related methods:

  * Provision an instance of the app, and return its root URL;

  * Deprovision an app instance;

  * Provision an account on the instance;

  * Deprovision an account.

* Observability-related methods:

  * Is post X there?

  * Has user Y been blocked?

  * Etc.

* Controllability-related methods:

  * Create a post;

  * Delete a post;

  * Edit a post.

  * Follow an account.

  * Etc.

(The exact list of methods will only become clear once the test framework and the first
actual tests are being implemented.)

There will be a default implementation for the App Driver interface, which is “manual”. This
default implementation merely tells the tester what operation to perform manually, and what
result to observe and enter manually. This manual App Driver can be used with any app,
but obviously requires lots of human time.

App Drivers for apps may choose to implement a combination of fully automated and manual.

App Drivers are most naturally implemented by the developer of the respective app.

## Organizational approach

Organizationally, the test suite will be structured in a way that it is easy for
developers from any existing or new Fediverse app A:

* To add support for their app A in the test suite, so it can be used:

  * To test their own app A;

  * By developers of other Fediverse apps B to test against app A.

* To add new test cases that can be run not only against their own app B, but also by
  other developers for configurations that do not involve app A at all. (Example: app A
  developer may discover that posts they receive that contains content using the cyrillic
  alphabet get mangled in their app, so they define an extra test case for their own app;
  this test case should now also be usable by developers of other apps)

So we foresee a single Fediverse test suite that becomes a collaborative endeavor of many
Fediverse developers, all of whom have an incentive to contribute to a single test suite
with broad coverage (in terms of tests, and in terms of covered apps) and shared effort
to keep it up-to-date.

This is best accomplished by making the test suite a well-functioning open-source
project with many contributors under a neutral organizational framework such as the
emerging Fediverse Developers Network.

## Other outcomes

Beyond the direct benefits of having automated tests (such as higher software quality,
fewer regressions, fewer frustrations for the user), we anticipate some potential
additional, indirect benefits:

* The definition of test cases makes interoperability choices transparent where apps
  with different capabilities interoperate (e.g. what is the “correct” behavior for an
  app receiving richly formatted text if the receiving app does not actually support
  richly formatted text, or how, say, event invitations should show up in a microblogging
  app). Once transparent, an easier discussion can be had about how this impacts user
  expectations and experience, and what the “best” behavior actually is.

* It opens up the possibility of a potential Fediverse conformance program, potentially
  leading to a “Interoperates with the Fediverse” logo / certification mark that could
  help reduce user confusion, like similar programs do in other industries. (Many
  questions would have to be answered before any such thing can be accomplished;
  including, for example, the question of “interop profiles”.)

## Tester experience (straw proposal)

To illustrate how a tester might interact with the test suite, consider the following.
Note that once we start implementing, the actual supported interactions may differ
substantially; so this is a straw proposal for illustrative purposes only:

### Setup

```
> git clone https://github.com/fediverse-devnet/testsuite.git
> cd testsuite
```

### Test runs

```
> fediverse-test run —single —app mastodon –all
```

This would run all tests that can be run against app Mastodon without involving another app.

```
> fediverse-test run —interop —app mastodon –all
```

This would run all interoperability tests involving app Mastodon against all other supported apps.

```
> fediverse-test run —interop —app mastodon –app pixelfed –filter media\*
```

This would run all interoperability tests between apps Mastodon and Pixelfed that involve media.

At the (practically probably infeasible) limit:

```
> fediverse-test run –all
```
This would run all known tests against all apps in all combinations.

Reports would look something like this:

```
Report:
…
ERROR: app X: does not publish outbox in Actor file
WARNING: Threads->Lemmy: post in cyrillic alphabet arrived with mangled characters
…
```

### Other

```
> fediverse-test list-tests
```

Shows all available tests.

```
> fediverse-test list-tests –app lemmy
```

Shows all available tests for app lemmy.

