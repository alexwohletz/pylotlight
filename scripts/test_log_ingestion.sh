#!/bin/bash

source=$1
message=$2
level=${3:-INFO}
component=${4:-test_component}

if [ -z "$source" ] || [ -z "$message" ]; then
    echo "Usage: $0 <source> <message> [level] [component]"
    exit 1
fi

timestamp=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

curl -X POST http://localhost:8000/ingest_log \
     -H "Content-Type: application/json" \
     -d "{
           \"source\": \"$source\",
           \"timestamp\": \"$timestamp\",
           \"data\": {
             \"message\": \"$message\",
             \"level\": \"$level\",
             \"component\": \"$component\"
           }
         }"

echo