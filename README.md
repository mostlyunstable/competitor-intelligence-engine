# Competitor Intelligence Engine

An advanced, adaptive data collection engine that crawls competitor websites and stores structured data in PostgreSQL. Built for high-coverage extraction without the use of brittle CSS selectors.

## 🚀 Key Features

*   **23 Adaptive Extraction Strategies:** Uses DOM proximity, Schema.org/JSON-LD, NLP, semantic HTML, and multi-pass heuristic models to extract data gracefully even when sites change layouts.
*   **Comprehensive Data Coverage:** Extracts Companies, Services, Pricing, Content, Social Profiles, Team Members, Physical Locations, FAQs, Reviews, Trust Signals, Contact Forms, Tables, Media Assets, and Breadcrumb structures.
*   **Intelligent Crawl Budgeting:** Priority queue with URL scoring, canonical URL enforcement (50+ tracking params stripped), and duplicate detection via ETag/Last-Modified.
*   **Robust Deduplication:** Dual-layer deduplication using fast normalized hash sets for URLs and SHA-256 content hashes for stored data.
*   **Production-Ready Observability:** Built-in Prometheus metrics (`/metrics`) monitoring crawl duration, extraction yields, strategy success rates, and errors.
*   **Self-Healing Database:** Uses upsert logic, context managers, and transaction boundaries to ensure database ACID consistency even on pipeline crashes.
*   **Entity Resolution & Relationship Linking:** Automatic deduplication with fuzzy matching, canonicalization, and mapping entities into coherent graphs.
*   **Evidence Metadata:** DOM path, XPath, and HTML snippet for every extraction.
*   **Interactive Real-Time Dashboard:** Access system health, collection metrics, real-time server telemetry (CPU/Memory/Proxies), and trigger background pipeline tasks visually via the interactive web UI at `/dashboard`.
*   **Fault-Tolerant Distributed Queue:** Utilizes a Redis-backed queue system with stateful processing maps and Dead Letter Queue (DLQ) routing for maximum uptime without OOM crashes.
*   **Hybrid Ingestion Engine:** Supports standard SSR HTML fetching via `httpx` and dynamic Single Page Application (SPA) rendering via Chromium/`Playwright`, armed with stealth modes to bypass WAFs.

## 📚 Documentation

