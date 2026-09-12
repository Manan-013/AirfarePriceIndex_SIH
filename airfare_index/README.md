# MoSPI Real-Time Airfare Price Index (APIx)
### Smart India Hackathon 2026 • Problem Statement: SIH26056
> **"Development of a Real-time Airfare Price Index for India through Automated Web Scraping of Airline and Online Travel Aggregator Portals for Augmentation of the Consumer Price Index (CPI)"**

[![Python Version](https://img.shields.io/badge/Python-3.12%2B-blue.svg)](https://www.python.org/)
[![Playwright](https://img.shields.io/badge/Playwright-Headless%20Workers-orange.svg)](https://playwright.dev/)
[![Scikit-Learn](https://img.shields.io/badge/ML-Scikit--Learn%20RandomForest-green.svg)](https://scikit-learn.org/)
[![Gemini](https://img.shields.io/badge/LLM-Gemini%203.7%20Flash-purple.svg)](https://ai.google.dev/)
[![License](https://img.shields.io/badge/License-MIT-lightgrey.svg)](LICENSE)
[![Status](https://img.shields.io/badge/Status-Production%20Ready%20%7C%20Live-brightgreen.svg)](#)

---

## Executive Summary

In India, the **Ministry of Statistics and Programme Implementation (MoSPI)** currently publishes the national Consumer Price Index (CPI) with a 30 to 45-day lag due to manual monthly price collection surveys. In highly dynamic sectors such as civil aviation, airline algorithms adjust ticket tariffs multiple times per day. By the time central bank monetary authorities (RBI MPC) review inflation data, ticket price shocks have already passed through the economy.

**The Solution:** This platform delivers India's first end-to-end, automated **National Airfare Price Index (APIx)**. Operating on an autonomous 12-second scrape cadence, it extracts live domestic airfares across 25 key national corridors and 16 airport hubs, deconstructs mandatory taxes and fuel surcharges, weights tariffs by official DGCA passenger census figures (136 Million annual passengers), and computes real-time Laspeyres price indices. 

The system features an in-memory **Random Forest Machine Learning Nowcaster**, real-time **METAR Aviation Weather Radar** for 16 Indian airport towers, a **33-Festival Google Calendar Explorer**, and an **Autonomous AI Airfare Situation Room** powered by **Gemini 3.7 Flash** (with instant deterministic offline fallback) supporting English and official **शुद्ध हिन्दी**.

---

## System Architecture

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ 1. DATA INGESTION ENGINE (Every 12s Cadence)                                           │
│    • Headless Playwright workers query live airline portals (Google Flights / OTAs)    │
│    • Ingests 25 key corridors & 16 airport hubs across advance windows (T+1 to T+45)   │
│    • Deconstructs base fare vs UDF, PSF, ASF, CGST/SGST, and carrier fuel surcharges   │
└────────────────────────────────────────┬───────────────────────────────────────────────┘
                                         ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ 2. MICRODATA WAREHOUSE & DGCA CENSUS WEIGHTING                                         │
│    • SQLite microdata warehouse storing 19,400+ quotes with full timestamp audit logs  │
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

### 1. Modern Sticky Left Sidebar Navigation
* **Executive Dashboard Quick Card:** Features live rolling National Index metrics and 1-click return to the top overview.
* **Navigation Modules:**
  * **Main Dashboard:** High-level macroeconomic overview, headline KPIs, and AI briefing.
  * **Live Fare Verifier:** Real-time route search, deconstructed taxes (UDF, PSF, GST), and price dispersion curves.
  * **Forward Nowcast:** Machine learning simulator with live METAR weather radar and full-year festival explorer.
  * **Pricing Heatmaps:** Advance booking elasticity matrix ($T+1$ to $T+45$) and state-level inflation heatmaps.
  * **Macro Alignment:** ATF aviation turbine fuel correlation and 30-day historical MoSPI time-series.
  * **DGCA Route Basket:** Census passenger volumes, route weights, and airline market shares.
* **Engine Telemetry Card:** Live daemon status (`Port 8000 Active Feed`), scrape cadence, monitored hubs, and quick modal triggers.

### 2. Forward Nowcast & Calamity Simulator
* **Real-Time Airspace Weather Radar:** Ingests official Aviation Weather METAR sensor telemetry for 16 Indian airport control towers (DEL, BOM, BLR, CCU, MAA, HYD, PAT, BBI, GAU, SXR, ATQ, LKO, GOI, COK, AMD, PNQ) and UN GDACS disaster feeds.
* **33-Festival Google Calendar Explorer:** Covers all gazetted national holidays, regional harvest peaks, and cultural festivals spanning January to December.
* **Instant ML Inference:** In-memory `RandomForestRegressor` predicts corridor surge tariffs, projected APIx index, and CPI basis point impacts in **`< 2ms`**.

### 3. AI Airfare Situation Room (Gemini 3.7 Flash)
* **Zero-Latency First Paint:** Briefings are pre-computed in RAM during background scrape cycles, serving initial loads in **`< 3ms`**.
* **4 Executive Pillars:** Explains *The Big Picture*, *Surging Corridors*, *Lead-Time Reality*, and *Airline Floor & Scale* in plain language without jargon.
* **Multilingual Compliance:** Instant 1-click toggle to official **शुद्ध हिन्दी** fulfilling Digital India & Bhashini national language guidelines.
* **Grounded Conversational Q&A:** Answers user queries (e.g. *"Why is Goa surging today?"* or *"आज सबसे सस्ती उड़ानें कौन सी हैं?"*) grounded strictly in live SQLite microdata.
* **Fail-Safe Offline Mode:** If internet drops or API keys are missing, the platform automatically runs on an audited, deterministic econometric engine.

### 4. Official NSO / RBI Data Exporters
* **Daily Sector Bulletin (`.csv`):** Standard RFC 4180 CSV containing carrier-weighted fares, Laspeyres indices, and price changes vs Base 2024.
* **Monthly Time-Series (`.csv`):** 20-month historical backtest comparing APIx with official MoSPI Transport CPI.
* **Microdata Audit Quotes (`.csv`):** Complete scrape audit log with flight numbers, departure times, taxes, and raw prices.

---

## Tech Stack

| Component | Technology | Purpose |
| :--- | :--- | :--- |
| **Backend & Server** | Python 3.12, `http.server` | Lightweight, zero-dependency async multithreaded daemon |
| **Scraping Engine** | Playwright (Chromium Headless) | Resilient extraction with dynamic waits and round-robin corridor rotation |
| **Database** | SQLite 3 with B-Tree Indexes | Microdata storage with connection pooling and atomic transactions |
| **Machine Learning** | scikit-learn, joblib, NumPy | In-memory Random Forest regressor with one-hot encoded route features |
| **AI / LLM** | Google Gemini 3.7 Flash SDK | Executive situation briefings & conversational econometric Q&A |
| **Telemetry & Radar** | NOAA Aviation Weather (METAR), UN GDACS | Live airport surface weather conditions & natural calamity detection |
| **Frontend Layout** | HTML5, Tailwind CSS, Canvas | Sticky sidebar, glassmorphic cards, rolling odometers, zero emojis |
| **Data Export** | RFC 4180 CSV Engine | Official statistical bulletins for NSO & RBI monetary policy analysts |

---

## REST API Specification

### Core Telemetry & Search
* `GET /api/v1/live/pulse` — Returns real-time scrape telemetry, national APIx index, CPI impact bps, and rolling quote counters.
* `POST /api/v1/search` — Triggers Playwright live search for origin, destination, and departure date with tax breakdown.

### AI Situation Room
* `GET /api/v1/ai/summary` — Returns pre-computed executive briefing in English and शुद्ध हिन्दी (`< 3ms`).
* `POST /api/v1/ai/query` — Submits natural language question to the econometric Q&A engine grounded in SQLite quotes.
* `GET /api/v1/ai/config` — Checks Gemini API key configuration and active model status.
* `POST /api/v1/ai/config` — Sets and validates Gemini API key securely from frontend UI.

### Forward ML Nowcast & Radar
* `POST /api/v1/forecast/predict` — Runs vectorized ML regression for target date and disruption scenario.
* `GET /api/v1/forecast/calendar` — Returns the 33-festival Indian holiday calendar with optional month/category filters.
* `GET /api/v1/forecast/live_calamities` — Fetches live METAR surface observations for 16 Indian airport towers.

### Heatmaps & Econometrics
* `GET /api/v1/heatmap/sectors` — Returns $T+1$ to $T+45$ advance booking elasticity matrix.
* `GET /api/v1/heatmap/states` — Returns state-wise airfare inflation pressure aggregations.
* `GET /api/v1/macro/timeline` — Returns 30-day historical time-series comparing APIx, ATF fuel prices, and CPI.
* `GET /api/v1/routes/weights` — Returns official DGCA Form-A 786-route census weights.

### NSO Data Exports
* `GET /api/v1/export/daily` — Downloads MoSPI Daily Sector Airfare Bulletin as standard RFC 4180 CSV.
* `GET /api/v1/export/monthly` — Downloads MoSPI 20-Month Historical Series as CSV.
* `GET /api/v1/export/quotes` — Downloads Scraped Flight Quotes Microdata Audit Log as CSV.

---

## Quickstart & Installation Guide

### Prerequisites
* **Python 3.12+** installed on Windows, Linux, or macOS.
* **Git** installed.

### 1. Clone the Repository
```bash
git clone https://github.com/Manan-013/MoSPI-Airfare-Price-Index.git
cd MoSPI-Airfare-Price-Index
```

### 2. Set Up Virtual Environment & Install Dependencies
```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows (PowerShell):
.\venv\Scripts\Activate.ps1
# On Linux/macOS:
source venv/bin/activate

# Install required packages
pip install -r requirements.txt

# Install Playwright Chromium browser binaries
playwright install chromium
```

### 3. Configure Environment Variables (Optional)
Copy the template configuration file:
```bash
cp .env.example .env
```
*(Optional) Add your Google Gemini API key to `.env` for AI Situation Room briefings:*
```env
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-3.7-flash
PORT=8000
```
> **Note:** If `GEMINI_API_KEY` is omitted, the platform automatically runs on the **Audited Local Econometric Engine** with 100% offline functionality.

### 4. Launch the Platform
Navigate to `live_fetcher/` and start the server daemon:
```bash
cd live_fetcher
python server.py
```
Open your browser and navigate to:
```
http://localhost:8000
```

---

## Security & Data Privacy Policy

* **Zero Hardcoded Secrets:** All private credentials and API keys are strictly excluded via `.gitignore` and loaded solely via environment variables or encrypted local storage.
* **Masked API Endpoints:** The `/api/v1/ai/config` endpoint masks sensitive credentials (`AIzaSy...4xQ9`), ensuring keys are never exposed over network inspection.
* **Responsible Scraping:** Scrapers utilize respectful 12-second inter-flight intervals, randomized user agents, and exponential backoff compliant with portal rate limits.
* **Database Isolation:** SQLite databases (`*.db`, `*.sqlite`) are git-ignored to prevent inadvertent leakage of operational telemetry.

---

## License & Acknowledgements

* **License:** MIT Open Source License.
* **Competition:** Developed for **Smart India Hackathon 2026** under Problem Statement **SIH26056**.
* **Data Sources:** DGCA Annual Air Transport Form-A Census, MoSPI National Statistical Office (NSO), NOAA Aviation Weather Center (METAR), UN GDACS.
