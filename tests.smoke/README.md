# FediTest smoke tests

## Files

The files in this directory:

### Session Templates

`mastodon_api.session.json`:
: Tests our use of the Mastodon API against a single Node that implements `NodeWithMastodonAPI`, such as Mastodon or WordPress with plugins

`mastodon_api_mastodon_api.session.json`:
: Simple tests that test whether two `NodeWithMastodonAPI`s can communicate.

### Constellations

`mastodon_mastodon.ubos.constellation.json`:
: A Constellation consisting of two instances of Mastodon, running on UBOS

`mastodon.saas.constellation.json`:
: A (degenerate) Constellation consisting of only one instance of Mastodon that already runs at a public hostname

`mastodon.ubos.constellation.json`:
: A (degenerate) Constellation consisting of only one instance of Mastodon, running on UBOS

`wordpress_mastodon.ubos.constellation.json`:
: A Constellation consisting of one instance of Mastodon and one of WordPress with plugins, running on UBOS

`wordpress.saas.constellation.json`:
: A (degenerate) Constellation consisting of only one instance of WordPress with plugins that already runs at a public hostname

`wordpress.ubos.constellation.json`:
: A (degenerate) Constellation consisting of only one instance of WordPress with plugins, running on UBOS

### Actual Tests

`tests/node_with_mastodon_api.py`:
: Tests the Mastodon API

`tests/nodes_with_mastodon_api_communicate.py`:
: Tests that two nodes with the Mastodon API can communicate

## How to run

Combine a session template with a constellation, such as:

`feditest run --session mastodon_api.session.json --constellation mastodon.ubos.constellation.json`
: Runs the Mastodon API test against a single Mastodon node on UBOS

`feditest run --session mastodon_api.session.json --constellation wordpress.ubos.constellation.json`
: Runs the Mastodon API test against a single WordPress plus plugins node on UBOS

etc.

If you invoke FediTest from any directory other than this one, make sure you specify a `--testsdir <dir>` to this directory's
subdirectory `tests` so FediTest can find the test files.
