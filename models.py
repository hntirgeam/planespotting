#!/usr/bin/env python3
"""
Database models for ADS-B aircraft tracking.
Uses peewee ORM with PostgreSQL backend.
"""

from peewee import (
    Model, PostgresqlDatabase, CharField, FloatField,
    IntegerField, DateTimeField, TextField, UUIDField
)
from datetime import datetime
from environs import Env
import uuid

# Load environment variables
env = Env()
env.read_env()

# Database instance from connection string
db = PostgresqlDatabase(
    env.str('DB_NAME'),
    user=env.str('DB_USER'),
    password=env.str('DB_PASSWORD'),
    host=env.str('DB_HOST', 'localhost'),
    port=env.int('DB_PORT', 5432)
)


class Aircraft(Model):
    """
    Aircraft tracking record from dump1090.
    Stores all available fields from ADS-B messages.

    flight_session_id groups consecutive observations of the same aircraft.
    When an aircraft disappears for more than SESSION_TIMEOUT, a new session starts.
    This prevents trajectory jumps when plotting flight paths.
    """
    # Primary key
    id = UUIDField(primary_key=True, default=uuid.uuid4)

    # Flight session grouping for trajectory analysis
    flight_session_id = UUIDField(index=True, null=True)

    # Primary identification
    hex = CharField(max_length=6, index=True)  # ICAO address
    timestamp = DateTimeField(default=datetime.now, index=True)

    # Flight information
    flight = CharField(max_length=10, null=True)
    squawk = CharField(max_length=4, null=True)
    category = CharField(max_length=2, null=True)

    # Position data
    lat = FloatField(null=True)
    lon = FloatField(null=True)

    # Altitude (imperial and metric)
    altitude = IntegerField(null=True)  # feet
    altitude_m = FloatField(null=True)  # meters

    # Movement data (imperial and metric)
    speed = IntegerField(null=True)  # knots
    speed_kmh = FloatField(null=True)  # km/h
    track = IntegerField(null=True)  # degrees
    vert_rate = IntegerField(null=True)  # feet/min
    vert_rate_ms = FloatField(null=True)  # m/s

    # Position accuracy
    nucp = IntegerField(null=True)
    seen_pos = FloatField(null=True)

    # Reception metadata
    messages = IntegerField(null=True)
    seen = FloatField(null=True)
    rssi = FloatField(null=True)

    # Additional arrays stored as JSON strings
    mlat = TextField(null=True)  # JSON array
    tisb = TextField(null=True)  # JSON array

    class Meta:
        database = db
        table_name = 'aircraft'


def init_db():
    """Initialize database and create tables if they don't exist."""
    db.connect()
    db.create_tables([Aircraft], safe=True)


def close_db():
    """Close database connection."""
    if not db.is_closed():
        db.close()


# Session timeout in seconds (30 minutes)
SESSION_TIMEOUT = 1800


def get_or_create_flight_session(icao_hex: str) -> uuid.UUID:
    """
    Get existing flight session or create new one based on last observation time.

    If the aircraft hasn't been seen for more than SESSION_TIMEOUT seconds,
    creates a new session to avoid trajectory jumps in visualization.

    Args:
        icao_hex: Aircraft ICAO address

    Returns:
        UUID of the flight session
    """
    last_record = Aircraft.select().where(Aircraft.hex == icao_hex.upper()).order_by(Aircraft.timestamp.desc()).first()

    if last_record:
        time_diff = (datetime.now() - last_record.timestamp).total_seconds()

        # If seen recently, reuse session
        if time_diff < SESSION_TIMEOUT:
            return last_record.flight_session_id

    # Create new session
    return uuid.uuid4()
