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
        "y": 475638.019,
        "maaiveld_nap": -2.91,
        "diver_nap": -4.97
    },
    {
    "id": 81,
    "name": "K070152A",
    "owner": "Kool",
    "type": "AWIS",
    "x": 124068,
    "y": 475630,
    "maaiveld_nap": -2.85,
    "diver_nap": -4.08
},
    {
        "id": 75,
        "name": "K070164A",
        "owner": "de Rooij",
        "type": "Referentie",
        "x": 124147.697,
        "y": 476393.577,
        "maaiveld_nap": -2.73,
    "diver_nap": -4.82
    },
    {
        "id": 76,
        "name": "K070165A",
        "owner": "G. Paul",
        "type": "AWIS",
        "x": 124705.929,
        "y": 475953.305,
        "maaiveld_nap": -2.96,
    "diver_nap": -5.02
    },
    {
        "id": 77,
        "name": "K070166A",
        "owner": "Kool",
        "type": "Referentie",
        "x": 124439.016,
        "y": 475596.567,
        "maaiveld_nap": -2.87,
    "diver_nap": -4.92
    },
    {
        "id": 78,
        "name": "K070167A",
        "owner": "Kroon",
        "type": "Referentie",
        "x": 123980.999,
        "y": 475854.299,
        "maaiveld_nap": -2.95,
    "diver_nap": -5.01
    },
    {
        "id": 79,
        "name": "L080248A",
        "owner": "Gijsen",
        "type": "AWIS",
        "x": 125670.905,
        "y": 474800.172,
        "maaiveld_nap": -2.25,
    "diver_nap": -4.26
    },
    {
        "id": 80,
        "name": "L070058A",
        "owner": "Gijsen",
        "type": "Referentie",
        "x": 125704.377,
        "y": 474905.177,
        "maaiveld_nap": -2.48,
    "diver_nap": -4.45
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
        f"https://diver-hub.com/private/api/v1/DiverData/"
        f"ByMonitoringPoint/{p['id']}"
        f"?startTime={start_time}"
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

        air_pressure_cm = (
            m["airPressure"] * 1.01972
        )
    
        water_column_m = (
            m["pressure"]
            - air_pressure_cm
        ) / 100.0
    
        waterlevel_nap = (
            p["diver_nap"]
            + water_column_m
        )
    
        waterlevel_mv = (
            p["maaiveld_nap"]
            - waterlevel_nap
        )
    
        m["level"] = waterlevel_mv

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
