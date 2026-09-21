"""行旅日记 — 旅行日程记录与规划 App（FastAPI + PostgreSQL + SSO）。

页面：GET / 返回 static/index.html（移动端优先的 SPA）
API：
  GET    /api/trips                       旅行列表（含行程数/完成数进度）
  POST   /api/trips                       新建旅行
  GET    /api/trips/{id}                  旅行详情 + 每日摘要 + 汇总（概览页数据）
  PUT    /api/trips/{id}                  编辑旅行
  DELETE /api/trips/{id}                  删除旅行（级联删行程）
  GET    /api/trips/{id}/items?date=…     行程列表（可按天过滤）
  POST   /api/trips/{id}/items            新增行程
  PUT    /api/items/{item_id}             编辑行程
  DELETE /api/items/{item_id}             删除行程
  POST   /api/items/{item_id}/move        上移/下移（调整顺序）
  POST   /api/trips/{id}/copy-day         复制某一天的全部行程到另一天
  POST   /api/upload                      图片上传（PG Large Object）
  GET    /api/files/{file_id}             读取图片
"""
from __future__ import annotations

import json
from datetime import date, datetime
from typing import Annotated, Any, Optional

import psycopg
from psycopg.rows import dict_row
from fastapi import FastAPI, File, Header, HTTPException, Response, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, StringConstraints

# ---------------------------------------------------------------------------
# properties / DB
# ---------------------------------------------------------------------------


def _load_props(path: str) -> dict[str, str]:
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


def _get_db_conn() -> psycopg.Connection:
    p = _load_props("db.properties")
    if not p.get("db.host"):
        raise HTTPException(status_code=503, detail="db.properties 未配置")
    return psycopg.connect(
        host=p["db.host"],
        port=int(p["db.port"]),
        dbname=p["db.database"],
        user=p["db.username"],
        password=p["db.password"],
        row_factory=dict_row,
    )


# ---------------------------------------------------------------------------
# SSO
# ---------------------------------------------------------------------------


def _parse_sso_user(decrypted_userinfo: Optional[str]) -> Optional[dict]:
    if not decrypted_userinfo:
        return None
    try:
        fixed = decrypted_userinfo.encode("latin-1").decode("utf-8")
        data = json.loads(fixed)
    except Exception:
        return None
    return {
        "userId": data.get("userId") or data.get("id"),
        "username": data.get("username") or data.get("name") or data.get("displayName"),
        "email": data.get("email") or data.get("workEmail"),
    }


def _require_user(decrypted_userinfo: Optional[str]) -> dict:
    user = _parse_sso_user(decrypted_userinfo)
    if not user:
        raise HTTPException(status_code=401, detail="unauthenticated")
    return user


# ---------------------------------------------------------------------------
# Pydantic DTO
# ---------------------------------------------------------------------------

NonBlankStr = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
DateStr = Annotated[str, StringConstraints(strip_whitespace=True, min_length=8, max_length=10)]


class TripCreate(BaseModel):
    name: NonBlankStr
    destination: str = ""
    startDate: DateStr
    endDate: DateStr
    coverImage: Optional[str] = None
    totalBudget: Optional[float] = None
    notes: Optional[str] = None


class TripUpdate(BaseModel):
    name: Optional[NonBlankStr] = None
    destination: Optional[str] = None
    startDate: Optional[DateStr] = None
    endDate: Optional[DateStr] = None
    coverImage: Optional[str] = None
    totalBudget: Optional[float] = None
    notes: Optional[str] = None


class ItemIn(BaseModel):
    date: DateStr
    startTime: Optional[str] = None   # HH:MM，空 = 待定事项
    endTime: Optional[str] = None
    type: str = "other"
    title: NonBlankStr
    location: Optional[str] = None
    address: Optional[str] = None
    transport: Optional[str] = None
    cost: Optional[float] = None
    precautions: Optional[str] = None
    notes: Optional[str] = None
    extra: dict[str, Any] = {}
    images: list[str] = []
    completed: bool = False
    sortOrder: int = 0


class ItemPatch(BaseModel):
    date: Optional[DateStr] = None
    startTime: Optional[str] = None
    endTime: Optional[str] = None
    type: Optional[str] = None
    title: Optional[NonBlankStr] = None
    location: Optional[str] = None
    address: Optional[str] = None
    transport: Optional[str] = None
    cost: Optional[float] = None
    precautions: Optional[str] = None
    notes: Optional[str] = None
    extra: Optional[dict[str, Any]] = None
    images: Optional[list[str]] = None
    completed: Optional[bool] = None
    sortOrder: Optional[int] = None


