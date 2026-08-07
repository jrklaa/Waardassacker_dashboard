import os
import json
import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

USERNAME = os.environ["DIVER_USERNAME"]
PASSWORD = os.environ["DIVER_PASSWORD"]

BASE_URL = "https://diver-hub.com/private/api/v1"

# Omrekening:
# airPressure uit API = hPa
# pressure uit API = cmH2O
# 1 hPa = 1.019716 cmH2O
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


def normalize_measurements(response_json):
    """
    Zorgt dat de API-response altijd als lijst wordt behandeld.

    Soms geeft een API direct een lijst terug:
        [{...}, {...}]

    Soms zit de lijst in een veld zoals:
        {"data": [{...}, {...}]}
        {"items": [{...}, {...}]}
        {"measurements": [{...}, {...}]}
    """

    if isinstance(response_json, list):
        return response_json

    if isinstance(response_json, dict):
        for key in ["data", "items", "measurements", "values", "result"]:
            value = response_json.get(key)

            if isinstance(value, list):
                return value

    return []


def fetch_diver_data(point, headers):
    """
    Haalt alle ruwe DiverData op voor één monitoring point,
    zonder startTime en endTime in de URL.
    """

    url = (
        f"{BASE_URL}/DiverData/"
        f"ByMonitoringPoint/{point['id']}"
    )

    response = requests.get(
        url,
        headers=headers,
        verify=False,
        timeout=120
    )

    if not response.ok:
        print("Fout bij ophalen DiverData")
        print("Meetpunt:", point["name"], point["id"])
        print("URL:", response.url)
        print("Status:", response.status_code)
        print("Response:", response.text[:2000])
        response.raise_for_status()

    response_json = response.json()
    measurements = normalize_measurements(response_json)

    return measurements


def calculate_groundwater_levels(measurements, point):
    """
    Zet ruwe drukdata om naar grondwaterstand onder maaiveld.

    Formule:
    air_pressure_cm = airPressure * 1.019716
    water_column_m = (pressure - air_pressure_cm) / 100
    waterlevel_nap = diver_nap + water_column_m
    level = maaiveld_nap - waterlevel_nap

    level = meter onder maaiveld.
    """

    calculated = []
    skipped = 0

    for measurement in measurements:
        pressure = measurement.get("pressure")
        air_pressure = measurement.get("airPressure")

        if pressure is None or air_pressure is None:
            skipped += 1
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

        # Dit veld gebruikt je dashboard waarschijnlijk al.
        # Positieve waarde betekent: zoveel meter onder maaiveld.
        measurement["level"] = round(waterlevel_mv, 4)

        calculated.append(measurement)

    calculated.sort(
        key=lambda m: m.get("dateAndTime", "")
    )

    if skipped > 0:
        print(
            f"Waarschuwing: {skipped} metingen overgeslagen bij "
            f"{point['name']} door ontbrekende pressure of airPressure"
        )

    return calculated


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

dashboard_data = []

for point in POINTS:
    print(f"Ophalen: {point['name']}")

    measurements = fetch_diver_data(
        point=point,
        headers=headers
    )

    print(
        f"  {point['name']}: {len(measurements)} ruwe metingen opgehaald"
    )

    measurements = calculate_groundwater_levels(
        measurements=measurements,
        point=point
    )

    print(
        f"  {point['name']}: {len(measurements)} metingen omgerekend"
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
