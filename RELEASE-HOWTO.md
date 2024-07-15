# Release How-To

1. Repo `feditest`: merge `develop` into `main`
1. Repo `feditest-tests-fediverse`: merge `develop` into `main`
1. Repo `feditest-tests-sandbox`: merge `develop` into `main`

1. On the Mac:
   1. Repo `feditest`: `git checkout main`
   1. In `pyproject.toml`, change `project` / `version` to the new version `VERSION` (needed so the generated files have the right version in them before check-in)
   1. Clean rebuild:
      1. `rm -rf venv.*`
      1. `make venv PYTHON=python3`
      1. `make lint`: ruff and mypy show no errors
      1. `make`
   1. Repo `feditest-tests-sandbox`: `git checkout main`
   1. Clean re-run and report generation of the sandbox tests:
      1. `make -f Makefile.generate clean FEDITEST=../feditest/venv.darwin.main/bin/feditest`
      1. `make -f Makefile.run clean FEDITEST=../feditest/venv.darwin.main/bin/feditest`
      1. `make -f Makefile.generate examples FEDITEST=../feditest/venv.darwin.main/bin/feditest`
      1. `make -f Makefile.run sandbox FEDITEST=../feditest/venv.darwin.main/bin/feditest`
      1. `open examples/testresults/*.html` and check for plausbility of reports

1. On UBOS:
   1. Repo `feditest`: `git checkout main`
   1. Clean rebuild:
     1. `rm -rf venv.*`
     1. `make`
   1. Repo `feditest-tests-fediverse`: `git checkout main`
   1. Clean re-run and report generation of the sandbox tests:
      1. `make -f Makefile.generate clean FEDITEST=../feditest/venv.linux.main/bin/feditest`
      1. `make -f Makefile.run clean FEDITEST=../feditest/venv.linux.main/bin/feditest`
      1. `make -f Makefile.generate examples FEDITEST=../feditest/venv.linux.main/bin/feditest`
      1. `make -f Makefile.run examples FEDITEST=../feditest/venv.linux.main/bin/feditest`
      1. `xdg-open examples/testresults/*.html` and check for plausbility of reports

1. On the Mac:
   1. Update repo `feditest-tests-fediverse`
      1. `git commit` to `main`
      1. `git tag -a vVERSION -m vVERSION`
      1. `git push`
      1. `git push --tags`
   1. Update repo `feditest-tests-sandbox`
      1. `git commit` to `main`
      1. `git tag -a vVERSION -m vVERSION`
      1. `git push`
      1. `git push --tags`
   1. Update repo `feditest`:
      1. `git commit` to `main`
      1. `git tag -a vVERSION -m vVERSION`
      1. `git push`
      1. `git push --tags`
   1. Release to PyPi
      1. `make release PYTHON=python3`
      1. `venv.release/bin/twine upload dist/*`
      1. `pip install --upgrade feditest`
      1. `feditest version` now shows `VERSION`

1. On UBOS:
   1. Build `feditest` for the UBOS package repos so it can be installed with `pacman -S feditest`

1. Release notes:
   1. Repo: `feditest.org`: create release notes
   1. `git push`

1. Announce:
   1. `@feditest@mastodon.social`: post link to release notes
   1. `https://matrix.to/#/#fediverse-testing:matrix.org`: post link to release notes
