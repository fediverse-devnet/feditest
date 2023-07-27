# FAQ about the test suite

## How should we determine whether a test should pass or fail?

We use two benchmarks:

* Does the implementation conform to the relevant standards? This would check, for example,
  whether all required attributes in a message are present and have valid values.

* Does the interaction between two particular apps meet user expectations? This would check,
  for example, whether an app respects "block" requests, or preserve hyperlinks in
  the payload.

## The document talks about "single-app" tests and "interop" tests. What are they?

Here's an example for a "single-app" test:

I want to test that the WordPress ActivityPub plugin correctly emits the
right ActivityPub message when a new post is created. The test (through the App Driver)
gets WordPress to create a new test post, the test receives the message, and checks
whether it is of the right format according to the relevant standards.

Here's an example for an "interop tests" of a similar situation:

I want to test that a post made in WordPress shows up in the feed of an account
already following the WordPress site from Mastodon. The test (through the WordPress App
Driver) gets WordPress to create a new test post, waits for a bit, and then checks
(through the Mastodon App Driver) that the post has arrived, and the content is
not mangled.

## Do we need both "interop" and "single-app" tests?

"Single-app tests" are a great way to determine whether an app correctly implements
a (or several) relevant protocol standards, such as ActivityPub.

"Interop tests" test real-world interop between pairs of apps. They adress user-level
expectations and encompass such things as "does my post show up in the other app without
being distorted" in some undesirable fashion, such as dropping formatting or attachments,
character set problems, or misrepresenting semantics.

Experience in the Fediverse has shown that there are many situations
in which two apps can both be perfectly standards compliant individually, but do
not interoperate sufficiently to meet user expectations, so we need both.

## It seems really complicated to implement and run these "App Drivers"

We will only develop one -- well, at least initially -- and that one will be trivial
to implement and to run. All it does is prints out instructions to the user, and
requests certain information to be entered manually.

For example, a test may need access to an instance of Mastodon. At the point in the
test where that is needed, the test will invoke the default App Driver, which will
print:

```
Please provide the URL to a Mastodon instance we can use for testing:
```

The tester then can enter any URL reachable through curl, such as one on a locally
running VM or Docker container, or a shared one in the cloud. This is entirely up to
the user.

Alternatively, we could automate that more, by using an App Driver that instead of
instructing the user to manually do something, it does it for them. For example,
it could download and run a Docker container running Mastodon automatically,
or provision Mastodon on a cloud server.

The important part here is that the test does not need to know how Mastodon was
provisioned, and so it does not need to be changed as we increase automation.

In implementation terms, think of the "App Driver" as a Java-style "interface" that
defines some abstract methods, like "provision app" or "provision user". We
will develop a default implementation "class" that merely prints out instructions
to the user. Later, additional implementations can be defined that provide
more automation.

## This sounds like a gigantic project

we don't actually want to implement such a big test suite setup from the get-go. We
create a framework that can grow (I have it in my head, it's actually not very complicated),
and start very small with just a handful of tests.

Learn, listen, and proceed in the direction that people say would be useful.

Most importantly make it easy for developers who run into problems in the real world to
create new tests and add them to the test suite, like we all do for unit tests I guess based on reported / fixed customer bugs.

## Who would benefit from this?

Developers who are afraid of the following scenario:

A user of their app attempts to interact with somebody else on some other app that
the developer has not tested against, at least not in the relevant version, or has
never even heard of. Some interop problem occurs, the user is confused and disappointed,
and gives up on both apps and the Fediverse because "it doesn't work", as users are
prone to say.

By being able to run both single-app tests and interop tests for their app, in as
automated a fashion as we can, the risk of that is significantly diminished.

