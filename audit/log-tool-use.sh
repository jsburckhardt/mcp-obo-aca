#!/bin/bash
INPUT=$(cat)
TOOL_NAME=$(echo "$INPUT" | jq -r '.toolName')
TOOL_ARGS=$(echo "$INPUT" | jq -r '.toolArgs')

echo "$(date): Tool=$TOOL_NAME Args=$TOOL_ARGS" >> audit/tool-usage.log

# Check for dangerous patterns
if echo "$TOOL_ARGS" | grep -qE "rm -rf /|format|DROP TABLE"; then
  echo '{"permissionDecision":"deny","permissionDecisionReason":"Dangerous command detected"}'
  exit 0
fi

echo '{"permissionDecision":"allow"}'
