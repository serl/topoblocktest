#!/bin/bash


server_path=$(cat .rsyncserver 2>/dev/null)
if [ -z "$server_path" ]; then
    echo "In order to use this tool, you must write the server address and path into a file called .rsyncserver (using the rsync format, see manpage and source of this file)."
    exit
fi

rsync --compress --recursive --times --delete --progress "$server_path/results/" results/

echo
read -p "Purge Python results cache? " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    rm cache/results.pdl
fi
