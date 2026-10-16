import requests

APP_DETAILS_URL = "https://store.steampowered.com/api/appdetails"


def get_app_details(app_id):
    """Return the raw store response for one app: {"success": bool, "data": {...}}."""
    params = {
        "appids": app_id,
        "cc": "br",       # Brazilian store: prices in BRL
        "l": "english",   # genre names in English, so the classification rule is stable
    }
    response = requests.get(APP_DETAILS_URL, params=params, timeout=30)
    if response.status_code != 200:
        # 429 means too many requests: progress is saved, run again later
        raise RuntimeError(f"Steam store returned HTTP {response.status_code} for app {app_id}")
    return response.json()[str(app_id)]
