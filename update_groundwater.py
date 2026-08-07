import os
import json
import requests
import urllib3

from datetime import datetime, timedelta, timezone

# Verberg waarschuwingen door verify=False
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

USERNAME = os.environ["DIVER_USERNAME"]
PASSWORD = os.environ["DIVER_PASSWORD"]

BASE_URL = "https://diver-hub.com/private/api/v1"

# Data begint op 1 maart.
# Pas het jaar aan als nodig, bijvoorbeeld "2025-03-01".
START_DATE_TEXT = "2026-03-01"

# Ruwe data in blokken ophalen.
# Als Diver-HUB nog steeds 500-errors geeft, zet deze op 14 of 7.
CHUNK_DAYS = 30

# Omrekening:
# airPressure komt uit de API in hPa.
# pressure komt uit de API in cmH2O.
# 1 hPa = 1.019716 cmH2O.
HPA_TO_CMH2O = 1.019716

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


def parse_start_date(date_text):
    return datetime.strptime(date_text, "%Y-%m-%d").replace(tzinfo=timezone.utc)


def fetch_diver_data_for_point(point, headers, start_dt, end_dt):
    """
    Haalt alle ruwe DiverData op voor één monitoring point.
    De data wordt in blokken opgehaald om API-errors bij grote periodes te voorkomen.
    """

    all_measurements = []
    seen_timestamps = set()

    chunk_start = start_dt

    while chunk_start < end_dt:
        chunk_end = min(
            chunk_start + timedelta(days=CHUNK_DAYS),
            end_dt
        )

        url = (
            f"{BASE_URL}/DiverData/"
            f"ByMonitoringPoint/{point['id']}"
        )

        params = {
            "startTime": int(chunk_start.timestamp()),
            "endTime": int(chunk_end.timestamp())
        }

        print(
            f"  {point['name']}: ophalen "
            f"{chunk_start.date()} t/m {chunk_end.date()}"
        )

        response = requests.get(
            url,
            headers=headers,
            params=params,
            verify=False,
            timeout=60
        )

        if not response.ok:
            print("  Fout bij DiverData request")
            print("  URL:", response.url)
            print("  Status:", response.status_code)
            print("  Response:", response.text[:2000])
            response.raise_for_status()

        chunk_data = response.json()

        for measurement in chunk_data:
            timestamp = measurement.get("dateAndTime")

            if timestamp is None:
                continue

            if timestamp not in seen_timestamps:
                seen_timestamps.add(timestamp)
                all_measurements.append(measurement)

        # Een seconde opschuiven voorkomt dubbele metingen op de blokgrens.
        chunk_start = chunk_end + timedelta(seconds=1)

    all_measurements.sort(
        key=lambda m: m.get("dateAndTime", "")
    )

    return all_measurements


def calculate_groundwater_levels(measurements, point):
    """
    Zet ruwe drukdata om naar grondwaterstanden onder maaiveld.

    API-velden:
    - pressure: absolute druk van de diver in cmH2O
    - airPressure: luchtdruk in hPa

    Berekening:
    air_pressure_cm = airPressure * 1.019716
    water_column_m = (pressure - air_pressure_cm) / 100
    waterlevel_nap = diver_nap + water_column_m
    level = maaiveld_nap - waterlevel_nap

    level is dus de grondwaterstand in meter onder maaiveld.
    """

    calculated_measurements = []

    for measurement in measurements:
        pressure = measurement.get("pressure")
        air_pressure = measurement.get("airPressure")

        if pressure is None or air_pressure is None:
            continue

        air_pressure_cm = air_pressure * HPA_TO_CMH2O

        water_column_m = (
            pressure - air_pressure_cm
        ) / 100.0

        waterlevel_nap = (
            point["diver_nap"]
            + water_column_m
        )

        waterlevel_mv = (
            point["maaiveld_nap"]
            - waterlevel_nap
        )

        measurement["water_column_m"] = round(water_column_m, 4)
        measurement["waterlevel_nap"] = round(waterlevel_nap, 4)

        # Deze naam blijft hetzelfde voor je dashboard.
        # Dit is grondwaterstand in meter onder maaiveld.
        measurement["level"] = round(waterlevel_mv, 4)

        calculated_measurements.append(measurement)

    calculated_measurements.sort(
        key=lambda m: m.get("dateAndTime", "")
    )

    return calculated_measurements


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

login.raise_for_status()

token = login.json()["token"]

headers = {
    "Authorization": f"Bearer {token}"
}

print("Login gelukt")

start_dt = parse_start_date(START_DATE_TEXT)
end_dt = datetime.now(timezone.utc)

print(f"Data ophalen vanaf {start_dt.date()} t/m {end_dt.date()}")

dashboard_data = []

for point in POINTS:
    print(f"Ophalen: {point['name']}")

    measurements = fetch_diver_data_for_point(
        point=point,
        headers=headers,
        start_dt=start_dt,
        end_dt=end_dt
    )

    measurements = calculate_groundwater_levels(
        measurements=measurements,
        point=point
    )

    current = None

    if measurements:
        current = measurements[-1].get("level")

    dashboard_data.append({
        "id": point["id"],
        "name": point["name"],
        "owner": point["owner"],
        "type": point["type"],
        "x": point["x"],
        "y": point["y"],
        "maaiveld_nap": point["maaiveld_nap"],
        "diver_nap": point["diver_nap"],
        "current": current,
        "measurements": measurements
    })

with open(
    "groundwater.json",
    "w",
    encoding="utf-8"
) as file:
    json.dump(
        dashboard_data,
        file,
        ensure_ascii=False,
        indent=2
    )

print("groundwater.json bijgewerkt")
