import os
import time
from datetime import datetime

import requests
from flask import Flask, request, render_template_string

app = Flask(__name__)

GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"
WEATHER_URL = "https://api.open-meteo.com/v1/forecast"

# code: (description, day icon, night icon)
WEATHER = {
    0: ("Clear sky", "☀️", "🌙"),
    1: ("Mainly clear", "🌤️", "🌙"),
    2: ("Partly cloudy", "⛅", "☁️"),
    3: ("Overcast", "☁️", "☁️"),
    45: ("Fog", "🌫️", "🌫️"),
    48: ("Rime fog", "🌫️", "🌫️"),
    51: ("Light drizzle", "🌦️", "🌧️"),
    53: ("Drizzle", "🌦️", "🌧️"),
    55: ("Heavy drizzle", "🌧️", "🌧️"),
    61: ("Light rain", "🌦️", "🌧️"),
    63: ("Rain", "🌧️", "🌧️"),
    65: ("Heavy rain", "🌧️", "🌧️"),
    66: ("Freezing rain", "🌧️", "🌧️"),
    67: ("Heavy freezing rain", "🌧️", "🌧️"),
    71: ("Light snow", "🌨️", "🌨️"),
    73: ("Snow", "❄️", "❄️"),
    75: ("Heavy snow", "❄️", "❄️"),
    77: ("Snow grains", "❄️", "❄️"),
    80: ("Rain showers", "🌦️", "🌧️"),
    81: ("Heavy showers", "🌧️", "🌧️"),
    82: ("Violent showers", "⛈️", "⛈️"),
    85: ("Snow showers", "🌨️", "🌨️"),
    86: ("Heavy snow showers", "❄️", "❄️"),
    95: ("Thunderstorm", "⛈️", "⛈️"),
    96: ("Thunderstorm with hail", "⛈️", "⛈️"),
    99: ("Severe thunderstorm", "⛈️", "⛈️"),
}


def describe(code, is_day=1):
    desc, day_icon, night_icon = WEATHER.get(code, ("Unknown", "🌡️", "🌡️"))
    return desc, (day_icon if is_day else night_icon)


def theme_for(code, is_day):
    if code in (95, 96, 99):
        theme = "storm"
    elif code in (71, 73, 75, 77, 85, 86):
        theme = "snow"
    elif code in (51, 53, 55, 61, 63, 65, 66, 67, 80, 81, 82):
        theme = "rain"
    elif code in (45, 48):
        theme = "fog"
    elif code in (2, 3):
        theme = "cloudy"
    else:
        theme = "clear"
    if not is_day and theme in ("clear", "cloudy", "fog"):
        theme = "night"
    return theme