- **[Architecture Guide](docs/architecture.md)** - System design and component overview
- **[API Documentation](docs/api.md)** - REST API reference with examples
- **[OpenAPI Specification](https://api.utservio.com/openapi.json)** - Machine-readable API spec

---

## 🛠 Prerequisites

Before starting, ensure you have:
*   **Python 3.12+**
*   **PostgreSQL 14+** (Running locally or via Docker)
*   **Git**

---

## 🖥 Step-by-Step Installation

### Option 1: Native Installation (Mac / Linux / Windows)

#### 1. Clone the Repository
```bash
git clone https://github.com/mostlyunstable/competitor-intelligence-engine.git
cd competitor-intelligence-engine
```

#### 2. Install PostgreSQL

**macOS (via Homebrew):**
```bash
brew install postgresql@16
brew services start postgresql@16
```

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install postgresql postgresql-contrib
sudo systemctl start postgresql
sudo systemctl enable postgresql
```

**Windows:**
Download the installer from [PostgreSQL Official Site](https://www.postgresql.org/download/windows/) and follow the installation wizard. Remember your `postgres` superuser password.

#### 3. Setup the Database

Create a dedicated database and user.

**Mac / Linux:**
```bash
sudo -u postgres psql -c "CREATE USER utservio WITH PASSWORD 'changeme_in_production';"
sudo -u postgres psql -c "CREATE DATABASE utservio_ci OWNER utservio;"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE utservio_ci TO utservio;"
```

**Windows (via psql command line):**
Open `psql` (SQL Shell) from your Start Menu and run:
```sql
CREATE USER utservio WITH PASSWORD 'changeme_in_production';
CREATE DATABASE utservio_ci OWNER utservio;
GRANT ALL PRIVILEGES ON DATABASE utservio_ci TO utservio;
```

#### 4. Setup Python Environment
```bash
# Create a virtual environment
python -m venv .venv

# Activate the virtual environment
# On macOS / Linux:
source .venv/bin/activate
# On Windows:
.venv\Scripts\activate

# Install all required dependencies
pip install -e ".[dev]"

# Install Playwright browsers (for scraping JS-heavy sites)
python -m playwright install chromium
```

#### 5. Configure Environment Variables
Copy the example environment configuration:
```bash
cp .env.example .env
```
Ensure your `.env` contains the correct database URLs:
```env
DATABASE_URL=postgresql+asyncpg://utservio:changeme_in_production@localhost:5432/utservio_ci
CI_DATABASE__URL=postgresql+asyncpg://utservio:changeme_in_production@localhost:5432/utservio_ci
```

#### 6. Run Database Migrations
Create the database tables using Alembic:
```bash
alembic upgrade head
```

#### 7. Start the Engine
```bash
# Start the FastAPI server with auto-reload for development
uvicorn app.main:app --reload

# Start the FastAPI server in production mode (using multiple workers)
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

The application is now running.
- **Interactive Dashboard:** Access the live UI at `http://localhost:8000/dashboard`.
- **API Documentation:** Interactive Swagger UI is at `http://localhost:8000/docs`.

---

### Option 2: Docker Installation

If you prefer using Docker, the setup is heavily automated:

```bash
# 1. Clone repository
git clone https://github.com/mostlyunstable/competitor-intelligence-engine.git
cd competitor-intelligence-engine

# 2. Setup environment variables
cp .env.example .env

# 3. Start services via Docker Compose
docker compose up -d

# 4. Run database migrations inside the container
docker compose exec api alembic upgrade head
```

---

## 🎯 Collecting Competitor Data

Competitors are managed via a `competitors.json` configuration file (copy the sample if needed: `cp sample-data/competitors.json competitors.json`). Do not track this file in Git to keep your competitor targets private.

### Using the Interactive Dashboard
The easiest way to collect data is via the built-in UI:
1. Navigate to `http://localhost:8000/dashboard`
2. Use the dropdown to select a competitor.
3. Click **Start Collection** to trigger the background pipeline.
4. Watch the progress bar advance through Discovery, Parsing, and Storage stages.
5. Click **View Extracted JSON** or **Download CSV** once complete.

### Running via Command Line
Alternatively, use the bundled `scripts/collect.py` tool to trigger scraping pipelines manually:

```bash
# Ensure your virtual environment is activated
source .venv/bin/activate  # Or .venv\Scripts\activate on Windows

# Collect data from ALL enabled competitors in your configuration
python scripts/collect.py --all

# Collect data from a specific competitor by name
python scripts/collect.py --competitor "Example Corp"

# Collect data by competitor ID
python scripts/collect.py --id 1
```

---

## 🧪 Testing and Development

We maintain a high standard for code quality. Before submitting a PR or pushing code, ensure you run the testing suite:

```bash
# Run unit and integration tests
pytest

# Run type checking
mypy app tests

# Run linter and code formatting checks
ruff check app tests
ruff format --check app tests
```

---

## 🏗 Architecture Overview

The system uses a strictly decoupled architecture:
1.  **Collection Service**: Orchestrates the crawling process.
2.  **Collectors**: Specialized modules for fetching raw data (e.g., Company, Services, Pricing).
3.  **Parsers / Strategies**: HTML parser that uses a cascading list of strategies (JSON-LD -> Semantic HTML -> Generic DOM) to extract structured data into Pydantic models.
4.  **Repositories**: Responsible for validating and upserting parsed models into PostgreSQL safely.
5.  **Raw Storage**: Maintains point-in-time snapshots of raw HTML for future reprocessing.

See `documentation/architecture.md` for a deeper dive.
