#!/bin/bash
INPUT=$(cat)
PROMPT=$(echo "$INPUT" | jq -r '.prompt')
TIMESTAMP=$(echo "$INPUT" | jq -r '.timestamp')

echo "$(date -d @$((TIMESTAMP/1000))): $PROMPT" >> audit/prompts.log

exit 0
