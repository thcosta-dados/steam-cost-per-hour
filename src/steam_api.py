import requests

OWNED_GAMES_URL = "https://api.steampowered.com/IPlayerService/GetOwnedGames/v1/"


def get_owned_games(api_key, steam_id, include_played_free_games):
    """Return the user's games: [{"appid", "name", "playtime_forever" (minutes), ...}].

    include_played_free_games=False returns only games the user has a license for.
    """
    params = {
        "key": api_key,
        "steamid": steam_id,
        "include_appinfo": 1,  # include the game name
        "include_played_free_games": int(include_played_free_games),
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
    return games_from_response(response.json()["response"])


def games_from_response(data):
    # A private profile does not return an error, just an empty response: {}.
    # An account with no games returns {"game_count": 0}, which is valid.
    if "game_count" not in data:
        raise RuntimeError("Steam API returned an empty response: are the profile's game details public?")
    return data.get("games", [])
