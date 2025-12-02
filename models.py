#!/usr/bin/env python3
"""
Database models for ADS-B aircraft tracking.
Uses peewee ORM with SQLite backend.
"""

from peewee import (
    Model, SqliteDatabase, CharField, FloatField,
    IntegerField, DateTimeField, TextField
)
from datetime import datetime

# Database instance
db = SqliteDatabase('adsb_tracker.db')


class Aircraft(Model):
    """
    Aircraft tracking record from dump1090.
    Stores all available fields from ADS-B messages.
    """
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
    altitude = IntegerField(null=True)  # feet

    # Movement data
    speed = IntegerField(null=True)  # knots
    track = IntegerField(null=True)  # degrees
    vert_rate = IntegerField(null=True)  # feet/min

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


# Migration notes:
# To migrate from SQLite to PostgreSQL:
# 1. Change: db = PostgresqlDatabase('adsb_tracker', user='your_user', password='your_pass', host='localhost')
# 2. Export data: sqlite3 adsb_tracker.db .dump > backup.sql
# 3. Convert and import using pgloader or manually adjust SQL syntax (main differences: AUTOINCREMENT -> SERIAL, TEXT -> VARCHAR, etc.)
