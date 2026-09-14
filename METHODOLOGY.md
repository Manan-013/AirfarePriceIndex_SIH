# Econometric & Statistical Methodology: National Airfare Price Index (APIx)
**Smart India Hackathon 2026 | Problem Statement: SIH26056**  
*Lead Author / Engineering Team: AeroDex (Manan Ramani & Team)*  
*Institutional Scope: Ministry of Statistics and Programme Implementation (MoSPI) & Directorate General of Civil Aviation (DGCA)*

---

## 1. Executive Abstract & Regulatory Mandate

The **National Airfare Price Index (APIx)** is a high-frequency, representative price index developed to measure the temporal and spatial price movements of scheduled domestic passenger air transport in India. 

Under the revised Consumer Price Index (CPI) framework aligned with COICOP 07.3.3 (*Passenger transport by air*), airfare volatility exerts a measurable impact on transportation subgroup inflation. In dynamic deregulated airline markets, traditional monthly survey sampling faces severe temporal latency (30–45 days) and fails to capture intraday algorithmic surge pricing, advance purchase elasticity ($T+1$ to $T+45$), or localized weather/festival shocks.

AeroDex resolves this structural gap by combining:
1. **Census-grade spatial weighting** from DGCA Form-A traffic returns (786 domestic routes; 136.0 million annual passenger origin-destination pairs).
2. **Carrier market share aggregation** reflecting DGCA monthly airline census.
3. **Multi-portal web scraping** across named Indian travel aggregators (MakeMyTrip, EaseMyTrip, Google Flights) with pre-request RFC 9309 `robots.txt` verification and active enforcement gating.
4. **Statutory fare decomposition** isolating pure base tariffs from aviation fuel surcharges (YQ), airport user fees (UDF/PSF), and statutory Goods and Services Tax (GST).
5. **Non-parametric statistical cleaning** preventing luxury class skew from contaminating headline inflation metrics.

---

## 2. Mathematical Formulation: Laspeyres Price Index

The APIx calculation engine implements the Laspeyres index methodology, consistent with the official compilation standards of the National Statistical Office (NSO) and the International Monetary Fund (IMF) Consumer Price Index Manual.

### 2.1 National Composite Index Formula

The aggregate price index at time $t$ relative to base period $0$ (Base Year $2024 = 100.0$) is defined as:

$$I_{APIx, t} = \frac{\sum_{r=1}^{R} P_{r,t} \cdot Q_{r,0}}{\sum_{r=1}^{R} P_{r,0} \cdot Q_{r,0}} \times 100 = \sum_{r=1}^{R} W_r \cdot \left(\frac{P_{r,t}}{P_{r,0}}\right) \times 100$$

Where:
- $R$: Number of active scheduled domestic city-pair sectors in the national representative basket ($R = 786$).
- $P_{r,t}$: Carrier-weighted representative economy tariff on route $r$ observed at time $t$.
- $P_{r,0}$: Baseline calibrated base fare on route $r$ for the base period ($2024 = 100.0$).
- $Q_{r,0}$: Annual passenger volume on route $r$ during the base period.
- $W_r$: DGCA Form-A expenditure/traffic weight of route $r$, such that:

$$W_r = \frac{Q_{r,0} \cdot P_{r,0}}{\sum_{k=1}^{R} Q_{k,0} \cdot P_{k,0}}, \quad \sum_{r=1}^{R} W_r = 1.0 \quad (100\%)$$

### 2.2 Carrier Market Share Weighting

Because domestic trunk and regional routes are operated by multiple competing carriers with disparate capacity shares, the representative route fare $P_{r,t}$ is not a naive arithmetic mean. It is computed as a carrier-market-share-weighted average:

$$P_{r,t} = \frac{\sum_{c \in C_r} \omega_c \cdot \bar{p}_{r,c,t}}{\sum_{c \in C_r} \omega_c}$$

Where:
- $C_r$: Set of carriers operating non-stop or one-stop scheduled flights on route $r$.
- $\bar{p}_{r,c,t}$: Median economy tariff quoted by carrier $c$ on route $r$ at observation time $t$.
- $\omega_c$: Domestic passenger market share of carrier $c$, calibrated from DGCA Form-A monthly traffic reports:
  - **IndiGo (6E)**: $61.2\%$
  - **Air India (AI)**: $14.3\%$
  - **Air India Express (IX)**: $6.4\%$
  - **Akasa Air (QP)**: $4.8\%$
  - **SpiceJet (SG)**: $4.2\%$
  - **Other / Regional Carriers**: $9.1\%$

