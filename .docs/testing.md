# Test suite overview

This section provides an overview of the test suite organization and
instructions on how to write and run the tests. The suite is fully automated
with [tox](http://tox.readthedocs.io/en/latest/), which helps standardize
the configuration and execution of individual test environments.

The main test suite structure consists of three components:

- **Unit:** Tests for isolated units of code. These tests should be extensive,
  accounting for edge cases and failure modes.
- **Integration:** Test the integration of multiple units. e.g., a component
  that relies on an external API service.
- **Functional:** End-to-end system tests that verify that the primary
  application workflows are functioning as expected. These tests are generally
  slow, as the rely on Selenium to drive a headless web browser (Google Chrome).

In addition to the test suite, tox contains test envs for linting the codebase
with [isort](https://github.com/timothycrosley/isort) and
[flake8](http://flake8.pycqa.org/en/latest/).


## Writing functional tests

Functional tests should simulate the actions of a user. In order to simulate
these actions, selenium is used to drive a web browser. You can read more about
using selenium in their [docs](http://selenium-python.readthedocs.io/). To help
reduce writing boilerplate setup code, use the `FunctionalTestCase` found in
the `project.utils.test` module. It contains a standard driver configuration,
navigation and authorization helpers, and debug logging.


## Running the test suite

If you followed the guide for setting up a development environment, then the
necessary python dependencies should already be installed. The only additional
requirement is that you have a modern version of Chrome installed (59+). Chrome
is configured as the browser driven in the functional tests.

To run the entire test suite, simply invoke `tox`.

```bash
$ tox
```

By default, tox will run all test environments. If this takes too long, or if
you only need to run a specific environment, you can specify it with the `-e`
option. First, list the available test environments.

```bash
$ tox -l
unit
integration
functional
lint
isort
warnings
```

Now that you know the names of the various test environments, you can select
the desired test envs.

```bash
$ tox -e isort,lint
```


## Continuous Integration

The project includes a Travis-CI config with a multi-stage build process. To
enable Travis, read their "[Getting Started][guide]" guide.

[guide]: https://docs.travis-ci.com/user/getting-started/
