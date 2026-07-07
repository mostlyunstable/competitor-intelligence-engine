# Competitor Intelligence Engine

An advanced, adaptive data collection engine that crawls competitor websites and stores structured data in PostgreSQL. Built for high-coverage extraction without the use of brittle CSS selectors.

## 🚀 Key Features

*   **15+ Adaptive Extraction Strategies:** Uses DOM proximity, Schema.org/JSON-LD, NLP, semantic HTML, and multi-pass heuristic models to extract data gracefully even when sites change layouts.
*   **Comprehensive Data Coverage:** Extracts Companies, Services, Pricing, Content, Social Profiles, Team Members, Physical Locations, FAQs, Reviews, Trust Signals, Contact Forms, Tables, Media Assets, and Breadcrumb structures.
*   **Intelligent Crawl Budgeting:** Priority queue with URL scoring, canonical URL enforcement (50+ tracking params stripped), and duplicate detection via ETag/Last-Modified.
*   **Robust Deduplication:** Dual-layer deduplication using fast normalized hash sets for URLs and SHA-256 content hashes for stored data.
*   **Production-Ready Observability:** Built-in Prometheus metrics (`/metrics`) monitoring crawl duration, extraction yields, strategy success rates, and errors.
*   **Self-Healing Database:** Uses upsert logic and transaction boundaries per collector to ensure database consistency.

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
# Start the API server in production mode
python scripts/run.py

# OR start in development mode with auto-reload
python scripts/dev.py
```

The API will be available at `http://localhost:8000`. 
Interactive API documentation can be accessed at `http://localhost:8000/docs`.

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

### Running a Collection Pipeline

Use the bundled `scripts/collect.py` tool to trigger scraping pipelines manually:

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
