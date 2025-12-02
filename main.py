#!/usr/bin/env python3
"""
ADS-B Aircraft Tracker
Reads dump1090 JSON data and logs aircraft information to database.
"""

import json
import time
import os
import sys
import logging
import argparse
from typing import Dict, Any, Optional

from models import Aircraft, init_db, close_db


def setup_logging(level: str = 'INFO') -> logging.Logger:
    """Configure logging with specified level."""
    logger = logging.getLogger('adsb_tracker')
    logger.setLevel(getattr(logging, level.upper()))

    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    return logger


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='ADS-B Aircraft Tracker')
    parser.add_argument(
        '--pretty',
        action='store_true',
        help='Enable pretty console output (default: structured logging)'
    )
    parser.add_argument(
        '--json-file',
        default='/tmp/dump1090/aircraft.json',
        help='Path to dump1090 aircraft.json file'
    )
    parser.add_argument(
        '--interval',
        type=int,
        default=1,
        help='Polling interval in seconds'
    )
    parser.add_argument(
        '--log-level',
        default='INFO',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        help='Logging level'
    )
    return parser.parse_args()


def read_aircraft_json(json_file: str, logger: logging.Logger) -> Optional[Dict[str, Any]]:
    """Read and parse dump1090 JSON file."""
    try:
        if not os.path.exists(json_file):
            logger.warning(f"Waiting for {json_file}...")
            return None

        with open(json_file, 'r') as f:
            data = json.load(f)

        return data

    except json.JSONDecodeError:
        logger.error("JSON decode error, retrying...")
        return None
    except Exception as e:
        logger.error(f"Error reading JSON: {e}")
        return None


def save_aircraft_to_db(aircraft: Dict[str, Any], logger: logging.Logger) -> bool:
    """Save aircraft data to database."""
    try:
        # Convert arrays to JSON strings
        mlat_json = json.dumps(aircraft.get('mlat', []))
        tisb_json = json.dumps(aircraft.get('tisb', []))

        # Create database record
        Aircraft.create(
            hex=aircraft.get('hex', '').upper(),
            flight=aircraft.get('flight', '').strip() or None,
            squawk=aircraft.get('squawk'),
            category=aircraft.get('category'),
            lat=aircraft.get('lat'),
            lon=aircraft.get('lon'),
            altitude=aircraft.get('altitude'),
            speed=aircraft.get('speed'),
            track=aircraft.get('track'),
            vert_rate=aircraft.get('vert_rate'),
            nucp=aircraft.get('nucp'),
            seen_pos=aircraft.get('seen_pos'),
            messages=aircraft.get('messages'),
            seen=aircraft.get('seen'),
            rssi=aircraft.get('rssi'),
            mlat=mlat_json,
            tisb=tisb_json
        )

        return True

    except Exception as e:
        logger.error(f"Database error for ICAO {aircraft.get('hex', 'N/A')}: {e}")
        return False


def log_aircraft_structured(aircraft: Dict[str, Any], logger: logging.Logger) -> None:
    """Log aircraft data in structured format."""
    icao = aircraft.get('hex', 'N/A').upper()
    flight = aircraft.get('flight', '').strip() or 'Unknown'

    log_msg = f"ICAO={icao} Flight={flight}"

    if aircraft.get('altitude'):
        log_msg += f" Alt={aircraft['altitude']}ft"

    if aircraft.get('lat') and aircraft.get('lon'):
        log_msg += f" Pos={aircraft['lat']:.5f},{aircraft['lon']:.5f}"

    if aircraft.get('speed'):
        log_msg += f" Speed={aircraft['speed']}kt"

    if aircraft.get('track'):
        log_msg += f" Track={aircraft['track']}°"

    if aircraft.get('rssi'):
        log_msg += f" RSSI={aircraft['rssi']:.1f}dBFS"

    log_msg += f" Msgs={aircraft.get('messages', 0)} Seen={aircraft.get('seen', 0):.1f}s"

    logger.info(log_msg)


def pretty_print_aircraft(data: Dict[str, Any], clear_screen: bool = True) -> None:
    """Pretty print aircraft data with emojis (original functionality)."""
    if clear_screen:
        os.system('clear' if os.name != 'nt' else 'cls')

    aircraft_list = data.get('aircraft', [])
    timestamp = time.strftime('%H:%M:%S')

    print(f"⏰ {timestamp} | Total messages: {data.get('messages', 0)}")
    print(f"✈️  Aircraft visible: {len(aircraft_list)}")
    print("=" * 80)

    if len(aircraft_list) == 0:
        print("No aircraft detected. Antenna working? Try checking dump1090 console.")
        return

    for ac in aircraft_list:
        icao = ac.get('hex', 'N/A').upper()
        flight = ac.get('flight', '').strip() or 'Unknown'
        alt = ac.get('altitude')
        lat = ac.get('lat')
        lon = ac.get('lon')
        speed = ac.get('speed')
        track = ac.get('track')
        rssi = ac.get('rssi')
        seen = ac.get('seen', 0)
        messages = ac.get('messages', 0)

        print(f"\n🛫 ICAO: {icao} | Flight: {flight} | Messages: {messages}")

        if alt is not None:
            print(f"   📏 Altitude: {alt} ft ({alt/3.28084:.0f} m)")

        if lat is not None and lon is not None:
            print(f"   📍 Position: {lat:.5f}°, {lon:.5f}°")

        if speed is not None:
            print(f"   🚀 Speed: {speed} kt")

        if track is not None:
            print(f"   🧭 Track: {track}°")

        if rssi is not None:
            print(f"   📶 Signal: {rssi:.1f} dBFS")

        print(f"   ⏱️  Last seen: {seen:.1f}s ago")

    print("\n" + "=" * 80)


def process_aircraft_data(
    data: Dict[str, Any],
    logger: logging.Logger,
    pretty_mode: bool = False
) -> None:
    """Process aircraft data: display and save to database."""
    if pretty_mode:
        pretty_print_aircraft(data)
    else:
        aircraft_list = data.get('aircraft', [])
        logger.info(f"Processing {len(aircraft_list)} aircraft, {data.get('messages', 0)} total messages")

    # Save each aircraft to database
    for aircraft in data.get('aircraft', []):
        if not pretty_mode:
            log_aircraft_structured(aircraft, logger)

        save_aircraft_to_db(aircraft, logger)


def main():
    """Main loop."""
    args = parse_args()
    logger = setup_logging(args.log_level)

    # Initialize database
    try:
        init_db()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        sys.exit(1)

    if args.pretty:
        print("🛩️  Aircraft Tracker (Pretty mode + Database logging)")
        print("=" * 80)
    else:
        logger.info("Starting ADS-B tracker in structured logging mode")
        logger.info(f"Monitoring: {args.json_file}")

    try:
        while True:
            data = read_aircraft_json(args.json_file, logger)

            if data:
                process_aircraft_data(data, logger, args.pretty)

            time.sleep(args.interval)

    except KeyboardInterrupt:
        if args.pretty:
            print("\n\n👋 Stopped")
        else:
            logger.info("Tracker stopped by user")

    finally:
        close_db()
        logger.info("Database connection closed")


if __name__ == '__main__':
    main()
