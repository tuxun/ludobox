#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Python 3 compatibility
from __future__ import print_function

import os
import glob
import shutil
import argparse
import py

from ludobox.webserver import serve


# TODO: move this to config file
INPUT_DIR = os.path.join(os.getcwd(),"data")
OUTPUT_DIR = os.path.join(os.getcwd(),"static")

def clean(**kwargs):
    """Delete tmp files"""

    print("Remove all precompiled python files (*.pyc): ", end='')
    for f in glob.glob("server/**/*.pyc"):
        os.remove(f)
    print("SUCCESS")

    print("Remove all python generated object files (*.pyo): ", end='')
    for f in glob.glob("server/**/*.pyo"):
        os.remove(f)
    print("SUCCESS")

    print("Remove py.test caches directory (__pycache__): ", end='')
    shutil.rmtree("__pycache__", ignore_errors=True)
    shutil.rmtree("server/tests/__pycache__", ignore_errors=True)
    print("SUCCESS")

def test(**kwargs):
    """Run tests from the command line"""
    py.test.cmdline.main("server/tests")

# TODO add an info action that list the default dirs, all actual games
#   installed
def config_parser():
    """Configure the argument parser and returns it."""
    # Initialise the parsers
    parser = argparse.ArgumentParser(description="Ludobox server.")

    # Add all the actions (subcommands)
    subparsers = parser.add_subparsers(
        title="actions",
        description="the program needs to know what action you want it to do.",
        help="those are all the possible actions")

    # Test command ###########################################################
    parser_serve = subparsers.add_parser(
        "test",
        help="Run server tests.")
    parser_serve.set_defaults(func=test)

    # Clean command ###########################################################
    parser_serve = subparsers.add_parser(
        "clean",
        help="Remove usuless and temp files from the folder.")
    parser_serve.set_defaults(func=clean)

    # Serve command ###########################################################
    parser_serve = subparsers.add_parser(
        "serve",
        help="Launch an tiny web server to make the ludobox site available.")

    parser_serve.add_argument(
        "--debug",
        default=False,
        action='store_true',
        help="activate the debug mode of the Flask server (for development "
             "only NEVER use it in production).")
    parser_serve.add_argument(
        "--port",
        default=None,
        help="define port to serve the web application.")

    # Returns the, now configured, parser
    return parser


def main(commands=None):
    """
    Launch command parser from real command line or from args.

    This allow easy testing of the command line options/actions.
    """
    # Configure the parser
    parser = config_parser()

    # Parse the args
    if commands is None:
        # When executed has a script
        args = parser.parse_args()
    else:
        # When executed in the tests
        args = parser.parse_args(commands.split())

    # Call whatever function was selected
    return args.func(**vars(args))  # We use `vars` to convert args to a dict


if __name__ == "__main__":
    main()
