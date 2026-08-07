import os
import json
import requests
import urllib3

from datetime import datetime, timezone

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

USERNAME = os.environ["DIVER_USERNAME"]
PASSWORD = os.environ["DIVER_PASSWORD"]

BASE_URL = "https://diver-hub.com/private/api/v1"

MONITORING_POINT_ID = 74

print("Inloggen op Diver-HUB...")

login = requests.post(
    f"{BASE_URL}/Accounts/Login",
    json={
        "username": USERNAME,
        "password": PASSWORD
    },
    verify=False,
    timeout=60
)

print("Login status:", login.status_code)
print("Login response:", login.text[:1000])

login.raise_for_status()

token = login.json()["token"]

headers = {
    "Authorization": f"Bearer {token}"
}

print("Login gelukt")

test_start = int(
    datetime(2026, 3, 1, 0, 0, tzinfo=timezone.utc).timestamp()
)

test_end = int(
    datetime(2026, 3, 2, 0, 0, tzinfo=timezone.utc).timestamp()
)

tests = [
    {
        "name": "DiverData zonder datums",
        "url": f"{BASE_URL}/DiverData/ByMonitoringPoint/{MONITORING_POINT_ID}",
        "params": None
    },
    {
        "name": "DiverData met startTime/endTime",
        "url": f"{BASE_URL}/DiverData/ByMonitoringPoint/{MONITORING_POINT_ID}",
        "params": {
            "startTime": test_start,
            "endTime": test_end
        }
    },
    {
        "name": "WaterLevels controle",
        "url": f"{BASE_URL}/WaterLevels/ByMonitoringPoint/{MONITORING_POINT_ID}",
        "params": {
            "approved": "false",
            "reference": 3,
            "startTime": test_start,
            "endTime": test_end
        }
    }
]

for test in tests:
    print("")
    print("=" * 80)
    print("TEST:", test["name"])

    response = requests.get(
        test["url"],
        headers=headers,
        params=test["params"],
        verify=False,
        timeout=60
    )

    print("Final URL:", response.url)
    print("Status:", response.status_code)
    print("Content-Type:", response.headers.get("content-type"))
    print("Response eerste 3000 tekens:")
    print(response.text[:3000])

    if response.ok:
        try:
            data = response.json()
            print("JSON type:", type(data).__name__)

            if isinstance(data, list):
                print("Aantal records:", len(data))

                if data:
                    print("Eerste record:")
                    print(json.dumps(data[0], indent=2))
            elif isinstance(data, dict):
                print("Keys:", list(data.keys()))
                print(json.dumps(data, indent=2)[:3000])

        except Exception as e:
            print("Kon JSON niet parsen:", e)

print("")
print("Debug klaar")
