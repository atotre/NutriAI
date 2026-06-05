"""
pipeline.py — NutriAI Database Connection Engine
Reads directly from ../data/food_database.db.
No data generation logic lives here.
"""

import sqlite3
import os
import sys
import pandas as pd

# ─────────────────────────────────────────────────────────────────────────────
# Path resolution — works whether app.py is run from code/ or from the project root
# ─────────────────────────────────────────────────────────────────────────────

_HERE = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(_HERE, "..", "data", "food_database.db")

REQUIRED_COLUMNS = [
    "meal_id", "name", "meal_type",
    "calories", "protein", "carbs", "fat", "fiber",
    "iron", "calcium", "vitamin_b12", "vitamin_d", "zinc",
    "sodium", "potassium", "magnesium", "glycemic_index",
    "is_low_fodmap", "fodmap_triggers", "is_gerd_safe",
    "is_vegetarian", "is_vegan", "is_pescatarian",
    "is_diabetic_friendly", "is_dash_compliant",
    "contains_gluten", "contains_dairy", "contains_eggs", "contains_soy",
    "contains_tree_nuts", "contains_shellfish", "contains_fish", "contains_peanuts",
]

NUTRIENT_COLS = [
    "calories", "protein", "carbs", "fat", "fiber",
    "iron", "calcium", "vitamin_b12", "vitamin_d", "zinc",
    "sodium", "potassium", "magnesium", "glycemic_index",
]

MIN_ROWS = 10_000


# ─────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────────────────────────────────────

def _get_connection(db_path: str = DB_PATH) -> sqlite3.Connection:
    if not os.path.exists(db_path):
        sys.exit(
            f"\n[pipeline] FATAL: Database not found at:\n  {os.path.abspath(db_path)}\n"
            "Run setup first:\n  python data/build_database.py\n"
        )
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def _verify_schema(conn: sqlite3.Connection) -> None:
    """Raise if any required column is absent from the meals table."""
    cursor = conn.execute("PRAGMA table_info(meals);")
    existing = {row["name"] for row in cursor.fetchall()}
    missing  = set(REQUIRED_COLUMNS) - existing
    if missing:
        raise RuntimeError(
            f"[pipeline] Schema mismatch — missing columns: {sorted(missing)}\n"
            "Re-run: python data/build_database.py"
        )


def _verify_row_count(conn: sqlite3.Connection) -> int:
    """Return row count; raise if below MIN_ROWS."""
    count = conn.execute("SELECT COUNT(*) FROM meals;").fetchone()[0]
    if count < MIN_ROWS:
        raise RuntimeError(
            f"[pipeline] Only {count:,} rows found (minimum {MIN_ROWS:,}).\n"
            "Re-run: python data/build_database.py"
        )
    return count


def _sql_deduplicate(conn: sqlite3.Connection) -> int:
    """
    Remove duplicate meal names in-place, keeping lowest meal_id.
    Returns number of rows removed.
    """
    cur = conn.execute("""
        DELETE FROM meals
        WHERE  meal_id NOT IN (
            SELECT MIN(meal_id)
            FROM   meals
            GROUP  BY name
        )
    """)
    conn.commit()
    return cur.rowcount


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

def load_meals(
    db_path: str = DB_PATH,
    meal_types: list[str] | None = None,
    run_dedup: bool = False,
) -> pd.DataFrame:
    """
    Primary entry point for all other modules.

    Parameters
    ----------
    db_path    : override the default database path
    meal_types : if provided, filter to ["Breakfast"], ["Lunch"], etc.
    run_dedup  : execute SQL deduplication before loading (default False —
                 the builder already deduplicates; use True only for ad-hoc
                 data quality runs)

    Returns
    -------
    pd.DataFrame with columns from REQUIRED_COLUMNS
    """
    conn = _get_connection(db_path)
    _verify_schema(conn)

    if run_dedup:
        removed = _sql_deduplicate(conn)
        if removed:
            print(f"[pipeline] Removed {removed:,} duplicate rows.")

    _verify_row_count(conn)

    if meal_types:
        placeholders = ",".join(["?"] * len(meal_types))
        query = f"SELECT * FROM meals WHERE meal_type IN ({placeholders})"
        df = pd.read_sql_query(query, conn, params=meal_types)
    else:
        df = pd.read_sql_query("SELECT * FROM meals", conn)

    conn.close()

    # Coerce numeric columns
    for col in NUTRIENT_COLS + [
        "is_low_fodmap", "is_gerd_safe", "is_vegetarian", "is_vegan",
        "is_pescatarian", "is_diabetic_friendly", "is_dash_compliant",
        "contains_gluten", "contains_dairy", "contains_eggs", "contains_soy",
        "contains_tree_nuts", "contains_shellfish", "contains_fish", "contains_peanuts",
    ]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    return df


def load_meals_by_type(meal_type: str, db_path: str = DB_PATH) -> pd.DataFrame:
    """Convenience wrapper — load only one meal type."""
    return load_meals(db_path=db_path, meal_types=[meal_type])


def get_db_stats(db_path: str = DB_PATH) -> dict:
    """Return summary statistics for the database (used by the UI)."""
    conn = _get_connection(db_path)
    stats: dict = {}

    stats["total_meals"] = conn.execute("SELECT COUNT(*) FROM meals;").fetchone()[0]

    for mt in ["Breakfast", "Lunch", "Dinner"]:
        count = conn.execute(
            "SELECT COUNT(*) FROM meals WHERE meal_type = ?;", (mt,)
        ).fetchone()[0]
        stats[f"count_{mt.lower()}"] = count

    stats["low_fodmap"]   = conn.execute(
        "SELECT COUNT(*) FROM meals WHERE is_low_fodmap = 1;"
    ).fetchone()[0]
    stats["gerd_safe"]    = conn.execute(
        "SELECT COUNT(*) FROM meals WHERE is_gerd_safe = 1;"
    ).fetchone()[0]
    stats["diabetic_ok"]  = conn.execute(
        "SELECT COUNT(*) FROM meals WHERE is_diabetic_friendly = 1;"
    ).fetchone()[0]
    stats["dash_compliant"] = conn.execute(
        "SELECT COUNT(*) FROM meals WHERE is_dash_compliant = 1;"
    ).fetchone()[0]
    stats["vegan"]        = conn.execute(
        "SELECT COUNT(*) FROM meals WHERE is_vegan = 1;"
    ).fetchone()[0]
    stats["vegetarian"]   = conn.execute(
        "SELECT COUNT(*) FROM meals WHERE is_vegetarian = 1;"
    ).fetchone()[0]

    conn.close()
    return stats


def get_db_path() -> str:
    return os.path.abspath(DB_PATH)


# ─────────────────────────────────────────────────────────────────────────────
# CLI utility
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print(f"[pipeline] Database path: {get_db_path()}")
    stats = get_db_stats()
    for k, v in stats.items():
        print(f"  {k:<25} {v:,}")
    df = load_meals()
    print(f"\n[pipeline] DataFrame shape: {df.shape}")
    print(df.head(3).to_string())
