#!/bin/sh
set -e

if [ "$1" = 'cookiecutter' ]; then
    # Set up default output (as long as -o wasn't already provided on the commandline)
    OUT_FOLDER_ARG="-o /out"
    case "$@" in
    *" -o"*) OUT_FOLDER_ARG=;;
    esac

    shift
    exec cookiecutter $OUT_FOLDER_ARG $CFG_FILE_ARG $@
elif [ "$1" = 'suggest' ]; then
    # We're wanting suggestions to transform a candidate docker commandline
    exec docker_cookiecutter $@
else
    exec $@
fi
