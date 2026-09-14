"""
live_calamity_tracker.py - Real-Time Natural Calamity & Aviation Weather Disruption Tracker
Smart India Hackathon 2026 (PS SIH26056)

Connects to:
1. Official Aviation Weather METAR API (aviationweather.gov) for 16 major Indian airport stations:
   - VIDP (Delhi), VABB (Mumbai), VOBL (Bengaluru), VECC (Kolkata), VOMM (Chennai), VOHS (Hyderabad),
     VEPT (Patna), VEBI (Bhubaneswar), VEGT (Guwahati), VISR (SXR), VIAR (Amritsar), VILK (Lucknow),
     VOGO (Goa), VOCI (Kochi), VAAH (Ahmedabad), VAPO (Pune).
2. UN Global Disaster Alert and Coordination System (GDACS) for real-time Cyclone, Flood, and Earthquake alerts in India.

Provides real-time operational risk ratings, capacity cut recommendations, and route impact matrices.
"""

import os
import time
import json
import ssl
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime

# Airport mappings: ICAO -> IATA, City, Name, Corridors
INDIAN_AIRPORT_STATIONS = {
    'VIDP': {'iata': 'DEL', 'city': 'Delhi', 'name': 'Indira Gandhi Intl', 'routes': ['DEL-BOM', 'DEL-BLR', 'DEL-CCU', 'DEL-HYD', 'DEL-PAT', 'DEL-SXR', 'DEL-ATQ', 'DEL-LKO', 'DEL-GAU', 'DEL-COK']},
    'VABB': {'iata': 'BOM', 'city': 'Mumbai', 'name': 'Chhatrapati Shivaji Maharaj Intl', 'routes': ['BOM-DEL', 'BOM-BLR', 'BOM-GOI', 'BOM-MAA', 'BOM-AMD', 'BOM-COK', 'BOM-PAT']},
    'VOBL': {'iata': 'BLR', 'city': 'Bengaluru', 'name': 'Kempegowda Intl', 'routes': ['BLR-DEL', 'BLR-BOM', 'BLR-HYD', 'BLR-MAA', 'BLR-PAT', 'BLR-CCU']},
    'VECC': {'iata': 'CCU', 'city': 'Kolkata', 'name': 'Netaji Subhash Chandra Bose Intl', 'routes': ['CCU-DEL', 'CCU-GAU', 'CCU-BOM', 'DEL-CCU']},
    'VOMM': {'iata': 'MAA', 'city': 'Chennai', 'name': 'Chennai Intl', 'routes': ['MAA-DEL', 'MAA-BOM', 'MAA-BLR', 'DEL-MAA']},
    'VOHS': {'iata': 'HYD', 'city': 'Hyderabad', 'name': 'Rajiv Gandhi Intl', 'routes': ['HYD-DEL', 'HYD-BLR', 'DEL-HYD', 'BLR-HYD']},
    'VEPT': {'iata': 'PAT', 'city': 'Patna', 'name': 'Jay Prakash Narayan Airport', 'routes': ['DEL-PAT', 'PAT-DEL', 'BOM-PAT', 'BLR-PAT']},
    'VEBI': {'iata': 'BBI', 'city': 'Bhubaneswar', 'name': 'Biju Patnaik Intl', 'routes': ['DEL-BBI', 'BBI-DEL', 'CCU-BBI']},
    'VEGT': {'iata': 'GAU', 'city': 'Guwahati', 'name': 'Lokpriya Gopinath Bordoloi Intl', 'routes': ['DEL-GAU', 'GAU-DEL', 'CCU-GAU', 'GAU-CCU']},
    'VISR': {'iata': 'SXR', 'city': 'Srinagar', 'name': 'Sheikh ul-Alam Intl', 'routes': ['DEL-SXR', 'SXR-DEL']},
    'VIAR': {'iata': 'ATQ', 'city': 'Amritsar', 'name': 'Sri Guru Ram Dass Jee Intl', 'routes': ['DEL-ATQ', 'ATQ-DEL']},
    'VILK': {'iata': 'LKO', 'city': 'Lucknow', 'name': 'Chaudhary Charan Singh Intl', 'routes': ['DEL-LKO', 'LKO-DEL']},
    'VOGO': {'iata': 'GOI', 'city': 'Goa', 'name': 'Dabolim Airport', 'routes': ['BOM-GOI', 'GOI-BOM', 'DEL-GOI', 'BLR-GOI']},
    'VOCI': {'iata': 'COK', 'city': 'Kochi', 'name': 'Cochin Intl', 'routes': ['DEL-COK', 'COK-DEL', 'BOM-COK', 'COK-BOM']},
    'VAAH': {'iata': 'AMD', 'city': 'Ahmedabad', 'name': 'Sardar Vallabhbhai Patel Intl', 'routes': ['AMD-DEL', 'DEL-AMD', 'BOM-AMD', 'AMD-BOM']},
    'VAPO': {'iata': 'PNQ', 'city': 'Pune', 'name': 'Pune Airport', 'routes': ['DEL-PNQ', 'PNQ-DEL']}
}

