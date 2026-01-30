#!/bin/bash
INPUT=$(cat)
REASON=$(echo "$INPUT" | jq -r '.reason')

echo "Session ended: $REASON" >> audit/session.log
