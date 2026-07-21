import os
import json
import requests

from datetime import datetime, timedelta

USERNAME = os.environ["DIVER_USERNAME"]
PASSWORD = os.environ["DIVER_PASSWORD"]

POINTS = [
    {
        "id": 74,
        "name": "K070163A",
        "owner": "Kool",
        "type": "AWIS",
        "x": 124638.861,
        "y": 475738.019
    },
    {
    "id": 81,
    "name": "K070152A",
    "owner": "Kool",
    "type": "AWIS",
    "x": 124068,
    "y": 475730
},
    {
        "id": 75,
        "name": "K070164A",
        "owner": "de Rooij",
        "type": "Referentie",
        "x": 124147.697,
        "y": 476493.577
    },
    {
        "id": 76,
        "name": "K070165A",
        "owner": "G. Paul",
        "type": "AWIS",
        "x": 124705.929,
        "y": 476053.305
    },
    {
        "id": 77,
        "name": "K070166A",
        "owner": "Kool",
        "type": "Referentie",
        "x": 124439.016,
        "y": 475696.567
    },
    {
        "id": 78,
        "name": "K070167A",
        "owner": "Kroon",
        "type": "Referentie",
        "x": 123980.999,
        "y": 475954.299
    },
    {
        "id": 79,
        "name": "L080248A",
        "owner": "Gijsen",
        "type": "AWIS",
        "x": 125670.905,
        "y": 474800.172
    },
    {
        "id": 80,
        "name": "L070058A",
        "owner": "Gijsen",
        "type": "Referentie",
        "x": 125704.377,
        "y": 474905.177
    }
]

print("Inloggen op Diver-HUB...")

login = requests.post(
    "https://diver-hub.com/private/api/v1/Accounts/Login",
    json={
        "username": USERNAME,
        "password": PASSWORD
    },
    verify=False
)

login.raise_for_status()

token = login.json()["token"]

headers = {
    "Authorization": f"Bearer {token}"
}

print("Login gelukt")

end_time = int(datetime.now().timestamp())

start_time = int(
    (
        datetime.now()
        - timedelta(days=365)
    ).timestamp()
)

dashboard_data = []

for p in POINTS:

    print(f"Ophalen: {p['name']}")

    url = (
        f"https://diver-hub.com/private/api/v1/WaterLevels/"
        f"ByMonitoringPoint/{p['id']}"
        f"?approved=false"
        f"&reference=3"
        f"&startTime={start_time}"
        f"&endTime={end_time}"
    )

    r = requests.get(
        url,
        headers=headers,
        verify=False
    )

    r.raise_for_status()

    measurements = r.json()

    for m in measurements:
        m["level"] = -m["level"]

    dashboard_data.append({

        "id": p["id"],
        "name": p["name"],
        "owner": p["owner"],
        "type": p["type"],
        "x": p["x"],
        "y": p["y"],

        "current":
            measurements[-1]["level"]
            if measurements
            else None,

        "measurements":
            measurements

    })

with open(
    "groundwater.json",
    "w",
    encoding="utf-8"
) as f:

    json.dump(
        dashboard_data,
        f,
        ensure_ascii=False
    )

print("groundwater.json bijgewerkt")
