import argparse
from collections import defaultdict
import simplekml
from models import Aircraft, init_db, close_db


def generate_color(icao_hex: str) -> str:
    """Generate consistent color for each aircraft based on ICAO hex."""
    # Use hash to generate consistent color
    hash_val = hash(icao_hex)
    r = (hash_val & 0xFF0000) >> 16
    g = (hash_val & 0x00FF00) >> 8
    b = (hash_val & 0x0000FF)

    # KML color format: aabbggrr (alpha, blue, green, red)
    return f'ff{b:02x}{g:02x}{r:02x}'


def fetch_trajectories(max_altitude_m: float = None):
    """
    Fetch all aircraft records with coordinates from database.

    Args:
        max_altitude_m: Maximum altitude in meters (filter out higher altitudes)

    Returns dict: {icao_hex: {session_id: [records]}}
    """
    # Build query conditions
    conditions = [
        Aircraft.lat.is_null(False),
        Aircraft.lon.is_null(False),
        Aircraft.altitude_m.is_null(False)
    ]

    # Add altitude filter if specified
    if max_altitude_m is not None:
        conditions.append(Aircraft.altitude_m <= max_altitude_m)

    # Query all records with position data, ordered by timestamp
    records = (
        Aircraft
        .select()
        .where(*conditions)
        .order_by(Aircraft.timestamp.asc())
    )

    # Group by ICAO and session
    trajectories = defaultdict(lambda: defaultdict(list))

    for record in records:
        trajectories[record.hex][record.flight_session_id].append(record)

    return trajectories


def create_kml(trajectories: dict, output_file: str, min_points: int = 3):
    """
    Create KML file from trajectories.

    Args:
        trajectories: Grouped aircraft records
        output_file: Output KML filename
        min_points: Minimum points required to create a trajectory
    """
    kml = simplekml.Kml()
    kml.document.name = "ADS-B Aircraft Trajectories"

    stats = {
        'total_aircraft': 0,
        'total_sessions': 0,
        'total_points': 0
    }

    # Process each aircraft
    for icao_hex, sessions in sorted(trajectories.items()):
        stats['total_aircraft'] += 1

        # Create folder for each aircraft
        aircraft_folder = kml.newfolder(name=f"ICAO: {icao_hex}")
        color = generate_color(icao_hex)

        # Process each session (flight)
        for session_id, points in sorted(sessions.items(), key=lambda x: x[1][0].timestamp):
            if len(points) < min_points:
                continue  # Skip sessions with too few points

            stats['total_sessions'] += 1
            stats['total_points'] += len(points)

            # Get flight info
            flight_name = points[0].flight or "Unknown"
            start_time = points[0].timestamp
            end_time = points[-1].timestamp
            duration = (end_time - start_time).total_seconds() / 60  # minutes

            # Create LineString for trajectory
            linestring = aircraft_folder.newlinestring(name=f"{icao_hex} ({start_time.strftime('%Y-%m-%d %H:%M')})")

            # Add coordinates (lon, lat, altitude)
            coords = []
            for point in points:
                coords.append((point.lon, point.lat, point.altitude_m))

            linestring.coords = coords
            linestring.altitudemode = simplekml.AltitudeMode.absolute
            linestring.extrude = 1  # Draw line to ground

            # Style
            linestring.style.linestyle.color = color
            linestring.style.linestyle.width = 3

            # Description with flight details
            description = f"""
            <b>Flight:</b> {flight_name.strip()}<br/>
            <b>ICAO:</b> {icao_hex}<br/>
            <b>Session ID:</b> {session_id}<br/>
            <b>Start:</b> {start_time.strftime('%Y-%m-%d %H:%M:%S')}<br/>
            <b>End:</b> {end_time.strftime('%Y-%m-%d %H:%M:%S')}<br/>
            <b>Duration:</b> {duration:.1f} minutes<br/>
            <b>Points:</b> {len(points)}<br/>
            <b>Max Altitude:</b> {max(p.altitude_m for p in points):.0f} m<br/>
            <b>Min Altitude:</b> {min(p.altitude_m for p in points):.0f} m
            """
            linestring.description = description

            # Add start point marker
            # start_point = aircraft_folder.newpoint(
            #     name=f"Start: {flight_name.strip()}",
            #     coords=[(points[0].lon, points[0].lat, points[0].altitude_m)]
            # )
            # start_point.style.iconstyle.color = simplekml.Color.green
            # start_point.style.iconstyle.scale = 0.7
            # start_point.altitudemode = simplekml.AltitudeMode.absolute

            # Add end point marker
            # end_point = aircraft_folder.newpoint(
            #     name=f"End: {flight_name.strip()}",
            #     coords=[(points[-1].lon, points[-1].lat, points[-1].altitude_m)]
            # )
            # end_point.style.iconstyle.color = simplekml.Color.red
            # end_point.style.iconstyle.scale = 0.7
            # end_point.altitudemode = simplekml.AltitudeMode.absolute

    # Save KML file
    kml.save(output_file)

    return stats


def main():
    parser = argparse.ArgumentParser(description='Export aircraft trajectories to KML')
    parser.add_argument(
        '--output',
        '-o',
        default='trajectories.kml',
        help='Output KML filename (default: trajectories.kml)'
    )
    parser.add_argument(
        '--min-points',
        type=int,
        default=2,
        help='Minimum points required per trajectory (default: 3)'
    )
    parser.add_argument(
        '--max-altitude',
        type=float,
        help='Maximum altitude in meters (filter out higher altitudes)'
    )
    parser.add_argument(
        '--icao',
        help='Filter by specific ICAO hex code'
    )

    args = parser.parse_args()

    print("🛩️  ADS-B Trajectory KML Exporter")
    print("=" * 50)

    # Initialize database
    try:
        init_db()
        print("✅ Connected to database")
    except Exception as e:
        print(f"❌ Database error: {e}")
        return 1

    # Fetch trajectories
    print("📡 Fetching trajectories from database...")
    if args.max_altitude:
        print(f"🔧 Filtering altitudes <= {args.max_altitude}m")
    trajectories = fetch_trajectories(max_altitude_m=args.max_altitude)

    if not trajectories:
        print("⚠️  No trajectories found in database")
        close_db()
        return 1

    # Filter by ICAO if specified
    if args.icao:
        icao_upper = args.icao.upper()
        if icao_upper in trajectories:
            trajectories = {icao_upper: trajectories[icao_upper]}
            print(f"🔍 Filtering for ICAO: {icao_upper}")
        else:
            print(f"⚠️  ICAO {icao_upper} not found in database")
            close_db()
            return 1

    # Generate KML
    print(f"📝 Generating KML file: {args.output}")
    stats = create_kml(trajectories, args.output, args.min_points)

    # Print statistics
    print("\n" + "=" * 50)
    print("📊 Export Statistics:")
    print(f"  Aircraft: {stats['total_aircraft']}")
    print(f"  Flight sessions: {stats['total_sessions']}")
    print(f"  Total data points: {stats['total_points']}")
    print(f"\n✅ KML file saved: {args.output}")
    print(f"💡 Open this file in Google Earth to view trajectories")

    close_db()
    return 0


if __name__ == '__main__':
    exit(main())
