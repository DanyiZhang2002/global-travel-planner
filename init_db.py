"""init_db.py — 行旅日记 幂等建表。install.sh 调用：python3 init_db.py"""
import psycopg


def load_db_props(path: str = "db.properties") -> dict[str, str]:
    props: dict[str, str] = {}
    try:
        with open(path) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, _, v = line.partition("=")
                props[k.strip()] = v.strip()
    except FileNotFoundError:
        pass
    return props


SCHEMA = """
CREATE TABLE IF NOT EXISTS trips (
    id            SERIAL PRIMARY KEY,
    owner_id      TEXT          NOT NULL,
    name          TEXT          NOT NULL,
    destination   TEXT          NOT NULL DEFAULT '',
    start_date    DATE          NOT NULL,
    end_date      DATE          NOT NULL,
    cover_image   TEXT,
    total_budget  NUMERIC(12, 2),
    notes         TEXT,
    created_at    TIMESTAMPTZ   DEFAULT NOW(),
    updated_at    TIMESTAMPTZ   DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_trips_owner ON trips (owner_id);

CREATE TABLE IF NOT EXISTS itinerary_items (
    id           SERIAL PRIMARY KEY,
    trip_id      INT           NOT NULL REFERENCES trips(id) ON DELETE CASCADE,
    owner_id     TEXT          NOT NULL,
    date         DATE          NOT NULL,
    start_time   TEXT,
    end_time     TEXT,
    type         TEXT          NOT NULL DEFAULT 'other',
    title        TEXT          NOT NULL,
    location     TEXT,
    address      TEXT,
    transport    TEXT,
    cost         NUMERIC(12, 2),
    precautions  TEXT,
    notes        TEXT,
    extra        JSONB         DEFAULT '{}',
    images       JSONB         DEFAULT '[]',
    completed    BOOLEAN       DEFAULT FALSE,
    sort_order   INT           NOT NULL DEFAULT 0,
    created_at   TIMESTAMPTZ   DEFAULT NOW(),
    updated_at   TIMESTAMPTZ   DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_items_trip ON itinerary_items (trip_id, date);

CREATE TABLE IF NOT EXISTS trip_files (
    id           SERIAL PRIMARY KEY,
    owner_id     TEXT          NOT NULL,
    filename     TEXT          NOT NULL,
    content_type TEXT,
    oid          OID           NOT NULL,
    size         BIGINT,
    created_at   TIMESTAMPTZ   DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_trip_files_owner ON trip_files (owner_id);
"""


def main() -> None:
    p = load_db_props()
    if not p.get("db.host"):
        print("[init_db] db.properties 未找到或为空 — 跳过")
        return
    with psycopg.connect(
        host=p["db.host"],
        port=int(p["db.port"]),
        dbname=p["db.database"],
        user=p["db.username"],
        password=p["db.password"],
    ) as conn:
        conn.execute(SCHEMA)
        conn.commit()
    print("[init_db] done")


if __name__ == "__main__":
    main()
