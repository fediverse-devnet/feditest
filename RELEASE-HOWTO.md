# Release How-To

## Merge

1. Repo `feditest`: merge `develop` into `main`
1. Repo `feditest-tests-fediverse`: merge `develop` into `main`
1. Repo `feditest-tests-sandbox`: merge `develop` into `main`

## Smoke test and test with sandbox

1. On the Mac:
   1. Repo `feditest`: `git checkout develop`
   1. In `pyproject.toml`, change `project` / `version` to the new version `VERSION` (needed so the generated files have the right version in them before check-in)
   1. Clean rebuild:
      1. `rm -rf venv.*`
      1. `make venv`
      1. `make lint`: ruff and mypy show no errors
      1. `make tests`: unit tests show no errors (smoke tests don't run on macOS)
   1. Repo `feditest-tests-sandbox`: `git checkout develop`
   1. Clean re-run and report generation of the sandbox tests:
      1. `make -f Makefile.create clean FEDITEST=../feditest/venv.darwin.default/bin/feditest`
      1. `make -f Makefile.run clean FEDITEST=../feditest/venv.darwin.default/bin/feditest`
      1. `make -f Makefile.create examples FEDITEST=../feditest/venv.darwin.default/bin/feditest`
      1. `make -f Makefile.run sandbox FEDITEST=../feditest/venv.darwin.default/bin/feditest`
      1. `open examples/testresults/*.html` and check for plausbility of reports

## Smoke test and test quickstart

1. On UBOS:
   1. Repo `feditest`: `git checkout develop`
   1. Clean rebuild:
      1. `rm -rf venv.*`
      1. `make venv`
      1. `make lint`: ruff and mypy show no errors
      1. `make tests`: unit tests and smoke tests show no errors
   1. Repo `feditest-tests-fediverse`: `git checkout develop`
   1. Clean re-run and report generation of the sandbox tests:
      1. `make -f Makefile.create clean FEDITEST=../feditest/venv.linux.main/bin/feditest`
      1. `make -f Makefile.run clean FEDITEST=../feditest/venv.linux.main/bin/feditest`
      1. `make -f Makefile.create examples FEDITEST=../feditest/venv.linux.main/bin/feditest`
      1. `make -f Makefile.run examples FEDITEST=../feditest/venv.linux.main/bin/feditest`
      1. `xdg-open examples/testresults/*.html` and check for plausbility of reports

## Tag versions

1. On the Mac:
   1. Update repo `feditest-tests-fediverse`, branch `develop`:
      1. `git tag -a vVERSION -m vVERSION`
      1. `git push`
      1. `git push --tags`
   1. Update repo `feditest-tests-sandbox`, branch `develop`:
      1. `git tag -a vVERSION -m vVERSION`
      1. `git push`
      1. `git push --tags`
   1. Update repo `feditest`, branch `develop`:
      1. `git commit` to `main`
      1. `git tag -a vVERSION -m vVERSION`
      1. `git push`
      1. `git push --tags`

## Merge into main

1. Repo `feditest-tests-fediverse`: pull request `develop` into `main`
1. Repo `feditest-tests-sandbox`: pull request `develop` into `main`
1. Repo `feditest`: pull request `develop` into `main`
1. Approve all three pull requests

## Publish to PyPi

1. On the Mac:
    1. `make release`
    1. `venv.release/bin/twine upload dist/*`
    1. `pip install --upgrade feditest`
    1. `feditest version` now shows `VERSION`

## Publish to UBOS repos

1. On UBOS:
   1. Build `feditest` for the UBOS package repos so it can be installed with `pacman -S feditest`

## Create release notes

1. Repo: `feditest.org`: create release notes
1. `git push`

## Announce

1. `https://matrix.to/#/#fediverse-testing:matrix.org`: post link to release notes
1. `@feditest@mastodon.social`: post link to release notes
