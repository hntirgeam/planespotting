# ADS-B Aircraft Tracker

Log ADS-B data from dump1090 to PostgreSQL database and export flight trajectories to Google Earth.

**Features:**
- Flight session tracking - prevents trajectory jumps in visualizations
- Metric + imperial units stored in database
- KML export for Google Earth
- Automatic retry on database errors

## Setup

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure database
Copy `.env_template` to `.env` and set your PostgreSQL credentials:

```bash
cp .env_template .env
```

Edit `.env`:
```
DB_NAME=adsb_tracker
DB_USER=postgres
DB_PASSWORD=your_password
DB_HOST=localhost
DB_PORT=5432
```

Create database:
```bash
psql -U postgres -c "CREATE DATABASE adsb_tracker;"
```

## Usage

### Start tracking
```bash
# Default mode (structured logging)
python main.py

# Pretty output mode
python main.py --pretty
```

### Export to Google Earth
```bash
# Export all trajectories
python export_kml.py

# Export specific aircraft
python export_kml.py --icao 4C01E2

# Filter by maximum altitude (in meters)
python export_kml.py --max-altitude 5000

# Custom output file
python export_kml.py --output my_flights.kml
```

Open the generated `.kml` file in Google Earth to view 3D flight paths.

## dump1090 setup
```bash
dump1090 --write-json /tmp/dump1090 --write-json-every 1 --net --lat 44.80247 --lon 20.46632 --metric --fix --quiet
```