WX_DESCRIPTIONS = {
    'TS': 'Thunderstorm',
    'TSRA': 'Thunderstorm with Rain',
    '-TSRA': 'Light Thunderstorm with Rain',
    '+TSRA': 'Heavy Thunderstorm with Severe Rain',
    'SQ': 'Squall / Sudden Severe Wind Gusts',
    'FG': 'Dense Fog (Low Visibility)',
    'FZFG': 'Freezing Fog (Severe De-icing Delay)',
    'BR': 'Mist (Moderate Visibility)',
    'HZ': 'Haze (Normal Operations)',
    'RA': 'Moderate Rain',
    '-RA': 'Light Rain',
    '+RA': 'Heavy Torrential Rain',
    'DZ': 'Drizzle',
    'FU': 'Smoke / Low Visibility',
    'VCTS': 'Thunderstorm in Vicinity',
    'NSW': 'No Significant Weather',
    'SKC': 'Sky Clear',
    'FEW': 'Few Clouds',
    'SCT': 'Scattered Clouds',
    'BKN': 'Broken Clouds',
    'OVC': 'Overcast'
}


class LiveCalamityTracker:
    def __init__(self):
        self.cached_weather = None
        self.cached_gdacs = None
        self.last_fetch_time = 0
        self.cache_ttl = 300  # 5 minutes cache
        self.ssl_ctx = ssl.create_default_context()
        self.ssl_ctx.check_hostname = False
        self.ssl_ctx.verify_mode = ssl.CERT_NONE

    def fetch_all(self, force_refresh=False):
        """Fetches both live METAR and GDACS disaster alerts."""
        now = time.time()
        if not force_refresh and self.cached_weather is not None and (now - self.last_fetch_time) < self.cache_ttl:
            return self._build_status_response()

        self._fetch_metar()
        self._fetch_gdacs()
        self.last_fetch_time = now
        return self._build_status_response()

    def _fetch_metar(self):
        icaos = ','.join(INDIAN_AIRPORT_STATIONS.keys())
        url = f"https://aviationweather.gov/api/data/metar?ids={icaos}&format=json"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        stations_data = {}

        # Default normal fallback for each station
        for icao, meta in INDIAN_AIRPORT_STATIONS.items():
            stations_data[meta['iata']] = {
                'icao': icao,
                'iata': meta['iata'],
                'city': meta['city'],
                'name': meta['name'],
                'temp_c': 28,
                'wind_kts': 6,
                'visibility_sm': 3.5,
                'raw_wx': 'Normal',
                'weather_desc': 'Clear / Normal Operations',
                'disruption_level': 'Normal',
                'capacity_impact_pct': 0.0,
                'is_live_metar': False,
                'timestamp': datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')
            }

        try:
            with urllib.request.urlopen(req, context=self.ssl_ctx, timeout=8) as resp:
                metar_list = json.loads(resp.read().decode())
                for m in metar_list:
                    icao = m.get('icaoId')
                    if icao not in INDIAN_AIRPORT_STATIONS:
                        continue
                    iata = INDIAN_AIRPORT_STATIONS[icao]['iata']
                    city = INDIAN_AIRPORT_STATIONS[icao]['city']
                    name = INDIAN_AIRPORT_STATIONS[icao]['name']

                    wspd_raw = m.get('wspd', 0)
                    try:
                        wspd = float(wspd_raw)
                    except (ValueError, TypeError):
                        wspd = 0.0

                    visib_raw = m.get('visib', 4.0)
                    try:
                        visib_str = str(visib_raw).replace('+', '').strip()
                        visib = float(visib_str)
                    except (ValueError, TypeError):
                        visib = 4.0

                    wx_str = m.get('wxString') or ''
                    temp = m.get('temp', 28)
                    receipt = m.get('receiptTime', '')

                    # Interpret weather
                    weather_desc = WX_DESCRIPTIONS.get(wx_str, wx_str if wx_str else 'Clear / Normal')

                    # Disruption assessment
                    disruption_level = 'Normal'
                    capacity_cut = 0.0

                    # Severe: CAT-III fog (< 0.5 sm), Heavy Thunderstorm (+TSRA / SQ), or Gale (> 30 kts)
                    if (visib is not None and visib < 0.5) or ('+TSRA' in wx_str) or ('SQ' in wx_str) or (wspd and wspd > 30):
                        disruption_level = 'Severe'
                        capacity_cut = 40.0
                    # Moderate: Light/Mod Thunderstorm (TSRA, -TSRA), Heavy Rain (+RA), Reduced vis (< 1.5 sm)
                    elif ('TSRA' in wx_str) or ('TS' in wx_str) or ('+RA' in wx_str) or (visib is not None and visib < 1.5) or (wspd and wspd > 20):
                        disruption_level = 'Moderate'
                        capacity_cut = 20.0
                    # Advisory: Low haze or rain
                    elif ('RA' in wx_str) or (visib is not None and visib < 2.5):
                        disruption_level = 'Advisory'
                        capacity_cut = 8.0

                    stations_data[iata] = {
                        'icao': icao,
                        'iata': iata,
                        'city': city,
                        'name': name,
                        'temp_c': temp,
                        'wind_kts': wspd,
                        'visibility_sm': visib,
                        'raw_wx': wx_str or 'Nil',
                        'weather_desc': weather_desc,
                        'disruption_level': disruption_level,
                        'capacity_impact_pct': capacity_cut,
                        'is_live_metar': True,
                        'timestamp': receipt or datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')
                    }
        except Exception as e:
            print(f"[Live Calamity Tracker] Notice fetching METAR: {e}")

        self.cached_weather = stations_data

    def _fetch_gdacs(self):
        url = "https://www.gdacs.org/xml/rss.xml"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        india_alerts = []
        try:
            with urllib.request.urlopen(req, context=self.ssl_ctx, timeout=8) as resp:
                root = ET.fromstring(resp.read())
                for item in root.findall('.//item'):
                    title = item.find('title').text if item.find('title') is not None else ''
                    desc = item.find('description').text if item.find('description') is not None else ''
                    pubDate = item.find('pubDate').text if item.find('pubDate') is not None else ''
                    link = item.find('link').text if item.find('link') is not None else ''
                    text_corpus = (title + " " + desc).lower()
                    if any(k in text_corpus for k in ['india', 'bay of bengal', 'arabian sea', 'delhi', 'mumbai', 'chennai', 'kolkata', 'assam', 'odisha', 'gujarat', 'kerala']):
                        alert_level = 'Red' if 'red' in text_corpus else ('Orange' if 'orange' in text_corpus else 'Green')
                        event_type = 'Cyclone' if 'cyclone' in text_corpus or 'tropical' in text_corpus else ('Flood' if 'flood' in text_corpus else ('Earthquake' if 'earthquake' in text_corpus else 'Disaster Alert'))
                        india_alerts.append({
                            'title': title,
                            'description': desc[:180] + '...' if len(desc) > 180 else desc,
                            'alert_level': alert_level,
                            'event_type': event_type,
                            'pub_date': pubDate,
                            'link': link
                        })
        except Exception as e:
            print(f"[Live Calamity Tracker] Notice fetching GDACS: {e}")

        self.cached_gdacs = india_alerts

    def _build_status_response(self):
        weather = self.cached_weather or {}
        gdacs = self.cached_gdacs or []

        # Find any stations with Severe or Moderate disruptions
        disrupted_airports = [s for s in weather.values() if s['disruption_level'] in ['Severe', 'Moderate']]
        has_severe = any(s['disruption_level'] == 'Severe' for s in weather.values())
        has_disruption = len(disrupted_airports) > 0 or len([g for g in gdacs if g['alert_level'] in ['Red', 'Orange']]) > 0

        # Build active calamity profile if disrupted, else normal profile
        active_calamity_profile = None
        if has_disruption:
            affected_iatas = [s['iata'] for s in disrupted_airports]
            affected_routes = []
            max_cut = 0.0
            primary_names = []

            for s in disrupted_airports:
                iata = s['iata']
                for icao, meta in INDIAN_AIRPORT_STATIONS.items():
                    if meta['iata'] == iata:
                        affected_routes.extend(meta['routes'])
                if s['capacity_impact_pct'] > max_cut:
                    max_cut = s['capacity_impact_pct']
                primary_names.append(f"{s['city']} ({s['weather_desc']})")

            # GDACS severe storms
            for g in gdacs:
                if g['alert_level'] in ['Red', 'Orange']:
                    primary_names.append(g['title'])
                    if max_cut < 35.0:
                        max_cut = 35.0

            active_calamity_profile = {
                'id': 'real_live_disruption',
                'name': f"Live Weather Alert: {', '.join(primary_names[:2])}",
                'name_hi': f"सक्रिय मौसम चेतावनी: {', '.join(primary_names[:2])}",
                'is_live': True,
                'capacity_cut_pct': max_cut if max_cut > 0 else 15.0,
                'fare_surge_multiplier': 1.0 + (max_cut / 50.0),
                'affected_airports': affected_iatas,
                'affected_routes': list(set(affected_routes)),
                'description': f"Real-time sensor alert detected across {len(affected_iatas)} airport(s). Flight departures experiencing convective or weather ground delays."
            }

        return {
            'timestamp': datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC'),
            'airspace_status': 'Severe Weather Disruption' if has_severe else ('Weather Advisory Active' if len(disrupted_airports) > 0 else 'Normal Airspace Operations'),
            'airspace_status_hi': 'गंभीर मौसम व्यवधान' if has_severe else ('मौसम परामर्श सक्रिय' if len(disrupted_airports) > 0 else 'सामान्य हवाई क्षेत्र संचालन'),
            'has_active_disruption': has_disruption,
            'active_calamity_profile': active_calamity_profile,
            'disrupted_count': len(disrupted_airports),
            'disrupted_airports': disrupted_airports,
            'gdacs_alerts': gdacs,
            'all_stations': list(weather.values())
        }

    def get_airport_severity_score(self, iata: str):
        """
        Derives a numeric weather severity score (0.0 to 1.0) for a destination airport.
        Reuses the existing live METAR fetch. Returns None if the airport isn't covered
        or if the live METAR fetch fails.
        """
        if not iata:
            return None
        iata_clean = str(iata).strip().upper()
        if not self.cached_weather:
            try:
                self.fetch_all()
            except Exception:
                return None

        st = (self.cached_weather or {}).get(iata_clean)
        if not st or not st.get('is_live_metar'):
            return None

        visib = st.get('visibility_sm')
        wspd = st.get('wind_kts')
        wx_str = st.get('raw_wx', '')

        # Penalty components
        vis_penalty = 0.0
        if visib is not None:
            if visib < 0.5:
                vis_penalty = 0.5
            elif visib < 3.0:
                vis_penalty = 0.5 * (1.0 - (visib - 0.5) / 2.5)

        wind_penalty = 0.0
        if wspd is not None:
            if wspd > 30:
                wind_penalty = 0.3
            elif wspd > 10:
                wind_penalty = 0.3 * ((wspd - 10) / 20.0)

        wx_penalty = 0.0
        if any(k in wx_str for k in ['+TSRA', 'SQ', 'FZFG']):
            wx_penalty = 0.2
        elif any(k in wx_str for k in ['TSRA', 'TS', '+RA', 'FG']):
            wx_penalty = 0.1
        elif any(k in wx_str for k in ['RA', 'DZ', 'BR']):
            wx_penalty = 0.05

        severity = round(min(1.0, max(0.0, vis_penalty + wind_penalty + wx_penalty)), 3)
        return float(severity)

# Global Singleton
live_calamity_tracker = LiveCalamityTracker()