---

## 3. Statutory Fare Deconstruction Protocol

Modern airline commercial displays quote bundled gross tariffs. Under DGCA Tariff Monitoring Unit (TMU) directives and Ministry of Civil Aviation guidelines, statutory ticket deconstruction is mandatory to separate carrier pricing power from government/airport statutory charges:

$$P_{\text{Total}} = P_{\text{Base}} + P_{\text{YQ}} + P_{\text{Airport}} + P_{\text{GST}}$$

| Component | Standard Proportion | Economic / Regulatory Role |
|:---|:---:|:---|
| **Base Fare ($P_{\text{Base}}$)** | $\approx 70.0\%$ | Airline net inventory revenue; dynamic pricing demand indicator |
| **Fuel Surcharge ($P_{\text{YQ}}$)** | $\approx 18.0\%$ | Direct pass-through of IOCL Aviation Turbine Fuel (ATF) index |
| **Airport Charges ($P_{\text{Airport}}$)** | $\approx 7.0\%$ | User Development Fee (UDF) & Passenger Service Fee (PSF) |
| **Statutory GST ($P_{\text{GST}}$)** | $5.0\%$ | Ministry of Finance statutory tax on domestic economy class |

In real-time ingestion, every raw quote is mapped and verified across this statutory decomposition.

---

## 4. Multi-Portal Data Ingestion & Ethical Compliance

### 4.1 11-Source Governance Coverage (6 OTAs + 5 Direct Airlines)
Problem Statement SIH26056 mandates ingestion across major domestic OTAs and airline booking portals. To satisfy this requirement with strict adherence to the rule of law and RFC 9309 standards, AeroDex maintains an explicit 11-source governance catalog:

| Source | Category | Extraction / Integration Protocol | Robots.txt Legal Status | Governance Mode |
|:---|:---|:---|:---|:---|
| **Google Flights** | Aggregator | Real-time HTTP SSR + Playwright DOM | `Allow: /travel/flights` | Active Live Scrape |
| **EaseMyTrip** | Domestic OTA | Playwright Headless Browser Extraction | `Allow: /FlightList/Index` | Active Live Scrape |
| **MakeMyTrip** | Domestic OTA | Playwright Headless Browser Extraction | `Allow: /flight/search` | Active Live Scrape |
| **Yatra** | Domestic OTA | Direct Query Search & Parsing Adapter | `Allow: /air-search/dom2` | Active Live Scrape & Verification |
| **Goibibo** | Domestic OTA | 1-Click Verification Deeplink | MMT Group Unified Engine | Live Verification Portal |
| **Cleartrip** | Domestic OTA | 1-Click Verification Deeplink | `Disallow: /flights/search` | **RFC 9309 Ethically Gated** |
| **Ixigo** | Domestic OTA | 1-Click Verification Deeplink | `Disallow: /search*` | **RFC 9309 Ethically Gated** |
| **IndiGo (6E)** | Direct Carrier | Direct Booking Query & Verification Link | Permitted with polite delay | Direct Carrier Portal |
| **Air India (AI)** | Direct Carrier | Direct Booking Query & Verification Link | Permitted with polite delay | Direct Carrier Portal |
| **Akasa Air (QP)** | Direct Carrier | Direct Booking Query & Verification Link | Permitted with polite delay | Direct Carrier Portal |
| **SpiceJet (SG)** | Direct Carrier | Direct Booking Query & Verification Link | Permitted with polite delay | Direct Carrier Portal |
| **AI Express (IX)** | Direct Carrier | Direct Booking Query & Verification Link | Permitted with polite delay | Direct Carrier Portal |

> **Ethical Compliance Gating Principle**: Rather than scraping disallowed portals (Cleartrip, Ixigo) in breach of their `robots.txt`, `RobotGuard` formally evaluates their directives, logs the ethical restriction, and surfaces pre-filled 1-Click Verification Deeplinks so evaluators and consumers can verify live market tariffs directly without violating website terms of service.

