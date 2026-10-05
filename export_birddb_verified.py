#!/usr/bin/env python3
import sqlite3
from pathlib import Path

DB_PATH = Path("/home/pi/BirdNET-Pi/scripts/birds.db")
OUT_PATH = Path("/home/pi/BirdNET-Pi/BirdDB_verified.txt")

HEADER = [
    "Date", "Time", "Sci_Name", "Com_Name", "Confidence",
    "Lat", "Lon", "Cutoff", "Week", "Sens", "Overlap",
    "ReviewStatus", "ReviewedAt"
]

def safe_str(value):
    if value is None:
        return ""
    return str(value)

def main():
    if not DB_PATH.exists():
        raise FileNotFoundError(f"Database not found: {DB_PATH}")

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute("""
        SELECT name
        FROM sqlite_master
        WHERE type='table' AND name='detection_reviews'
    """)
    has_reviews = cur.fetchone() is not None

    if has_reviews:
        query = """
        SELECT
            d.Date,
            d.Time,
            d.Sci_Name,
            d.Com_Name,
            d.Confidence,
            d.Lat,
            d.Lon,
            d.Cutoff,
            d.Week,
            d.Sens,
            d.Overlap,
            r.review_status AS ReviewStatus,
            r.reviewed_at AS ReviewedAt
        FROM detections d
        LEFT JOIN detection_reviews r
          ON r.file_path = (
                d.Date || '/' ||
                REPLACE(REPLACE(d.Com_Name, ' ', '_'), '''', '') || '/' ||
                d.File_Name
             )
        ORDER BY d.Date, d.Time
        """
    else:
        query = """
        SELECT
            d.Date,
            d.Time,
            d.Sci_Name,
            d.Com_Name,
            d.Confidence,
            d.Lat,
            d.Lon,
            d.Cutoff,
            d.Week,
            d.Sens,
            d.Overlap,
            '' AS ReviewStatus,
            '' AS ReviewedAt
        FROM detections d
        ORDER BY d.Date, d.Time
        """

    cur.execute(query)
    rows = cur.fetchall()

    with OUT_PATH.open("w", encoding="utf-8", newline="") as f:
        f.write(";".join(HEADER) + "\n")
        for row in rows:
            values = [
                safe_str(row["Date"]),
                safe_str(row["Time"]),
                safe_str(row["Sci_Name"]),
                safe_str(row["Com_Name"]),
                safe_str(row["Confidence"]),
                safe_str(row["Lat"]),
                safe_str(row["Lon"]),
                safe_str(row["Cutoff"]),
                safe_str(row["Week"]),
                safe_str(row["Sens"]),
                safe_str(row["Overlap"]),
                safe_str(row["ReviewStatus"]),
                safe_str(row["ReviewedAt"]),
            ]
            f.write(";".join(values) + "\n")

    conn.close()
    print(f"Done: {OUT_PATH}")

if __name__ == "__main__":
    main()
