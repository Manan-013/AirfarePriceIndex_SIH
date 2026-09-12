# MoSPI Real-Time Airfare Price Index (APIx)
### Smart India Hackathon 2026 • Problem Statement: SIH26056
> **"Development of a Real-time Airfare Price Index for India through Automated Web Scraping of Airline and Online Travel Aggregator Portals for Augmentation of the Consumer Price Index (CPI)"**

[![Python Version](https://img.shields.io/badge/Python-3.12%2B-blue.svg)](https://www.python.org/)
[![Playwright](https://img.shields.io/badge/Playwright-Headless%20Workers-orange.svg)](https://playwright.dev/)
[![Scikit-Learn](https://img.shields.io/badge/ML-RandomForestNowcaster-green.svg)](https://scikit-learn.org/)
[![Gemini](https://img.shields.io/badge/LLM-Gemini%203.7%20Flash-purple.svg)](https://ai.google.dev/)
[![License](https://img.shields.io/badge/License-MIT-lightgrey.svg)](LICENSE)
[![Status](https://img.shields.io/badge/Status-Production%20Ready%20%7C%20SIH%202026-brightgreen.svg)](#)

---

## Executive Summary

In India, the **Ministry of Statistics and Programme Implementation (MoSPI)** publishes the national Consumer Price Index (CPI) with a 30 to 45-day lag due to conventional manual price survey cycles. In the civil aviation sector, airline pricing algorithms adjust tariffs multiple times per day. By the time central bank monetary authorities (RBI MPC) review inflation data, ticket price shocks have already passed through the macroeconomy.

**The Solution:** This repository delivers India's first end-to-end, automated **National Airfare Price Index (APIx)**. Operating on an autonomous scrape cadence, it extracts live domestic airfares across 25 key national corridors and 16 airport hubs, deconstructs mandatory taxes and fuel surcharges, weights tariffs by official DGCA passenger census figures (136 Million annual passengers), and computes real-time Laspeyres price indices.

The platform includes an in-memory **Random Forest Machine Learning Nowcaster**, real-time **METAR Aviation Weather Radar** for 16 Indian airport control towers, a **33-Festival Google Calendar Explorer**, and an **Autonomous AI Airfare Situation Room** powered by **Gemini 3.7 Flash** (with instant deterministic offline fallback) supporting English and official **शुद्ध हिन्दी**.

---

## Repository Structure

```
SIH/
├── airfare_index/                       # Core Production Engine & Dashboard
│   ├── live_fetcher/                    # Real-time data pipeline & web server
│   │   ├── static/index.html            # Sticky sidebar UI dashboard (zero emojis)
│   │   ├── server.py                    # FastAPI/Uvicorn REST API backend
│   │   ├── scraper.py                   # Playwright headless aggregator scraper
│   │   ├── index_engine.py              # Laspeyres/Paasche index calculator
│   │   ├── forecasting_engine.py        # ML Nowcasting engine & METAR telemetry
│   │   ├── live_calamity_tracker.py     # UN GDACS & weather calamity shock monitor
│   │   ├── ai_engine.py                 # Gemini 3.7 Flash Situation Room & offline fallback
│   │   ├── database.py                  # SQLite schema manager
│   │   ├── run_server.bat               # 1-Click launcher
│   │   └── .env.example                 # Environment configuration template
│   ├── index_engine.py                  # Offline econometric index validator
│   ├── airfare_predictor.joblib         # Pre-trained Random Forest model
│   ├── requirements.txt                 # Python dependencies
│   ├── atf_fuel_prices.csv              # Aviation Turbine Fuel (ATF) historical benchmarks
│   ├── carrier_market_shares.csv        # DGCA official carrier market shares
│   ├── dgca_citypair_weights.csv        # DGCA census route weights (786 routes)
│   └── official_mospi_cpi_airfare.csv   # Historical MoSPI CPI backtest series
├── data/                                # Comprehensive Census & Traffic Datasets
│   ├── CITY PAIR WISE... (.xlsx & .csv) # City-pair domestic traffic census
│   ├── cpi_2005 (.xlsx & .csv)          # Historical base CPI data
│   ├── atf_fuel_prices.csv              # ATF spot benchmarks
│   ├── carrier_market_shares.csv        # Airline market distribution
│   ├── dgca_citypair_weights.csv        # Route census weights
│   ├── official_mospi_cpi_airfare.csv   # MoSPI transport series
│   ├── sih2026_problem_statements.csv   # SIH 2026 Problem Statements dataset
│   └── data/                            # 43+ Monthly DGCA airline matrices & city-pairs (CSV + XLSX)
├── scratch/                             # Test harnesses and scraper diagnostic scripts
├── parse_all.py                         # SIH PS HTML table parser
├── scrape.py                            # Portal scraper prototype
├── sih2026_problem_statements.pdf       # SIH official problem statements catalog
├── sih2026_problem_statements.csv       # Problem statements in CSV format
├── sih2026_problem_statements.json      # Problem statements in JSON format
├── sih2026_problem_statements.md        # Problem statements in Markdown format
├── innovative_top_picks.md              # Innovation review of hackathon problem statements
└── README.md                            # Comprehensive system documentation
```

---

## System Architecture

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ 1. DATA INGESTION ENGINE                                                               │
│    • Headless Playwright workers query live airline portals (Google Flights / OTAs)    │
│    • Ingests 25 key corridors & 16 airport hubs across advance windows (T+1 to T+45)   │
│    • Deconstructs base fare vs UDF, PSF, ASF, CGST/SGST, and carrier fuel surcharges   │
└────────────────────────────────────────┬───────────────────────────────────────────────┘
                                         ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ 2. MICRODATA WAREHOUSE & DGCA CENSUS WEIGHTING                                         │
│    • SQLite microdata warehouse storing quotes with timestamp audit logs               │
│    • Calibrated against DGCA Form-A census covering 786 routes and 136M flyers         │
│    • Weights airline quotes by DGCA carrier shares (IndiGo 62%, Air India 15%, etc.)   │
└────────────────────────────────────────┬───────────────────────────────────────────────┘
                                         ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ 3. ECONOMETRIC & NOWCASTING CORE                                                       │
│    • Computes official Laspeyres & Paasche sector indices and National APIx            │
│    • Live METAR aviation weather telemetry for 16 Indian airport control towers        │
│    • UN GDACS disaster radar integration for active cyclones and flood groundings      │
│    • In-memory RandomForestRegressor (<2ms latency) for festival & calamity shocks     │
└────────────────────────────────────────┬───────────────────────────────────────────────┘
                                         ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ 4. USER INTERFACE & AI SITUATION ROOM                                                  │
│    • Modern sticky Left Sidebar navigation (Executive Dashboard, 5 Modules, Telemetry) │
│    • Autonomous AI Situation Room (Gemini 3.7 Flash + Audited Deterministic Fallback)  │
│    • Grounded Multilingual Q&A Engine (English & शुद्ध हिन्दी)                         │
│    • RFC 4180 CSV export feeds formatted for MoSPI NSO & RBI economists                │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## Econometric Methodology & Mathematical Formulation

### 1. National Airfare Price Index (APIx)
The platform strictly implements the **Laspeyres Price Index** formula approved by the International Monetary Fund (IMF) and MoSPI:

$$\text{APIx}_t = \frac{\sum_{i=1}^{N} (P_{t,i} \times Q_{0,i})}{\sum_{i=1}^{N} (P_{0,i} \times Q_{0,i})} \times 100$$

Where:
* $P_{t,i}$ is the carrier-weighted domestic fare on route $i$ at time $t$.
* $P_{0,i}$ is the representative baseline economy fare on route $i$ in **Base Year 2024**.
* $Q_{0,i}$ is the official base passenger traffic volume on route $i$ from the DGCA Annual Form-A Census.

### 2. Carrier-Weighted Fare Formulation
To prevent skew from boutique or low-frequency carriers, route tariffs are weighted by actual airline passenger market shares:

$$P_{t,i} = \sum_{c} \left( P_{t,i,c} \times w_c \right)$$

* $w_c$: IndiGo ($62\%$), Air India ($15\%$), SpiceJet ($5\%$), Akasa Air ($5\%$), AIX Connect ($13\%$).

### 3. Headline CPI Inflation Impact (Basis Points)
Air transportation is categorized under **COICOP Code 07.3.3** (*Passenger transport by air*) with an official weight of **$0.077\%$** in the All-India CPI combined basket:

$$\Delta \text{CPI (bps)} = \left( \frac{\text{APIx}_t - 100}{100} \right) \times W_{\text{CPI}} \times 10,000$$

Where:
* $W_{\text{CPI}} = 0.00077$ ($0.077\%$).
* $1 \text{ basis point (bps)} = 0.01\%$.

---

## Core Features & Modules

### 1. Sticky Left Sidebar Navigation
* **Executive Dashboard Quick Card:** Live rolling National Index metrics and 1-click return to the top overview.
* **Main Dashboard:** High-level macroeconomic overview, headline KPIs, and AI briefing.
* **Live Fare Verifier:** Real-time route search, deconstructed taxes (UDF, PSF, GST), and price dispersion curves.
* **Forward Nowcast:** Machine learning simulator with live METAR weather radar and full-year festival explorer.
* **Pricing Heatmaps:** Advance booking elasticity matrix ($T+1$ to $T+45$) and state-level inflation heatmaps.
* **Macro Alignment:** ATF aviation turbine fuel correlation and 30-day historical MoSPI time-series.
* **DGCA Route Basket:** Census passenger volumes, route weights, and airline market shares.

### 2. Machine Learning Forward Nowcaster
* Features: Days to departure ($T+1$ to $T+45$), carrier market power, route distance, METAR wind/visibility, and festival proximity.
* Model: Random Forest Regressor trained on 19,400+ airline price observations.
* Latency: Sub-2ms inference with 95% confidence intervals.

### 3. Live Aviation Weather & Calamity Radar
* Direct live integration with NOAA Aviation Weather Center METAR feeds for 16 Indian airport stations (`VIDP`, `VABB`, `VOBL`, `VOMM`, `VECC`, `VOHS`, etc.).
* Automated extraction of wind speed, flight category (VFR/IFR/LIFR), ceiling, and visibility.
* Automated detection of airport groundings and weather disruptions feeding dynamic price shocks into the econometric model.

### 4. Autonomous AI Situation Room
* Powered by Google Gemini 3.7 Flash with real-time prompt grounding in live scraped microdata.
* Built-in deterministic offline fallback engine that runs without an internet connection or API key.
* Full bilingual support: Natural language explanations in English and शुद्ध हिन्दी.

---

## REST API Specification

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/index/current` | Returns live National APIx, base fare, CPI bps impact, and active route count. |
| `GET` | `/api/index/history?days=30` | Time-series of national index, base fares, and carrier indices. |
| `GET` | `/api/routes` | All 25 tracked corridors with weights, passenger volumes, and base fares. |
| `GET` | `/api/routes/{origin}/{destination}/latest` | Detailed quotes, airline breakdown, and tax deconstruction for a route. |
| `POST`| `/api/forecast` | ML inference endpoint predicting future tariffs given route and advance booking date. |
| `GET` | `/api/weather/metar` | Real-time decoded METAR reports across 16 Indian airport stations. |
| `POST`| `/api/ai/query` | Natural language situation room query with automated microdata grounding. |
| `GET` | `/api/export/bulletin` | Official MoSPI RFC 4180 CSV daily index bulletin download. |
| `GET` | `/api/export/monthly-series` | MoSPI 20-month backtest time-series CSV export. |
| `GET` | `/api/export/microdata` | Complete raw scraped quote audit log CSV export. |

---

## Quick Start & Installation

### 1. Prerequisites
* Python 3.10+ (Recommended: Python 3.12)
* Google Chrome or Chromium (for Playwright scraping)

### 2. Setup Environment
```bash
git clone https://github.com/Manan-013/AirfarePriceIndex_SIH.git
cd AirfarePriceIndex_SIH

# Install dependencies
pip install -r airfare_index/requirements.txt

# Install Playwright browser binaries
playwright install chromium
```

### 3. Configuration (Optional)
To enable Gemini 3.7 Flash for the AI Situation Room:
```bash
cp airfare_index/.env.example airfare_index/live_fetcher/.env
# Add your GEMINI_API_KEY in airfare_index/live_fetcher/.env
```
*(If omitted, the platform runs in 100% audited offline deterministic mode with zero loss of econometric functionality).*

### 4. Launch Application
```bash
cd airfare_index/live_fetcher
python server.py
```
Or double-click `airfare_index/live_fetcher/run_server.bat` on Windows.

Open your browser and navigate to:
```
http://localhost:8000
```

---

## Security & Data Integrity Safeguards

1. **Zero Secret Leakage:** Production `.gitignore` strictly isolates all `.env` files, API keys, and local tokens.
2. **Deterministic Fallback:** Never exposes private data or credentials in client bundles.
3. **Database Isolation:** Active SQLite database files are gitignored and generated locally on launch.
4. **Data Verification:** Official DGCA and MoSPI statistics are provided in both RFC 4180 CSV and Microsoft Excel formats in the `data/` directory for full replication.

---

## Team & Credits
* **Project:** Smart India Hackathon (SIH 2026)
* **Problem Statement:** PS SIH26056 (MoSPI)
* **Lead Developer:** Manan Ramani