class MoveIn(BaseModel):
    direction: str  # "up" | "down"


class CopyDayIn(BaseModel):
    fromDate: DateStr
    toDate: DateStr


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

ITEM_SORT = " ORDER BY (start_time IS NULL), start_time, sort_order, id"


def _row_to_item(row: dict) -> dict:
    out = dict(row)
    out["cost"] = float(out["cost"]) if out.get("cost") is not None else None
    return out


def _check_trip_date_range(start: str, end: str) -> None:
    try:
        s = date.fromisoformat(start)
        e = date.fromisoformat(end)
    except ValueError:
        raise HTTPException(status_code=422, detail="日期格式应为 YYYY-MM-DD")
    if e < s:
        raise HTTPException(status_code=422, detail="结束日期不能早于开始日期")


def _own_trip(conn: psycopg.Connection, trip_id: int, owner_id: str) -> dict:
    row = conn.execute(
        "SELECT * FROM trips WHERE id = %s AND owner_id = %s", (trip_id, owner_id)
    ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="旅行不存在")
    return row


def _own_item(conn: psycopg.Connection, item_id: int, owner_id: str) -> dict:
    row = conn.execute(
        "SELECT * FROM itinerary_items WHERE id = %s AND owner_id = %s",
        (item_id, owner_id),
    ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="行程不存在")
    return row


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------

app = FastAPI(title="行旅日记")

SECURITY_CSP = "frame-ancestors 'self' https://*.xiaohongshu.com https://*.xhscdn.com"


@app.middleware("http")
async def add_security_headers(request, call_next):
    response = await call_next(request)
    response.headers["content-security-policy"] = SECURITY_CSP
    return response


@app.get("/health")
def health() -> dict:
    return {"ok": True}


@app.get("/")
def index():
    return FileResponse("static/index.html")


app.mount("/static", StaticFiles(directory="static", html=True), name="static")


# ---------------------------------------------------------------------------
# 旅行 CRUD
# ---------------------------------------------------------------------------


@app.get("/api/trips")
def list_trips(
    decrypted_userinfo: Optional[str] = Header(None, alias="Decrypted-Userinfo"),
):
    user = _require_user(decrypted_userinfo)
    with _get_db_conn() as conn:
        rows = conn.execute(
            """
            SELECT t.id, t.name, t.destination, t.start_date, t.end_date,
                   t.cover_image, t.total_budget, t.notes, t.created_at, t.updated_at,
                   COUNT(i.id)                          AS item_count,
                   COUNT(i.id) FILTER (WHERE i.completed) AS done_count,
                   COALESCE(SUM(i.cost), 0)             AS cost_sum
            FROM trips t
            LEFT JOIN itinerary_items i ON i.trip_id = t.id
            WHERE t.owner_id = %s
            GROUP BY t.id
            ORDER BY t.start_date DESC, t.id DESC
            """,
            (user["userId"],),
        ).fetchall()
    out = []
    for r in rows:
        r = dict(r)
        r["costSum"] = float(r.pop("cost_sum") or 0)
        out.append(r)
    return {"trips": out}


@app.post("/api/trips", status_code=201)
def create_trip(
    body: TripCreate,
    decrypted_userinfo: Optional[str] = Header(None, alias="Decrypted-Userinfo"),
):
    user = _require_user(decrypted_userinfo)
    _check_trip_date_range(body.startDate, body.endDate)
    with _get_db_conn() as conn:
        row = conn.execute(
            """
            INSERT INTO trips (owner_id, name, destination, start_date, end_date,
                               cover_image, total_budget, notes)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING *
            """,
            (
                user["userId"], body.name, body.destination,
                body.startDate, body.endDate,
                body.coverImage, body.totalBudget, body.notes,
            ),
        ).fetchone()
        conn.commit()
    return row