### 4.2 Enterprise Anti-Bot & Proxy Rotation Architecture (`ProxyManager`)
To prevent IP rate-limiting, Cloudflare/Akamai 403 blocks, and bot-interception in cloud runners or sandboxes, AeroDex features an active `ProxyManager` subsystem (`proxy_rotator.py`):
1. **Configurable Proxy Pool**: Reads rotating gateway endpoints from `PROXY_POOL`, `HTTP_PROXY`, and `HTTPS_PROXY` environment variables.
2. **User-Agent & Client Hints Shuffling**: Rotates across a pool of desktop Chrome, Edge, Safari, and Firefox browser signatures, keeping `sec-ch-ua`, `sec-ch-ua-mobile`, and `sec-ch-ua-platform` synchronized.
3. **Automated Bot Challenge Interception**: Inspects HTTP responses (status 403, 429) and HTML payloads for Cloudflare Turnstile (`cf-challenge`), Akamai Bot Manager (`Access Denied`), PerimeterX (`px-captcha`), and reCAPTCHA signatures.
4. **Quarantine Cooldown & Failover**: Banned or challenged egress endpoints enter an automatic 180-second cooldown, while requests fail over to the next operational proxy before cleanly resorting to the SQLite microdata warehouse.
5. **Auditable Telemetry**: Real-time proxy health and challenge counts are exposed at `GET /api/v1/compliance/anti_bot`.

### 4.3 Ethical Scraping Guard (`RobotGuard`)
In compliance with SIH26056 legal and ethical mandates:
- **`robots.txt` Pre-Request Verification & Enforcement Gate**: Candidate URLs are checked against RFC 9309 rules prior to launching browser sessions. If disallowed (`can_fetch() == False`), extraction is aborted immediately.
- **Polite Rate Limiting**: Per-domain request queues enforce a minimum crawl delay ($3.0\,\text{s}$) between successive requests to the same origin.
- **Exponential Backoff**: Dynamic backoff with randomized jitter on HTTP 429 / 503 status codes.
- **Auditable Telemetry**: Real-time compliance verification logs are exposed via `GET /api/v1/compliance/robots`.

---

## 5. Statistical Data Cleaning & Outlier Removal Protocol

Raw web-scraped tariffs frequently contain noise, multi-hop detour anomalies, cancellation placeholders, and luxury business-class listings. The data cleaning pipeline executes 5 sequential stages:

```
[Raw Web Scrape Quotes]
         │
         ▼
[1. Non-Null & Type Validation]      --> Drops null, zero, negative tariffs
         │
         ▼
[2. Operational Status Filter]       --> Filters "Sold Out", "Cancelled", "Waitlist"
         │
         ▼
[3. Statutory Range Bounds]          --> Restricts coach fares to ₹1,500 - ₹95,000
         │
         ▼
[4. Non-Parametric Outlier Cap]      --> Trims luxury quotes > 2.5x corridor median
         │
         ▼
[5. Duration Anomaly Filter]         --> Drops detours > 3.0x direct flight time
         │
         ▼
[Cleaned Representative Economy Quotes]
```

### 5.1 The 2.5x Median Rule
Rather than standard standard-deviation trimming (which is biased by extreme positive skews in exponential fare distributions), AeroDex applies a robust non-parametric rule:

$$\text{Threshold}_{\text{Upper}} = \max\left(₹28,000, \; 2.5 \times \text{Median}(P_r)\right)$$

For high-altitude or island sectors (e.g., Leh `IXL`, Port Blair `IXZ`), the statutory threshold floor is calibrated to $₹35,000$. This prevents ₹58,000 business class seats from distorting the economy baseline basket.

---

## 6. Multi-Frequency Temporal Rollups

To meet the diverse requirements of different institutional stakeholders, APIx aggregates microdata across three temporal frequencies:

### 6.1 Intraday / Daily Nowcast Bulletin
- **Frequency**: Continuous / 15-minute refresh.
- **Target User**: DGCA Tariff Monitoring Unit (TMU).
- **Deliverable**: Daily Sector Airfare Price Index Bulletin (RFC-4180 CSV export).
- **Function**: Rapid identification of abnormal route surges for regulatory scrutiny.

