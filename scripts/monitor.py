import httpx
import time
import csv
import sys
from datetime import datetime

API_URL = "http://localhost:8000/debug/metrics"
OUTPUT_FILE = "system_metrics.csv"

def run_monitor():
    print(f"Starting monitor, writing to {OUTPUT_FILE}")
    with open(OUTPUT_FILE, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["timestamp", "cpu_percent", "ram_mb", "db_pool_size", "db_checkedin", "db_checkedout", "worker_queue_depth"])
        
        while True:
            try:
                res = httpx.get(API_URL, timeout=2.0)
                if res.status_code == 200:
                    data = res.json()
                    writer.writerow([
                        datetime.now().isoformat(),
                        data.get("cpu_percent", 0),
                        data.get("ram_mb", 0),
                        data.get("db_pool_size", 0),
                        data.get("db_checkedin", 0),
                        data.get("db_checkedout", 0),
                        data.get("worker_queue_depth", 0)
                    ])
                    f.flush()
            except Exception as e:
                print(f"Monitor error: {e}")
            
            time.sleep(1)

if __name__ == "__main__":
    try:
        run_monitor()
    except KeyboardInterrupt:
        print("Monitor stopped.")
        sys.exit(0)