def _trip_summary(conn: psycopg.Connection, trip_id: int) -> dict:
    """每日摘要 + 类型汇总（概览页 / 日历页角标用）。"""
    days = conn.execute(
        """
        SELECT date,
               COUNT(*)                            AS item_count,
               COUNT(*) FILTER (WHERE completed)   AS done_count,
               COALESCE(SUM(cost), 0)              AS cost_sum,
               json_agg(DISTINCT type)             AS types
        FROM itinerary_items
        WHERE trip_id = %s
        GROUP BY date
        ORDER BY date
        """,
        (trip_id,),
    ).fetchall()
    by_type = conn.execute(
        """
        SELECT type, COUNT(*) AS cnt, COALESCE(SUM(cost), 0) AS cost_sum
        FROM itinerary_items
        WHERE trip_id = %s
        GROUP BY type
        """,
        (trip_id,),
    ).fetchall()
    return {
        "days": [
            {
                "date": str(d["date"]),
                "itemCount": d["item_count"],
                "doneCount": d["done_count"],
                "costSum": float(d["cost_sum"] or 0),
                "types": d["types"],
            }
            for d in days
        ],
        "byType": [
            {"type": t["type"], "count": t["cnt"], "costSum": float(t["cost_sum"] or 0)}
            for t in by_type
        ],
    }


@app.get("/api/trips/{trip_id}")
def get_trip(
    trip_id: int,
    decrypted_userinfo: Optional[str] = Header(None, alias="Decrypted-Userinfo"),
):
    user = _require_user(decrypted_userinfo)
    with _get_db_conn() as conn:
        trip = _own_trip(conn, trip_id, user["userId"])
        summary = _trip_summary(conn, trip_id)
    trip["totalBudget"] = float(trip["totalBudget"]) if trip["totalBudget"] is not None else None
    return {"trip": trip, **summary}


@app.put("/api/trips/{trip_id}")
def update_trip(
    trip_id: int,
    body: TripUpdate,
    decrypted_userinfo: Optional[str] = Header(None, alias="Decrypted-Userinfo"),
):
    user = _require_user(decrypted_userinfo)
    with _get_db_conn() as conn:
        trip = _own_trip(conn, trip_id, user["userId"])
        new_start = body.startDate or str(trip["start_date"])
        new_end = body.endDate or str(trip["end_date"])
        _check_trip_date_range(new_start, new_end)
        row = conn.execute(
            """
            UPDATE trips SET
                name        = COALESCE(%s, name),
                destination = COALESCE(%s, destination),
                start_date  = %s,
                end_date    = %s,
                cover_image = COALESCE(%s, cover_image),
                total_budget = COALESCE(%s, total_budget),
                notes       = COALESCE(%s, notes),
                updated_at  = NOW()
            WHERE id = %s AND owner_id = %s
            RETURNING *
            """,
            (
                body.name, body.destination, new_start, new_end,
                body.coverImage,
                body.totalBudget if body.totalBudget is not None else trip["total_budget"],
                body.notes, trip_id, user["userId"],
            ),
        ).fetchone()
        conn.commit()
    row["totalBudget"] = float(row["totalBudget"]) if row["totalBudget"] is not None else None
    return row


@app.delete("/api/trips/{trip_id}", status_code=204)
def delete_trip(
    trip_id: int,
    decrypted_userinfo: Optional[str] = Header(None, alias="Decrypted-Userinfo"),
) -> Response:
    user = _require_user(decrypted_userinfo)
    with _get_db_conn() as conn:
        _own_trip(conn, trip_id, user["userId"])
        conn.execute("DELETE FROM trips WHERE id = %s AND owner_id = %s",
                     (trip_id, user["userId"]))
        conn.commit()
    return Response(status_code=204)


# ---------------------------------------------------------------------------
# 行程 CRUD
# ---------------------------------------------------------------------------


@app.get("/api/trips/{trip_id}/items")
def list_items(
    trip_id: int,
    date_filter: Optional[str] = None,
    decrypted_userinfo: Optional[str] = Header(None, alias="Decrypted-Userinfo"),
):
    user = _require_user(decrypted_userinfo)
    with _get_db_conn() as conn:
        _own_trip(conn, trip_id, user["userId"])
        if date_filter:
            rows = conn.execute(
                "SELECT * FROM itinerary_items WHERE trip_id = %s AND date = %s"
                f" {ITEM_SORT}",
                (trip_id, date_filter),
            ).fetchall()
        else:
            rows = conn.execute(
                f"SELECT * FROM itinerary_items WHERE trip_id = %s {ITEM_SORT}",
                (trip_id,),
            ).fetchall()
    return {"items": [_row_to_item(r) for r in rows]}


