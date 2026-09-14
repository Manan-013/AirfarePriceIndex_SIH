# AeroDex: Real-Time Airfare Price Index (APIx)
### Smart India Hackathon 2026 • Problem Statement: SIH26056
> **"Development of a Real-time Airfare Price Index for India through Automated Web Scraping of Airline and Online Travel Aggregator Portals for Augmentation of the Consumer Price Index (CPI)"**

[![Python Version](https://img.shields.io/badge/Python-3.12%2B-blue.svg)](https://www.python.org/)
[![Playwright](https://img.shields.io/badge/Playwright-Multi--Source%20Headless-orange.svg)](https://playwright.dev/)
[![Compliance](https://img.shields.io/badge/Robots.txt-Ethical%20Compliance-brightgreen.svg)](#ethical-scraping--compliance)
[![Scikit-Learn](https://img.shields.io/badge/ML-RandomForestNowcaster-green.svg)](https://scikit-learn.org/)
[![Gemini](https://img.shields.io/badge/LLM-Gemini%203.6%20Flash-purple.svg)](https://ai.google.dev/)
[![Status](https://img.shields.io/badge/Status-Working%20Prototype%20%7C%20SIH%202026-blue.svg)](#)

---

## Executive Summary

In India, the **Ministry of Statistics and Programme Implementation (MoSPI)** publishes the national Consumer Price Index (CPI) with a 30 to 45-day lag due to conventional manual field survey cycles. In the civil aviation sector, airline pricing algorithms adjust tariffs continuously. By the time monetary authorities (RBI MPC) review monthly inflation prints, volatile ticket price fluctuations have already propagated through the economy.

**The Solution:** AeroDex is a working prototype delivering a real-time **National Airfare Price Index (APIx)** for India. Built directly for SIH 2026 Problem Statement SIH26056, the platform pairs ethical multi-source web extraction with official DGCA passenger census weights (136 Million annual flyers across 786 routes) to compute transparent Laspeyres and Paasche airfare price indices.

---

## Key Engineering Pillars

### 1. Ethical Multi-Source Web Scraping
- **Named Indian OTAs & Aggregators**: Live concurrent Playwright extraction across **EaseMyTrip** (premier Indian OTA named in PS) and **Google Flights**.
- **Robots.txt Verification**: Automated checking via `urllib.robotparser` (`RobotGuard`) before initiating requests to target domains.
- **Polite Crawl Delays & Backoff**: Enforces per-domain rate limiting with exponential backoff on HTTP 429/503 responses.
- **Live Compliance Audit API**: Real-time inspection of robots.txt status and crawl logs via `GET /api/v1/compliance/robots`.

### 2. Dual-Layer Resilient Architecture & Honest Provenance
- **Layer A (Live Extraction)**: Extracts live flight quotes (fares, flight numbers, aircraft type, departure/arrival schedules) across 25 high-traffic corridors and 16 airport hubs.
- **Layer B (Continuous Fallback)**: If a target portal is rate-limited or in offline environments, the system seamlessly transitions to a calibrated baseline derived from official DGCA Form-A traffic census data and empirical surge multipliers.
- **Honest Provenance Badges**: Every query and individual flight card clearly indicates its provenance:
  - `🟢 Live Web Scraped (EaseMyTrip & Google Flights)` when live data is extracted.
  - `⚠️ Simulated / Benchmark Estimate (Fallback)` with an informative alert banner when fallback estimates are active.

### 3. Cloud-Ready & Low-Memory Playwright Deployment
- Headless Chromium runs with resource-constrained cloud flags (`--no-sandbox`, `--disable-dev-shm-usage`, `--disable-gpu`).
- Request route interception aborts heavy assets (images, fonts, media) saving 70%+ bandwidth and keeping RAM usage <120MB.
- **Decoupled Ingestion Worker** (`worker_scraper.py`): Standalone background process that can run independently or on a cron schedule, insulating the FastAPI web server from browser load.

### 4. Econometric Rigor & Macroeconomic Alignment
- **DGCA Census Weighting**: Weights tariffs by actual airline market shares (IndiGo ~62%, Air India ~15%, Akasa ~5%, SpiceJet ~4%) and route passenger volumes.
- **Fare Deconstruction**: Breaks down total tariffs into Base Fare, Fuel Surcharge (YQ), Airport Fees (UDF/PSF), and GST (5%).
- **MoSPI CPI Integration**: Quantifies exact basis point impact on India's Headline Consumer Price Index (COICOP Sub-class 07.3.3, 0.077% basket weight).

### 5. AI Econometric Situation Room & Differentiating Features
- **Data Integrity Governance Engine** (`integrity_engine.py`): Calculates real-time composite data quality scores (0–100%, Grade A+) evaluating mathematical fare reconciliation ($Base + YQ + Fees + GST = Total$), Tukey 1.5× IQR outlier trimming, source diversity, and temporal freshness.
- **Historical Aviation Crisis Simulation Studio** (`shock_replay.py`): Calibrated stylized stress-testing simulator modeling historical supply shocks (May 2023 Go First Grounding, April 2019 Jet Airways Collapse, June 2022 ATF Fuel Spike) showing Laspeyres substitution bias vs Superlative Fisher index trajectories.
- **Autonomous Executive Briefings**: AI policy memos in English and formal Hindi (**शुद्ध हिन्दी**) powered by **Gemini 3.6 Flash** (`gemini-3.6-flash`) with deterministic offline fallback.

---

## Repository Structure

```
SIH/
├── airfare_index/                       # Core Production Engine & Dashboard
│   ├── live_fetcher/                    # Real-time data pipeline & web server
│   │   ├── static/index.html            # Interactive executive dashboard
│   │   ├── server.py                    # REST API backend & static file server
│   │   ├── scraper.py                   # Multi-source concurrent Playwright scraper
│   │   ├── robot_guard.py               # Ethical robots.txt checker & rate limiter
│   │   ├── proxy_rotator.py             # Multi-node rotating proxy & anti-bot manager
│   │   ├── integrity_engine.py          # Real-time econometric data integrity engine
│   │   ├── shock_replay.py              # Historical aviation shock replay simulator
│   │   ├── worker_scraper.py            # Decoupled background ingestion worker
│   │   ├── index_engine.py              # Laspeyres & Paasche index calculation engine
│   │   ├── forecasting_engine.py        # ML Nowcasting engine & METAR telemetry
│   │   ├── live_calamity_tracker.py     # UN GDACS & weather calamity shock monitor
│   │   ├── ai_engine.py                 # Gemini 3.6 Flash Situation Room & offline engine
│   │   ├── database.py                  # SQLite schema & microdata audit logger
│   │   ├── run_server.bat               # 1-Click launcher
│   │   └── .env.example                 # Environment configuration template
│   ├── index_engine.py                  # Offline econometric index validator
│   ├── airfare_predictor.joblib         # Pre-trained Random Forest model
│   ├── requirements.txt                 # Python dependencies
│   ├── atf_fuel_prices.csv              # Aviation Turbine Fuel (ATF) historical benchmarks
│   ├── carrier_market_shares.csv        # DGCA official carrier market shares
│   ├── dgca_citypair_weights.csv        # DGCA census route weights (786 routes)
│   └── official_mospi_cpi_airfare.csv   # Historical MoSPI CPI backtest series
├── data/                                # Official Census & Traffic Datasets
│   ├── atf_fuel_prices.csv              # ATF spot benchmarks
│   ├── carrier_market_shares.csv        # Airline market distribution
│   ├── dgca_citypair_weights.csv        # Route census weights
│   └── official_mospi_cpi_airfare.csv   # MoSPI transport series
├── scratch/                             # Test harnesses and verification scripts
├── DEMO_SCRIPT.md                       # 5-Minute Hackathon Presentation Script
└── README.md                            # Comprehensive system documentation
```

---

## Quick Start Guide

### 1. Prerequisites
- Python 3.10+ (Python 3.12 recommended)
- Chromium binary for Playwright

### 2. Installation
```bash
# Clone the repository
git clone https://github.com/Manan-013/AirfarePriceIndex_SIH.git
cd AirfarePriceIndex_SIH

# Install Python dependencies
pip install -r airfare_index/requirements.txt

# Install Playwright browser binaries
python -m playwright install chromium
```

### 3. Environment Configuration (Optional)
```bash
cp airfare_index/.env.example airfare_index/.env
# Add your GEMINI_API_KEY if you wish to use live Gemini 3.6 Flash briefings.
# If omitted, the system runs on the built-in deterministic local econometric engine.
```

### 4. Running the Application
```bash
# Option A: Run the unified server (Web Dashboard + In-Memory Scraper)
cd airfare_index/live_fetcher
python server.py

# Option B: Run the decoupled background worker (for scheduled cloud execution)
python worker_scraper.py --routes DEL-BOM,DEL-BLR,BOM-BLR --interval 300
```
Open **http://localhost:8000** in your browser.

---

## Ethical Scraping & Compliance

The platform implements ethical scraping safeguards:
1. **Robots.txt Pre-Request Verification & Enforcement Gate**: Every candidate scrape target URL is evaluated against RFC 9309 rules before initiating network requests. If an endpoint is disallowed, extraction is strictly aborted before launching browser automation, falling back safely to warehouse microdata.
   - *Active Verification*: Checks domain directives prior to dispatching traffic;
   - *Strict Abort*: Disallowed endpoints immediately halt Playwright/HTTP execution and log the restriction.
2. **Polite Crawl Cadence**: Default 3.0s delay between requests to the same domain.
3. **Adaptive Backoff**: Automatically escalates delay up to 8x upon encountering HTTP 429 (Too Many Requests) or 503 (Service Unavailable).
4. **Verifiable Audit Log**: Evaluators can verify compliance status at any time via:
   ```bash
   curl http://localhost:8000/api/v1/compliance/robots
   ```

---

## Automated Test Suite

AeroDex includes a comprehensive automated test suite covering Laspeyres index mathematics, carrier volume weighting, statutory tax decomposition (Base + Fuel YQ + Airport UDF + GST = Total), statistical outlier trimming (2.5x median rule), MakeMyTrip parsing, and live REST endpoints.

Run the test suite out-of-the-box:
```bash
python -m unittest discover tests -v
```
*Result: 31 unit & integration tests passing with 100% success.*

---

## Key REST API Endpoints

| Endpoint | Method | Description |
| :--- | :---: | :--- |
| `/api/v1/search` | `POST` | Live flight search & tariff deconstruction across OTAs |
| `/api/v1/integrity/score` | `GET` | Real-time Econometric Data Integrity Score (4D composite, SHA-256 seal) |
| `/api/v1/shocks/list` | `GET` | Historical aviation shock replay scenario catalog |
| `/api/v1/shocks/replay` | `GET` | Historical shock replay engine (Fisher vs Laspeyres, early detection) |
| `/api/v1/compliance/proxies` | `GET` | Client fingerprint & header rotation telemetry (direct egress mode) |
| `/api/v1/compliance/robots` | `GET` | Live robots.txt compliance status and audit log |
| `/api/v1/live/pulse` | `GET` | High-frequency live pulse of national airfare index |
| `/api/v1/index/national` | `GET` | Current National Airfare Price Index and CPI impact |
| `/api/v1/index/weekly` | `GET` | 12-week rolling temporal aggregation timeline JSON |
| `/api/v1/macro/timeline` | `GET` | 20-month comparison: MoSPI CPI vs ATF Fuel vs Scraper |
| `/api/v1/routes/weights` | `GET` | Top DGCA passenger volume weights across 786 routes |
| `/api/v1/db/quotes` | `GET` | Recent microdata quotes from SQLite audit warehouse |
| `/api/v1/export/daily` | `GET` | Export MoSPI Daily Sector Airfare Bulletin (CSV) |
| `/api/v1/export/weekly` | `GET` | Export MoSPI Weekly Aggregation Bulletin (CSV) |
| `/api/v1/export/quotes` | `GET` | Export full microdata quote audit warehouse (CSV) |
| `/api/v1/ai/summary` | `GET` | Gemini 3.6 Flash Situation Room briefing (English & Hindi) |

---

## Methodology & Documentation

- For the full econometric, mathematical, and regulatory specification, read [**METHODOLOGY.md**](METHODOLOGY.md).
- For a step-by-step 5-minute walkthrough designed for hackathon evaluators and jury panels, see [**DEMO_SCRIPT.md**](DEMO_SCRIPT.md).
