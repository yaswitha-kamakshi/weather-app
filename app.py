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

    <form method="get" action="/" id="searchForm">
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


def get_coordinates(city):
    r = requests.get(GEOCODE_URL, params={"name": city, "count": 1}, timeout=10)
    r.raise_for_status()
    results = r.json().get("results")
    if not results:
        return None
    p = results[0]
    return p["latitude"], p["longitude"], p["name"], p.get("country", "")


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
    r = requests.get(WEATHER_URL, params=params, timeout=10)
    r.raise_for_status()
    return r.json()


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

        if lat is not None and lon is not None and not error:
            data = get_weather(lat, lon, unit)
            weather, theme = build_weather(name, country, data)
    except requests.exceptions.RequestException:
        error = "Network error. Check your internet connection."

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