@app.post("/api/trips/{trip_id}/items", status_code=201)
def create_item(
    trip_id: int,
    body: ItemIn,
    decrypted_userinfo: Optional[str] = Header(None, alias="Decrypted-Userinfo"),
):
    user = _require_user(decrypted_userinfo)
    with _get_db_conn() as conn:
        _own_trip(conn, trip_id, user["userId"])
        row = conn.execute(
            """
            INSERT INTO itinerary_items
                (trip_id, owner_id, date, start_time, end_time, type, title,
                 location, address, transport, cost, precautions, notes,
                 extra, images, completed, sort_order)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING *
            """,
            (
                trip_id, user["userId"], body.date,
                body.startTime or None, body.endTime or None, body.type, body.title,
                body.location or None, body.address or None, body.transport or None,
                body.cost, body.precautions or None, body.notes or None,
                json.dumps(body.extra, ensure_ascii=False),
                json.dumps(body.images, ensure_ascii=False),
                body.completed, body.sortOrder,
            ),
        ).fetchone()
        conn.commit()
    return _row_to_item(row)


@app.put("/api/items/{item_id}")
def update_item(
    item_id: int,
    body: ItemPatch,
    decrypted_userinfo: Optional[str] = Header(None, alias="Decrypted-Userinfo"),
):
    user = _require_user(decrypted_userinfo)
    with _get_db_conn() as conn:
        cur = _own_item(conn, item_id, user["userId"])
        row = conn.execute(
            """
            UPDATE itinerary_items SET
                date        = COALESCE(%s, date),
                start_time  = %s,
                end_time    = %s,
                type        = COALESCE(%s, type),
                title       = COALESCE(%s, title),
                location    = %s,
                address     = %s,
                transport   = %s,
                cost        = %s,
                precautions = %s,
                notes       = %s,
                extra       = COALESCE(%s, extra),
                images      = COALESCE(%s, images),
                completed   = COALESCE(%s, completed),
                sort_order  = COALESCE(%s, sort_order),
                updated_at  = NOW()
            WHERE id = %s AND owner_id = %s
            RETURNING *
            """,
            (
                body.date,
                body.startTime if body.startTime is not None else cur["start_time"],
                body.endTime if body.endTime is not None else cur["end_time"],
                body.type, body.title,
                body.location if body.location is not None else cur["location"],
                body.address if body.address is not None else cur["address"],
                body.transport if body.transport is not None else cur["transport"],
                body.cost if body.cost is not None else cur["cost"],
                body.precautions if body.precautions is not None else cur["precautions"],
                body.notes if body.notes is not None else cur["notes"],
                json.dumps(body.extra, ensure_ascii=False) if body.extra is not None else None,
                json.dumps(body.images, ensure_ascii=False) if body.images is not None else None,
                body.completed, body.sortOrder, item_id, user["userId"],
            ),
        ).fetchone()
        conn.commit()
    return _row_to_item(row)


@app.delete("/api/items/{item_id}", status_code=204)
def delete_item(
    item_id: int,
    decrypted_userinfo: Optional[str] = Header(None, alias="Decrypted-Userinfo"),
) -> Response:
    user = _require_user(decrypted_userinfo)
    with _get_db_conn() as conn:
        _own_item(conn, item_id, user["userId"])
        conn.execute("DELETE FROM itinerary_items WHERE id = %s AND owner_id = %s",
                     (item_id, user["userId"]))
        conn.commit()
    return Response(status_code=204)


@app.post("/api/items/{item_id}/move")
def move_item(
    item_id: int,
    body: MoveIn,
    decrypted_userinfo: Optional[str] = Header(None, alias="Decrypted-Userinfo"),
):
    """在同一天内上移/下移：与相邻项交换 sort_order。"""
    user = _require_user(decrypted_userinfo)
    with _get_db_conn() as conn:
        cur = _own_item(conn, item_id, user["userId"])
        rows = conn.execute(
            f"SELECT id, sort_order FROM itinerary_items"
            f" WHERE trip_id = %s AND date = %s{ITEM_SORT}",
            (cur["trip_id"], cur["date"]),
        ).fetchall()
        ids = [r["id"] for r in rows]
        if item_id not in ids or len(ids) < 2:
            return {"ok": True}
        idx = ids.index(item_id)
        if body.direction == "up" and idx == 0:
            return {"ok": True}
        if body.direction == "down" and idx == len(ids) - 1:
            return {"ok": True}
        other_id = ids[idx - 1] if body.direction == "up" else ids[idx + 1]
        cur_order = rows[idx]["sort_order"]
        other_order = rows[idx - 1]["sort_order"] if body.direction == "up" else rows[idx + 1]["sort_order"]
        with conn.transaction():
            conn.execute("UPDATE itinerary_items SET sort_order = %s WHERE id = %s",
                         (other_order, item_id))
            conn.execute("UPDATE itinerary_items SET sort_order = %s WHERE id = %s",
                         (cur_order, other_id))
            # 若两者 sort_order 相同，交换后无效，则强制拉开
            if cur_order == other_order:
                conn.execute("UPDATE itinerary_items SET sort_order = %s WHERE id = %s",
                             (cur_order - 1 if body.direction == "up" else cur_order + 1, item_id))
        conn.commit()
    return {"ok": True}


