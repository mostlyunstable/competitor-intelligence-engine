#!/bin/bash
echo "Starting API Server..."
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 &
API_PID=$!

sleep 5

echo "Starting Monitor..."
uv run python scripts/monitor.py &
MON_PID=$!

sleep 2

USERS=(10 50 100)
for u in "${USERS[@]}"; do
    echo "Running Load Test with $u users..."
    uv run locust -f locustfile.py --headless -u $u -r $((u/2)) -t 10s --csv "locust_out_${u}" --host=http://localhost:8000
    sleep 2
done

# Note: 500 and 1000 users may crash the container depending on limits, but let's try them briefly
USERS_HIGH=(500 1000)
for u in "${USERS_HIGH[@]}"; do
    echo "Running Load Test with $u users..."
    uv run locust -f locustfile.py --headless -u $u -r $((u/2)) -t 10s --csv "locust_out_${u}" --host=http://localhost:8000
    sleep 2
done

echo "Killing processes..."
kill $MON_PID
kill $API_PID
echo "Done!"
