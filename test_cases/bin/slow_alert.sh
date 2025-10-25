#!/bin/bash
# slow_alert.sh - Alert script that sleeps longer than timeout for testing
# This script is designed to test the 30-second alert timeout

echo "Alert starting - will sleep for 35 seconds..."
sleep 35
echo "Alert finished (should have been killed by timeout)"

exit 0