@app.post("/api/trips/{trip_id}/copy-day", status_code=201)
def copy_day(
    trip_id: int,
    body: CopyDayIn,
    decrypted_userinfo: Optional[str] = Header(None, alias="Decrypted-Userinfo"),
):
    """把 fromDate 的全部行程复制到 toDate（保留时间/类型，completed 重置为未完成）。"""
    user = _require_user(decrypted_userinfo)
    with _get_db_conn() as conn:
        _own_trip(conn, trip_id, user["userId"])
        rows = conn.execute(
            f"SELECT * FROM itinerary_items WHERE trip_id = %s AND date = %s{ITEM_SORT}",
            (trip_id, body.fromDate),
        ).fetchall()
        copied = 0
        with conn.transaction():
            for r in rows:
                conn.execute(
                    """
                    INSERT INTO itinerary_items
                        (trip_id, owner_id, date, start_time, end_time, type, title,
                         location, address, transport, cost, precautions, notes,
                         extra, images, completed, sort_order)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, FALSE, %s)
                    """,
                    (
                        trip_id, user["userId"], body.toDate,
                        r["start_time"], r["end_time"], r["type"], r["title"],
                        r["location"], r["address"], r["transport"], r["cost"],
                        r["precautions"], r["notes"],
                        json.dumps(r["extra"], ensure_ascii=False) if r["extra"] else "{}",
                        json.dumps(r["images"], ensure_ascii=False) if r["images"] else "[]",
                        copied,
                    ),
                )
                copied += 1
        conn.commit()
    return {"copied": copied}


# ---------------------------------------------------------------------------
# 图片上传（PG Large Object）
# ---------------------------------------------------------------------------

MAX_UPLOAD_BYTES = 8 * 1024 * 1024
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif", "image/heic", "image/jpg"}


@app.post("/api/upload")
def upload_image(
    file: UploadFile = File(...),
    decrypted_userinfo: Optional[str] = Header(None, alias="Decrypted-Userinfo"),
):
    user = _require_user(decrypted_userinfo)
    if (file.content_type or "") not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(status_code=422, detail="仅支持 jpg / png / webp / gif / heic 图片")
    blob = file.file.read()
    if len(blob) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=422, detail="图片不能超过 8MB")
    with _get_db_conn() as conn:
        oid = conn.execute("SELECT lo_create(0)").fetchone()["lo_create"]
        with conn.transaction():
            lo = conn.lobject(oid, "wb")
            lo.write(blob)
            lo.close()
            row = conn.execute(
                """
                INSERT INTO trip_files (owner_id, filename, content_type, oid, size)
                VALUES (%s, %s, %s, %s, %s) RETURNING id
                """,
                (user["userId"], file.filename or "image", file.content_type, oid, len(blob)),
            ).fetchone()
        conn.commit()
    return {"id": row["id"], "url": f"/api/files/{row['id']}"}


@app.get("/api/files/{file_id}")
def get_file(
    file_id: int,
    decrypted_userinfo: Optional[str] = Header(None, alias="Decrypted-Userinfo"),
):
    user = _require_user(decrypted_userinfo)
    with _get_db_conn() as conn:
        row = conn.execute(
            "SELECT filename, content_type, oid, size FROM trip_files"
            " WHERE id = %s AND owner_id = %s",
            (file_id, user["userId"]),
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="文件不存在")
        lo = conn.lobject(row["oid"], "rb")
        blob = lo.read()
        lo.close()
    return Response(
        content=blob,
        media_type=row["content_type"] or "application/octet-stream",
        headers={"Cache-Control": "private, max-age=86400"},
    )
