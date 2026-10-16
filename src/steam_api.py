import requests

OWNED_GAMES_URL = "https://api.steampowered.com/IPlayerService/GetOwnedGames/v1/"


def get_owned_games(api_key, steam_id):
    """Return the user's games: [{"appid", "name", "playtime_forever" (minutes), ...}]."""
    params = {
        "key": api_key,
        "steamid": steam_id,
        "include_appinfo": 1,            # include the game name
        "include_played_free_games": 1,  # free games the user has played are part of the library
        "format": "json",
    }
    # Error messages from requests include the full URL, which contains the API key.
    # They are replaced by our own messages so the key never shows up in logs.
    try:
        response = requests.get(OWNED_GAMES_URL, params=params, timeout=30)
    except requests.RequestException:
        raise RuntimeError("Could not reach the Steam API") from None
    if response.status_code != 200:
        raise RuntimeError(f"Steam API returned HTTP {response.status_code}")

    data = response.json()["response"]
    # A private profile does not return an error, just an empty response
    if "games" not in data:
        raise RuntimeError("Steam API returned no games: are the profile's game details public?")
    return data["games"]
