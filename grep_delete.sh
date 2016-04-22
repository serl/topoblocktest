#!/bin/bash
shopt -s nullglob

results="$(grep --files-with-matches "$@" results/*.config)"

if [ -z "$results" ]; then
    echo "Nothing found."
    exit
fi
echo "Going to delete $(echo "$results" | wc -l) tests..."
echo "Check the regex again."
echo "One more time."
read -p "Is that ok? " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    for settings_file in $results; do
        test_files="$(echo ${settings_file%.*}.*)"
        if [ -z "$test_files" ]; then
            continue
        fi
        rm $test_files
    done
fi
