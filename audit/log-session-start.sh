#!/bin/bash
INPUT=$(cat)
SOURCE=$(echo "$INPUT" | jq -r '.source')
TIMESTAMP=$(echo "$INPUT" | jq -r '.timestamp')

echo "Session started from $SOURCE at $TIMESTAMP" >> audit/session.log

exit 0
