#!/usr/bin/env python
import os
import sys

import environ

if __name__ == "__main__":
    environ.Env.read_env(
        os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    )

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)
