# FAQ about the test suite

Note: We use the term "server-side app" to describe an instance of a project such as
Mastodon. (Don't confuse it with mobile apps; we don't talk about those here.)

## How should we determine whether a test should pass or fail?

We use two benchmarks:

* Does the implementation conform to the relevant standards? This would check, for example,
  whether all required attributes in a message are present and have valid values.

* Does the interaction between two particular server-side apps meet user expectations?
  This would check, for example, whether a server-side app respects "block" requests,
  or preserves hyperlinks in the payload.

## The document talks about "single-app" tests and "interop" tests. What are they?

Here's an example for a "single-app" test:

I want to test that the WordPress ActivityPub plugin correctly emits the right ActivityPub
message when a new post is published in WordPress. The test (through the App Driver)
gets WordPress to create a new test post, the test receives the message, and checks
whether it is of the right format according to the relevant standards.

Here's an example for an "interop test" of a similar situation:

I want to test that a post made in WordPress shows up in the feed of an account
already following the WordPress site from Mastodon. The test (through the WordPress App
Driver) gets WordPress to create a new test post, waits for a bit, and then checks
(through the Mastodon App Driver) that the post has arrived, and the content is
not mangled.

## Do we need both "interop" and "single-app" tests?

"Single-app tests" are a great way to determine whether a server-side app correctly implements
a (or several) relevant protocol standards, such as ActivityPub.

"Interop tests" test real-world interop between pairs of server-side apps. They adress
user-level expectations and encompass such things as "does my post show up in the other
server-side app without being distorted" in some undesirable fashion, such as dropping
formatting or attachments, character set problems, or misrepresenting semantics.

Experience in the Fediverse has shown that there are many situations in which two
server-side apps can both be perfectly standards compliant individually, but do
not interoperate sufficiently to meet user expectations, so we need both.

## How are you going to test the "receiving" of messages?

Single-app tests need a test framework that implements some aspects of the protocol
stack itself, so it can open up a port, serve WebFinger requests, receive
ActivityPub messages etc.'

We will use a webserver embedded in the test framework for this. This gives us maximum
controllability and observability and makes tests easier to write.

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
running Virtual Machine or Docker container, or a shared one in the cloud. This is entirely
up to the user running the test suite.

In the future, we could automate that more, by using an App Driver that instead of
instructing the user to manually do something, it does it for them. For example,
it could download and run a Docker container running Mastodon automatically,
or provision Mastodon on a cloud server.

## Which App Driver to use should be configurable by the user.

The important part here is that the test does not need to know how Mastodon was
provisioned, and so it does not need to be changed as we increase automation, if and
when we do that.

In implementation terms, think of the concept of an "App Driver" as a Java-style "interface"
that defines some abstract methods, like "provision app" or "provision user". We
will develop a default implementation "class" that merely prints out instructions
to the user. Later, additional implementations can be defined that provide
more automation.

## Are you going to start this project from scratch, or are you building on something that exists already?

We will be building on Steve Bate's [ActivityPub Testsuite](https://github.com/steve-bate/activitypub-testsuite).
It is already structured according to this approach, including App Drivers (he calls them
"Server Abstract Layer").