### 6.2 Weekly Aggregation Bulletin
- **Frequency**: Rolling 7-day calendar weeks (e.g., `2026-W37`).
- **Target User**: MoSPI NSO Economic Statistics Division & RBI Monetary Policy Department.
- **Deliverable**: Weekly Aggregation Bulletin (JSON API: `/api/v1/index/weekly`; CSV: `/api/v1/export/weekly`).
- **Metrics**: Weekly Laspeyres index, Week-over-Week (WoW) percentage change, and estimated headline CPI impact.

### 6.3 Monthly Time-Series Comparison
- **Frequency**: Calendar month.
- **Target User**: Central statistical reporting and academic research.
- **Benchmark Series**: MoSPI Official CPI COICOP 07.3.3 and IOCL Aviation Turbine Fuel (ATF) index (20-month series: Jan 2025 – Sep 2026).

---

## 7. Macroeconomic Linkage: Headline CPI Sensitivity

To evaluate the passthrough of airfare surges into headline consumer price inflation, the engine calculates the basis-point impact on the All-India Combined CPI:

$$\Delta \text{CPI}_{bps} = \left(\frac{I_{APIx, t} - 100.0}{100.0}\right) \times w_{\text{Airfare}} \times 10,000$$

Where:
- $w_{\text{Airfare}} = 0.00077$ ($0.077\%$ weight in MoSPI revised Consumer Price Index basket).
- $10,000$: Conversion multiplier to basis points ($1\% = 100\,\text{bps}$).

*Example Calculation:*  
If the National Airfare Price Index rises to $129.85$ ($+29.85\%$ over 2024 base):
$$\Delta \text{CPI}_{bps} = 0.2985 \times 0.00077 \times 10,000 \approx +2.30\,\text{basis points} \; (+0.023\%)$$

This enables the Reserve Bank of India (RBI) Monetary Policy Committee (MPC) to decompose headline transport inflation into fuel cost passthrough vs. cyclical holiday demand.

---

## 8. Econometric Forecasting Engine

AeroDex incorporates a two-layer econometric predictive engine:
1. **Machine Learning Baseline Regressor**: A Random Forest Regressor trained on 14,500+ empirical SQLite quotes predicting baseline economy tariffs as a continuous function of purchase lead time ($T+1$ to $T+45$), corridor distance ($\text{km}$), calendar month ($1$ to $12$), and day-of-week weekend effects.
2. **Calibrated Heuristic Shock Modeling**:
   - **Festival Surge Multipliers ($M_{\text{event}} \in [1.20, 1.90]$)**: Calibrated against historical MoSPI festival CPI spikes (Diwali, Chhath, Durga Puja, Pongal) and DGCA seasonal load-factor curves ($>92\%$).
   - **Extreme Calamity Profiles ($M_{\text{calamity}} \in [1.50, 1.80]$)**: Simulated coastal storm capacity cuts (-45%) and fog groundings (-35%).
   - **Methodological Transparency**: In compliance with honest statistical governance, all calendar cards and scenario chips in the UI are explicitly badged as **`Calibrated Econometric Heuristic (±80%)`**, ensuring policymakers distinguish between ML baseline forecasts and stress-test shock simulations.

---

## 9. Automated Verification & Quality Assurance

The codebase includes an automated test suite (`tests/`) ensuring 100% compliance with statistical and software engineering standards:
- **`tests/test_index_engine.py`**: Mathematical verification of Laspeyres index aggregation, carrier volume weighting, CPI basis point calculations, and weekly aggregation feeds.
- **`tests/test_scraper.py`**: Verification of statutory fare deconstruction ($P_{\text{Base}} + YQ + UDF + GST = P_{\text{Total}}$), statistical outlier filtering, cancellation filtering, MakeMyTrip card parsing, 1-click deeplink generation across all 11 sources, `ProxyManager` rotation and challenge detection, and deterministic offline `RobotGuard` compliance.
- **`tests/test_api.py`**: Integration tests verifying REST endpoints (`/api/v1/live/pulse`, `/api/v1/search`, `/api/v1/compliance/robots`, `/api/v1/compliance/anti_bot`, `/api/v1/compliance/sources`, `/api/v1/index/weekly`, `/api/v1/export/daily`, `/api/v1/export/weekly`, `/api/v1/export/quotes`).

Execution command:
```bash
python -m unittest discover tests -v
```
All 28 automated tests execute in under 1 second with 100% offline determinism and zero network flakiness.
