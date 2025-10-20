import csv
import sys
from dataclasses import dataclass, asdict
from datetime import datetime, date, time, timedelta
from pathlib import Path
from typing import List, Optional

DATA_FILE = Path("time_entries.csv")

# Hourly rates (you can change these values)
RATE_REGULAR_DAY = 1.0
RATE_REGULAR_NIGHT = 1.3
RATE_OVERTIME_DAY = 1.5
RATE_OVERTIME_NIGHT = 2.0

DAY_START = time(6, 0)
DAY_END = time(21, 0)

@dataclass
class TimeEntry:
    work_date: date
    start: datetime
    end: datetime

    def to_csv_row(self) -> List[str]:
        return [self.work_date.isoformat(), self.start.isoformat(), self.end.isoformat()]

    @staticmethod
    def from_csv_row(row: List[str]) -> "TimeEntry":
        work_date = date.fromisoformat(row[0])
        start = datetime.fromisoformat(row[1])
        end = datetime.fromisoformat(row[2])
        return TimeEntry(work_date, start, end)

def load_entries() -> List[TimeEntry]:
    entries = []
    if DATA_FILE.exists():
        with DATA_FILE.open("r", newline="") as f:
            reader = csv.reader(f)
            for row in reader:
                entries.append(TimeEntry.from_csv_row(row))
    return entries

def save_entry(entry: TimeEntry) -> None:
    new_file = not DATA_FILE.exists()
    with DATA_FILE.open("a", newline="") as f:
        writer = csv.writer(f)
        if new_file:
            pass  # no header, just rows
        writer.writerow(entry.to_csv_row())

def overlapping_interval(start: datetime, end: datetime, interval_start: datetime, interval_end: datetime) -> float:
    """Return hours overlapping between [start, end] and [interval_start, interval_end]."""
    latest_start = max(start, interval_start)
    earliest_end = min(end, interval_end)
    if latest_start >= earliest_end:
        return 0.0
    return (earliest_end - latest_start).total_seconds() / 3600

def categorize_hours(start: datetime, end: datetime):
    total_hours = (end - start).total_seconds() / 3600
    day_interval_start = datetime.combine(start.date(), DAY_START)
    day_interval_end = datetime.combine(start.date(), DAY_END)

    day_hours = overlapping_interval(start, end, day_interval_start, day_interval_end)
    night_hours = total_hours - day_hours

    regular_hours = min(8.0, total_hours)
    overtime_hours = max(0.0, total_hours - 8.0)

    day_regular = min(day_hours, regular_hours)
    night_regular = regular_hours - day_regular
    day_overtime = min(overtime_hours, max(0.0, day_hours - day_regular))
    night_overtime = overtime_hours - day_overtime

    return {
        "day_regular": day_regular,
        "night_regular": night_regular,
        "day_overtime": day_overtime,
        "night_overtime": night_overtime,
    }

def add_entry(date_str: str, start_str: str, end_str: str):
    start = datetime.fromisoformat(f"{date_str} {start_str}")
    end_dt = datetime.fromisoformat(f"{date_str} {end_str}")
    if end_dt <= start:
        end_dt += timedelta(days=1)
    entry = TimeEntry(start.date(), start, end_dt)
    save_entry(entry)
    print("Entry added")

def summary(start_date: Optional[str] = None, end_date: Optional[str] = None):
    entries = load_entries()
    if start_date:
        start_filter = date.fromisoformat(start_date)
    else:
        start_filter = min((e.work_date for e in entries), default=date.today())
    if end_date:
        end_filter = date.fromisoformat(end_date)
    else:
        end_filter = max((e.work_date for e in entries), default=date.today())

    totals = {
        "day_regular": 0.0,
        "night_regular": 0.0,
        "day_overtime": 0.0,
        "night_overtime": 0.0,
    }

    for e in entries:
        if start_filter <= e.work_date <= end_filter:
            c = categorize_hours(e.start, e.end)
            for k in totals:
                totals[k] += c[k]

    pay = (
        totals["day_regular"] * RATE_REGULAR_DAY
        + totals["night_regular"] * RATE_REGULAR_NIGHT
        + totals["day_overtime"] * RATE_OVERTIME_DAY
        + totals["night_overtime"] * RATE_OVERTIME_NIGHT
    )

    print("Resumen desde", start_filter, "hasta", end_filter)
    for k, v in totals.items():
        print(f"{k.replace('_', ' ').title():<20}: {v:.2f} horas")
    print(f"Pago estimado: {pay:.2f}")

def usage():
    print("Uso:")
    print("  python time_tracker.py add <fecha YYYY-MM-DD> <hora_inicio HH:MM> <hora_fin HH:MM>")
    print("  python time_tracker.py summary [--start YYYY-MM-DD] [--end YYYY-MM-DD]")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        usage()
        sys.exit(1)
    cmd = sys.argv[1]
    if cmd == "add" and len(sys.argv) == 5:
        add_entry(sys.argv[2], sys.argv[3], sys.argv[4])
    elif cmd == "summary":
        start_date = None
        end_date = None
        if "--start" in sys.argv:
            idx = sys.argv.index("--start")
            start_date = sys.argv[idx + 1]
        if "--end" in sys.argv:
            idx = sys.argv.index("--end")
            end_date = sys.argv[idx + 1]
        summary(start_date, end_date)
    else:
        usage()
