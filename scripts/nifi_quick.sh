#!/bin/bash

# NiFi Quick Commands
# Convenience wrapper for common NiFi operations

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
NIFI_CONTROL="$SCRIPT_DIR/nifi_control.sh"

# Quick start
nifi-start() {
    "$NIFI_CONTROL" start
}

# Quick stop
nifi-stop() {
    "$NIFI_CONTROL" stop
}

# Quick restart
nifi-restart() {
    "$NIFI_CONTROL" restart
}

# Quick status
nifi-status() {
    "$NIFI_CONTROL" status
}

# Quick logs
nifi-logs() {
    "$NIFI_CONTROL" logs "${1:-50}"
}

# Quick follow logs
nifi-follow() {
    "$NIFI_CONTROL" follow
}

# Export functions
export -f nifi-start
export -f nifi-stop
export -f nifi-restart
export -f nifi-status
export -f nifi-logs
export -f nifi-follow

echo "NiFi quick commands loaded:"
echo "  nifi-start    - Start NiFi"
echo "  nifi-stop     - Stop NiFi"
echo "  nifi-restart  - Restart NiFi"
echo "  nifi-status   - Show status"
echo "  nifi-logs     - Show logs"
echo "  nifi-follow   - Follow logs"
