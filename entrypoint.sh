#!/bin/sh
set -e

if [ "$1" = 'cookiecutter' ]; then
    # If the config file exists and we haven't provided an explicit config file on the 
    # commandline, then we should provide that to the command
    case "$@" in
    *" --config-file"*) CFG_FILE_ARG=;;
    *)  if [ "$CFG_FILE" ] && [ -f "$CFG_FILE" ]; then 
            CFG_FILE_ARG="--config-file \"$CFG_FILE\""
        fi;;
    esac

    # Set up default output (as long as -o wasn't already provided on the commandline)
    OUT_FOLDER_ARG="-o /out"
    case "$@" in
    *" -o"*) OUT_FOLDER_ARG=;;
    esac

    shift
    exec cookiecutter $OUT_FOLDER_ARG $CFG_FILE_ARG $@
elif [ "$1" = 'suggest' ]; then
    # We're wanting suggestions to transform a candidate docker commandline
    exec python /util/suggest.py $@
else
    exec $@
fi