PAGE = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Weather App</title>
  <style>
    * { box-sizing: border-box; }
    body { font-family: Arial, sans-serif; margin: 0; min-height: 100vh; display: flex;
           justify-content: center; padding: 32px 16px; transition: background .4s; }
    body.clear  { background: linear-gradient(135deg, #4facfe, #00f2fe); }
    body.night  { background: linear-gradient(135deg, #0f2027, #2c5364); }
    body.cloudy { background: linear-gradient(135deg, #8e9eab, #cfd9df); }
    body.rain   { background: linear-gradient(135deg, #485563, #29323c); }
    body.storm  { background: linear-gradient(135deg, #232526, #614385); }
    body.snow   { background: linear-gradient(135deg, #e6dada, #a8c0ff); }
    body.fog    { background: linear-gradient(135deg, #bdc3c7, #e0e6e8); }

    .card { background: rgba(255,255,255,.95); border-radius: 18px; padding: 26px;
            width: 100%; max-width: 480px; height: fit-content;
            box-shadow: 0 8px 28px rgba(0,0,0,.28); }
    h1 { margin: 0 0 16px; text-align: center; font-size: 26px; }
    form { display: flex; gap: 8px; flex-wrap: wrap; }
    input[type=text] { flex: 1; min-width: 140px; padding: 10px; font-size: 16px;
                       border: 1px solid #ccc; border-radius: 8px; }
    select { padding: 10px; font-size: 16px; border: 1px solid #ccc; border-radius: 8px; background: #fff; }
    button { padding: 10px 14px; font-size: 15px; background: #0077ff; color: #fff;
             border: none; border-radius: 8px; cursor: pointer; }
    button:hover { background: #005fcc; }
    .loc-btn { background: #16a34a; width: 100%; margin-top: 8px; }
    .loc-btn:hover { background: #12853d; }
    .msg { margin-top: 12px; text-align: center; color: #c00; }
    .place { text-align: center; font-size: 22px; font-weight: bold; margin: 18px 0 0; }
    .big { text-align: center; font-size: 64px; margin: 6px 0 0; }
    .temp { text-align: center; font-size: 52px; margin: 0; }
    .cond { text-align: center; color: #555; margin-bottom: 12px; font-size: 17px; }
    .row { display: flex; justify-content: space-between; align-items: center;
           padding: 7px 0; border-bottom: 1px solid #eee; }
    h3 { margin: 18px 0 6px; }
    .hourly { display: flex; gap: 10px; overflow-x: auto; padding-bottom: 8px; }
    .hour { min-width: 64px; text-align: center; background: #f1f5f9; border-radius: 12px; padding: 10px 6px; }
    .hour .t { font-size: 13px; color: #555; }
    .hour .i { font-size: 24px; margin: 4px 0; }
    .hour .d { font-weight: bold; }
    .hour .p { font-size: 11px; color: #0077ff; }
    img.emoji { height: 1em; width: 1em; margin: 0 .05em 0 .1em; vertical-align: -0.1em; }
  </style>
</head>
<body class="{{ theme }}">
  <div class="card">
    <h1>🌤 Weather App</h1>

    <form method="get" action="/" id="searchForm" onsubmit="return cleanForm(this)">
      <input type="text" name="city" placeholder="Enter city name" value="{{ city or '' }}">
      {% if lat and lon and not city %}
        <input type="hidden" name="lat" value="{{ lat }}">
        <input type="hidden" name="lon" value="{{ lon }}">
      {% endif %}
      <select name="unit" id="unit" onchange="this.form.submit()">
        <option value="c" {% if unit == 'c' %}selected{% endif %}>°C</option>
        <option value="f" {% if unit == 'f' %}selected{% endif %}>°F</option>
      </select>
      <button type="submit">Search</button>
    </form>
    <button type="button" class="loc-btn" onclick="useMyLocation()">📍 Use my location</button>
    <div class="msg" id="msg">{{ error or '' }}</div>

    {% if weather %}
      <div class="place">{{ weather.name }}{% if weather.country %}, {{ weather.country }}{% endif %}</div>
      <div class="big">{{ weather.icon }}</div>
      <div class="temp">{{ weather.temp }}{{ sym }}</div>
      <div class="cond">{{ weather.condition }} · feels like {{ weather.feels }}{{ sym }}</div>

      <div class="row"><span>💧 Humidity</span><span>{{ weather.humidity }}%</span></div>
      <div class="row"><span>💨 Wind speed</span><span>{{ weather.wind }} {{ wind_unit }}</span></div>

      <h3>Next 24 hours</h3>
      <div class="hourly">
        {% for h in weather.hourly %}
          <div class="hour">
            <div class="t">{{ h.label }}</div>
            <div class="i">{{ h.icon }}</div>
            <div class="d">{{ h.temp }}°</div>
            <div class="p">{{ h.rain }}%</div>
          </div>
        {% endfor %}
      </div>

      <h3>3-Day Forecast</h3>
      {% for d in weather.forecast %}
        <div class="row">
          <span>{{ d.icon }} {{ d.label }}</span>
          <span>{{ d.low }}° / {{ d.high }}{{ sym }}</span>
        </div>
      {% endfor %}
    {% endif %}
  </div>

  <script src="https://cdn.jsdelivr.net/npm/@twemoji/api@15.1.0/dist/twemoji.min.js" crossorigin="anonymous"></script>
  <script>
    // Replace plain system emoji with colorful, consistent icons on every device
    if (window.twemoji) { twemoji.parse(document.body, { folder: "svg", ext: ".svg" }); }

    var params = new URLSearchParams(window.location.search);

    // Remember the last successful search and reopen it next time
    {% if weather %}
      try { localStorage.setItem("lastQuery", {{ saved_query|tojson }}); } catch (e) {}
    {% endif %}
    if (!params.has("city") && !params.has("lat")) {
      try {
        var saved = localStorage.getItem("lastQuery");
        if (saved) { window.location.replace("/?" + saved); }
      } catch (e) {}
    }

    function cleanForm(form) {
      if (form.city.value.trim() !== "") {
        ["lat", "lon"].forEach(function (n) { if (form[n]) { form[n].disabled = true; } });
      }
      return true;
    }

    function useMyLocation() {
      var msg = document.getElementById("msg");
      if (!navigator.geolocation) { msg.textContent = "Geolocation is not supported by this browser."; return; }
      msg.style.color = "#555";
      msg.textContent = "Getting your location...";
      navigator.geolocation.getCurrentPosition(function (pos) {
        var unit = document.getElementById("unit").value;
        window.location.href = "/?lat=" + pos.coords.latitude.toFixed(4) +
                               "&lon=" + pos.coords.longitude.toFixed(4) + "&unit=" + unit;
      }, function () {
        msg.style.color = "#c00";
        msg.textContent = "Could not get your location. Please allow location access.";
      });
    }
  </script>
</body>
</html>
"""


class WeatherError(Exception):
    """Raised with a user-friendly message when the weather service fails."""


HEADERS = {"User-Agent": "weather-app-flask/1.0 (student project)"}
_cache = {}


def cache_get(key, ttl):
    item = _cache.get(key)
    if item and time.time() - item[0] < ttl:
        return item[1]
    return None


def cache_set(key, value):
    if len(_cache) > 500:
        _cache.clear()
    _cache[key] = (time.time(), value)
    return value


def fetch_json(url, params, bad_request_msg=None):
    """GET a URL with retries; raise WeatherError with a clear message on failure."""
    last = None
    for attempt in range(3):
        try:
            r = requests.get(url, params=params, headers=HEADERS, timeout=15)
            if r.status_code == 400 and bad_request_msg:
                raise WeatherError(bad_request_msg)
            if r.status_code in (401, 403):
                raise WeatherError("The weather API key is missing, invalid or disabled.")
            if r.status_code == 429 or r.status_code >= 500:
                app.logger.warning("Weather API returned %s for %s", r.status_code, url)
                last = WeatherError("The weather service is busy right now. Please try again in a minute.")
            else:
                r.raise_for_status()
                return r.json()
        except requests.exceptions.Timeout:
            app.logger.warning("Timeout calling %s", url)
            last = WeatherError("The weather service took too long to respond. Please try again.")
        except requests.exceptions.RequestException as e:
            app.logger.warning("Request to %s failed: %s", url, type(e).__name__)
            last = WeatherError("Could not reach the weather service. Please try again shortly.")
        if attempt < 2:
            time.sleep(1 + attempt)
    raise last


def get_coordinates(city):
    key = ("geo", city.lower())
    cached = cache_get(key, 86400)
    if cached is not None:
        return cached or None
    data = fetch_json(GEOCODE_URL, {"name": city, "count": 1})
    results = data.get("results")
    if not results:
        cache_set(key, False)
        return None
    p = results[0]
    return cache_set(key, (p["latitude"], p["longitude"], p["name"], p.get("country", "")))


def get_weather(lat, lon, unit):
    params = {
        "latitude": lat,
        "longitude": lon,
        "current": "temperature_2m,apparent_temperature,relative_humidity_2m,"
                   "wind_speed_10m,weather_code,is_day",
        "hourly": "temperature_2m,weather_code,precipitation_probability,is_day",
        "daily": "temperature_2m_max,temperature_2m_min,weather_code",
        "timezone": "auto",
        "forecast_days": 3,
        "temperature_unit": "fahrenheit" if unit == "f" else "celsius",
        "wind_speed_unit": "mph" if unit == "f" else "kmh",
    }
    key = ("wx", round(lat, 2), round(lon, 2), unit)
    cached = cache_get(key, 600)  # reuse results for 10 minutes
    if cached is not None:
        return cached
    return cache_set(key, fetch_json(WEATHER_URL, params))


# ---------- Optional provider: WeatherAPI.com (used when WEATHERAPI_KEY is set) ----------
API_KEY = os.environ.get("WEATHERAPI_KEY", "").strip()
WEATHERAPI_URL = "https://api.weatherapi.com/v1/forecast.json"

# WeatherAPI condition code -> WMO-style code used by this app
WA_TO_WMO = {
    1000: 0, 1003: 2, 1006: 3, 1009: 3, 1030: 45, 1135: 45, 1147: 48,
    1063: 61, 1150: 51, 1153: 51, 1168: 53, 1171: 55,
    1180: 61, 1183: 61, 1186: 63, 1189: 63, 1192: 65, 1195: 65,
    1198: 66, 1201: 67, 1204: 66, 1207: 67, 1072: 51,
    1066: 71, 1114: 73, 1117: 75, 1210: 71, 1213: 71, 1216: 73, 1219: 73,
    1222: 75, 1225: 75, 1237: 77, 1069: 66,
    1240: 80, 1243: 81, 1246: 82,
    1249: 85, 1252: 86, 1255: 85, 1258: 86, 1261: 85, 1264: 86,
    1087: 95, 1273: 95, 1276: 95, 1279: 95, 1282: 95,
}


def wa_time(value):
    """WeatherAPI times can have unpadded hours; return ISO 'YYYY-MM-DDTHH:MM'."""
    return datetime.strptime(value, "%Y-%m-%d %H:%M").strftime("%Y-%m-%dT%H:%M")


def get_weather_weatherapi(query, unit):
    """Fetch from WeatherAPI.com and reshape to the same structure build_weather expects."""
    key = ("wa", query.lower(), unit)
    cached = cache_get(key, 600)
    if cached is not None:
        return cached

    data = fetch_json(
        WEATHERAPI_URL,
        {"key": API_KEY, "q": query, "days": 3, "aqi": "no", "alerts": "no"},
        bad_request_msg="City not found. Please try another name.",
    )

    f = unit == "f"
    t_key = "temp_f" if f else "temp_c"
    feel_key = "feelslike_f" if f else "feelslike_c"
    wind_key = "wind_mph" if f else "wind_kph"
    max_key = "maxtemp_f" if f else "maxtemp_c"
    min_key = "mintemp_f" if f else "mintemp_c"

    loc, cur, days = data["location"], data["current"], data["forecast"]["forecastday"]

    hourly = {"time": [], "temperature_2m": [], "weather_code": [],
              "precipitation_probability": [], "is_day": []}
    for d in days:
        for h in d["hour"]:
            hourly["time"].append(wa_time(h["time"]))
            hourly["temperature_2m"].append(h[t_key])
            hourly["weather_code"].append(WA_TO_WMO.get(h["condition"]["code"], 3))
            hourly["precipitation_probability"].append(h.get("chance_of_rain", 0))
            hourly["is_day"].append(h["is_day"])

    daily = {"time": [d["date"] for d in days],
             "temperature_2m_max": [d["day"][max_key] for d in days],
             "temperature_2m_min": [d["day"][min_key] for d in days],
             "weather_code": [WA_TO_WMO.get(d["day"]["condition"]["code"], 3) for d in days]}

    current = {"time": wa_time(loc["localtime"]),
               "temperature_2m": cur[t_key],
               "apparent_temperature": cur[feel_key],
               "relative_humidity_2m": cur["humidity"],
               "wind_speed_10m": cur[wind_key],
               "weather_code": WA_TO_WMO.get(cur["condition"]["code"], 3),
               "is_day": cur["is_day"]}

    result = ({"current": current, "hourly": hourly, "daily": daily},
              loc.get("name", ""), loc.get("country", ""))
    return cache_set(key, result)


def build_weather(name, country, data):
    cur, hourly, daily = data["current"], data["hourly"], data["daily"]
    desc, icon = describe(cur["weather_code"], cur["is_day"])

    # find the current hour in the hourly list, then take the next 24
    start = 0
    for i, t in enumerate(hourly["time"]):
        if t[:13] == cur["time"][:13]:
            start = i
            break
    hours = []
    for i in range(start, min(start + 24, len(hourly["time"]))):
        _, h_icon = describe(hourly["weather_code"][i], hourly["is_day"][i])
        label = datetime.fromisoformat(hourly["time"][i]).strftime("%I %p").lstrip("0")
        hours.append({
            "label": label,
            "icon": h_icon,
            "temp": round(hourly["temperature_2m"][i]),
            "rain": hourly["precipitation_probability"][i] or 0,
        })

    forecast = []
    for i, day in enumerate(daily["time"]):
        _, d_icon = describe(daily["weather_code"][i], 1)
        forecast.append({
            "label": datetime.fromisoformat(day).strftime("%a, %d %b"),
            "icon": d_icon,
            "high": round(daily["temperature_2m_max"][i]),
            "low": round(daily["temperature_2m_min"][i]),
        })

    weather = {
        "name": name,
        "country": country,
        "temp": round(cur["temperature_2m"]),
        "feels": round(cur["apparent_temperature"]),
        "humidity": cur["relative_humidity_2m"],
        "wind": cur["wind_speed_10m"],
        "condition": desc,
        "icon": icon,
        "hourly": hours,
        "forecast": forecast,
    }
    return weather, theme_for(cur["weather_code"], cur["is_day"])


@app.route("/")
def home():
    city = request.args.get("city", "").strip()
    unit = "f" if request.args.get("unit") == "f" else "c"
    lat_arg = request.args.get("lat", "")
    lon_arg = request.args.get("lon", "")

    weather, error, theme = None, None, "clear"
    lat = lon = None

    try:
        name, country = "", ""
        if city:
            if not API_KEY:
                location = get_coordinates(city)
                if not location:
                    error = "City not found. Please try another name."
                else:
                    lat, lon, name, country = location
        elif lat_arg and lon_arg:
            try:
                lat, lon = float(lat_arg), float(lon_arg)
                if not (-90 <= lat <= 90 and -180 <= lon <= 180):
                    raise ValueError
                name = "Your location"
            except ValueError:
                error = "Invalid location."
                lat = lon = None

        if not error:
            if API_KEY and (city or lat is not None):
                query = city if city else f"{lat:.4f},{lon:.4f}"
                data, api_name, api_country = get_weather_weatherapi(query, unit)
                weather, theme = build_weather(api_name or name, api_country, data)
            elif lat is not None and lon is not None:
                data = get_weather(lat, lon, unit)
                weather, theme = build_weather(name, country, data)
    except WeatherError as e:
        error = str(e)

    return render_template_string(
        PAGE,
        city=city,
        unit=unit,
        sym="°F" if unit == "f" else "°C",
        wind_unit="mph" if unit == "f" else "km/h",
        weather=weather,
        error=error,
        theme=theme,
        lat=lat_arg if not city else "",
        lon=lon_arg if not city else "",
        saved_query=request.query_string.decode(),
    )
