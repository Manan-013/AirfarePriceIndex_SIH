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

## Architecture Overview

AeroDex is an academic research prototype engineered to address the 30–45 day time-lag in India's official Consumer Price Index (CPI) publication by providing a high-frequency, real-time national airfare price index.

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ 1. ETHICAL MULTI-SOURCE INGESTION CORE                                                 │
│    • Concurrent Playwright extraction: EaseMyTrip (Indian OTA) + Google Flights        │
│    • RobotGuard: Pre-flight robots.txt validation & per-domain rate limiting           │
│    • Low-RAM Chromium container flags & asset abort filters (<120MB RAM)               │
└────────────────────────────────────────┬───────────────────────────────────────────────┘
                                         ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ 2. MICRODATA WAREHOUSE & DGCA FORM-A CENSUS WEIGHTING                                  │
│    • SQLite microdata warehouse storing timestamped quotes with full provenance        │
│    • DGCA Form-A traffic census calibration (786 routes, 136M flyers)                  │
│    • Airline market share weighting: IndiGo (62%), Air India (15%), Akasa, SpiceJet    │
└────────────────────────────────────────┬───────────────────────────────────────────────┘
                                         ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ 3. ECONOMETRIC & NOWCASTING CORE                                                       │
│    • Official Laspeyres & Paasche sector indices and National APIx                     │
│    • Live METAR aviation weather telemetry for 16 Indian airport control towers        │
│    • UN GDACS disaster radar integration for active cyclones and flood groundings      │
│    • In-memory RandomForestRegressor (<2ms latency) for festival & calamity shocks     │
└────────────────────────────────────────┬───────────────────────────────────────────────┘
                                         ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ 4. USER INTERFACE & AI SITUATION ROOM                                                  │
│    • High-contrast, minimal dashboard with tactile feedback and zero distracting glow  │
│    • 100% Honest provenance badging (🟢 Live Web Scraped vs ⚠️ Simulated Fallback)     │
│    • Gemini 3.6 Flash Situation Room (English & हिन्दी) + deterministic offline mode   │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## Getting Started

```bash
# Install requirements
pip install -r requirements.txt
python -m playwright install chromium

# Launch web server & interactive dashboard
cd live_fetcher
python server.py

# Or launch decoupled background ingestion worker
python worker_scraper.py --routes DEL-BOM,DEL-BLR --once
```

Navigate to `http://localhost:8000` to interact with the dashboard.
