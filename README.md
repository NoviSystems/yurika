# Django Skeleton

[![Build Status](https://travis-ci.org/ITNG/django-skeleton.svg?branch=master)](https://travis-ci.org/ITNG/django-skeleton)
[![Python Version](https://img.shields.io/badge/Python-3.6-blue.svg)]()
[![Django Version](https://img.shields.io/badge/Django-1.11-blue.svg)]()


Extended startproject template for new Django projects.

## Builtin Features

- [Developer usage docs](.docs)
- Flexible base template layout with navbar and dismissable flash messages
- Styled with Bootstrap 4
- Glyphicons ported from Bootstrap 3
- Out of the box auth views
    - Templates for login, password change, and password reset workflows
    - Views overridden to not clash with admin auth templates
- Sensible settings layout and environment configuration
    - Settings split into a `common_settings.py` and `settings.py`
    - Settings files for development and production
    - Per-environment configuration handled with a dotenv file
    - Environment variables validated with django-environ
- Extensive logging configuration
- Sensible dependency management
    - Application requirements managed with pip-tools
    - Separate requirements for development and testing
- Comprehensive test suite
    - Tox & Travis-CI configurations
    - Codebase linted with isort and flake8
    - Separate suites for unit, integration, and functional tests
    - Functional test suite examples with selenium+chromedriver
- Deployment script for bundling the application and build artifacts
- OAuth workflows built with oauth2client, for SSO login support
- Sentry error reporting configured with release versions
- Google Analytics


## Using this Template

Starting a new project and want to use this skeleton? Follow these steps.

1. Copy the contents of the skeleton to your new project directory.
2. Change the app name from the placeholder "appname" to a name of your
choosing in the following places:
    - The `appname` directory itself
    - In `common_settings.py`, the `INSTALLED_APPS` setting
    - In `common_settings.py`, the `LOGGING` setting
    - The import statement in the project-wide `urls.py`
3. Change the skeleton project name references to your project name.
    - The [developer docs](.docs)
4. Run `git init` and make your initial commit
5. Set up git remotes and push the initial commit to a remote repository
6. Continue to the next step for Setting up your Development Enviroment
7. Delete this readme, as it's only relevant to the skeleton!
