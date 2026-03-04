#!/bin/bash

GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

echo "--- CERN Telemetry System Smoke Test ---"

wait_for_service() {
    local url=$1
    local name=$2
    local retries=15
    local wait_time=5

    echo -n "Checking $name... "
    for i in $(seq 1 $retries); do
        STATUS=$(curl -s -L -k -o /dev/null -w "%{http_code}" "$url")
        
        if [[ "$STATUS" == "200" || "$STATUS" == "301" ]]; then
            echo -e "${GREEN}PASS${NC}"
            return 0
        fi
        sleep $wait_time
    done
    echo -e "${RED}FAIL (Status $STATUS - Timed out after $retries attempts)${NC}"
    return 1
}

# 1. Test Java API via Nginx
wait_for_service "http://localhost/api/v1/telemetry/history" "Java Telemetry Service"

# 2. Test Django Status API via Nginx
wait_for_service "http://localhost/api/get-lhc-status/" "Django Backend"

# 3. Test C++ Data Injection (Verify data is flowing into DB)
echo -n "Checking C++ -> Java Persistence Bridge... "
sleep 15
DATA=$(curl -s -L -k http://localhost/api/v1/telemetry/history)

if [[ $DATA == *"sensorId"* ]]; then
    echo -e "${GREEN}PASS (Data is flowing!)${NC}"
else
    echo -e "${RED}FAIL (No sensor data found in history)${NC}"
fi

echo "---------------------------------------"
