"""
PostgreSQL JSONB üzerinde çalışan MongoDB API adaptörü.
motor/AsyncIOMotorClient ile birebir uyumlu interface sağlar.
Tüm dokümanlar JSONB sütununda saklanır — hiçbir şema tanımlamak gerekmez.
"""
import asyncio
import json
import os
import re
from typing import Any, Dict, List, Optional, Union
from datetime import datetime

import asyncpg

# ─── Bağlantı havuzu ──────────────────────────────────────────────────────────
_pool: Optional[asyncpg.Pool] = None

async def _get_pool() -> asyncpg.Pool:
    global _pool
    if _pool is None:
        dsn = os.environ.get("DATABASE_URL", "")
        _pool = await asyncpg.create_pool(dsn, min_size=2, max_size=10)
    return _pool


async def _conn():
    pool = await _get_pool()
    return pool


# ─── Tablo oluşturma ──────────────────────────────────────────────────────────
_created_tables: set = set()

async def _ensure_table(collection: str, conn):
    if collection in _created_tables:
        return
    safe = _safe_name(collection)
    await conn.execute(f"""
        CREATE TABLE IF NOT EXISTS "{safe}" (
            _id BIGSERIAL PRIMARY KEY,
            doc JSONB NOT NULL
        )
    """)
    _created_tables.add(collection)


def _safe_name(name: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_]", "_", name)


# ─── MongoDB Query → SQL WHERE dönüşümü ──────────────────────────────────────

def _build_where(query: Dict, params: List) -> str:
    """MongoDB filter sözlüğünü PostgreSQL WHERE yan cümlesi'ne çevirir."""
    if not query:
        return "TRUE"

    parts = []
    for key, value in query.items():
        if key == "$or":
            sub = " OR ".join(f"({_build_where(c, params)})" for c in value)
            parts.append(f"({sub})")
        elif key == "$and":
            sub = " AND ".join(f"({_build_where(c, params)})" for c in value)
            parts.append(f"({sub})")
        elif isinstance(value, dict) and any(k.startswith("$") for k in value):
            # Operator sorgular: $gte, $lte, $in, $nin, $ne, $exists, $regex
            for op, operand in value.items():
                field_expr = _field_expr(key)
                if op == "$gte":
                    params.append(_cast_value(operand))
                    parts.append(f"({field_expr})::text >= ${len(params)}::text")
                elif op == "$gt":
                    params.append(_cast_value(operand))
                    parts.append(f"({field_expr})::text > ${len(params)}::text")
                elif op == "$lte":
                    params.append(_cast_value(operand))
                    parts.append(f"({field_expr})::text <= ${len(params)}::text")
                elif op == "$lt":
                    params.append(_cast_value(operand))
                    parts.append(f"({field_expr})::text < ${len(params)}::text")
                elif op == "$ne":
                    params.append(json.dumps(_cast_value(operand)))
                    parts.append(f"({field_expr}) IS DISTINCT FROM ${len(params)}::jsonb")
                elif op == "$in":
                    json_vals = [json.dumps(_cast_value(v)) for v in (operand or [])]
                    if not json_vals:
                        parts.append("FALSE")
                    else:
                        placeholders = ", ".join(f"${len(params) + i + 1}::jsonb" for i in range(len(json_vals)))
                        params.extend(json_vals)
                        parts.append(f"({field_expr}) IN ({placeholders})")
                elif op == "$nin":
                    json_vals = [json.dumps(_cast_value(v)) for v in (operand or [])]
                    if not json_vals:
                        parts.append("TRUE")
                    else:
                        placeholders = ", ".join(f"${len(params) + i + 1}::jsonb" for i in range(len(json_vals)))
                        params.extend(json_vals)
                        parts.append(f"({field_expr}) NOT IN ({placeholders})")
                elif op == "$exists":
                    path_parts = key.split(".")
                    if len(path_parts) == 1:
                        if operand:
                            parts.append(f"doc ? '{path_parts[0]}'")
                        else:
                            parts.append(f"NOT (doc ? '{path_parts[0]}')")
                    else:
                        jpath = " -> ".join(f"'{p}'" for p in path_parts[:-1]) + f" ? '{path_parts[-1]}'"
                        if operand:
                            parts.append(f"doc -> {jpath}")
                        else:
                            parts.append(f"NOT (doc -> {jpath})")
                elif op == "$regex":
                    params.append(str(operand))
                    parts.append(f"({field_expr})::text ~* ${len(params)}")
                elif op == "$elemMatch":
                    # Simplified: check if array contains element matching conditions
                    parts.append("TRUE")
        else:
            # Eşitlik sorgusu
            field_expr = _field_expr(key)
            if value is None:
                root_key = key.split(".")[0]
                parts.append(f"({field_expr}) IS NULL OR NOT (doc ? '{root_key}')")
            else:
                params.append(json.dumps(_cast_value(value)))
                parts.append(f"({field_expr}) = ${len(params)}::jsonb")

    return " AND ".join(parts) if parts else "TRUE"


def _field_expr(key: str) -> str:
    """Noktalı MongoDB alan adını PostgreSQL JSONB path ifadesine çevirir."""
    parts = key.split(".")
    if len(parts) == 1:
        return f"doc->'{parts[0]}'"
    path = "->".join(f"'{p}'" for p in parts[:-1])
    return f"doc->{path}->'{parts[-1]}'"


def _cast_value(v):
    if isinstance(v, datetime):
        return v.isoformat()
    return v


# ─── Projeksiyon ──────────────────────────────────────────────────────────────

def _apply_projection(doc: dict, projection: Optional[dict]) -> dict:
    if not projection:
        return doc
    # _id her zaman hariç tut
    include = {k for k, v in projection.items() if v and k != "_id"}
    exclude = {k for k, v in projection.items() if not v}
    if include:
        return {k: v for k, v in doc.items() if k in include}
    if exclude:
        return {k: v for k, v in doc.items() if k not in exclude}
    return doc


# ─── Sıralama ────────────────────────────────────────────────────────────────

def _build_order(sort_spec) -> str:
    if not sort_spec:
        return ""
    if isinstance(sort_spec, str):
        return f'ORDER BY doc->>\'{sort_spec}\' ASC'
    if isinstance(sort_spec, list):
        parts = []
        for field, direction in sort_spec:
            direction_sql = "DESC" if direction == -1 else "ASC"
            parts.append(f"doc->>'{field}' {direction_sql}")
        return "ORDER BY " + ", ".join(parts)
    if isinstance(sort_spec, dict):
        parts = []
        for field, direction in sort_spec.items():
            direction_sql = "DESC" if direction == -1 else "ASC"
            parts.append(f"doc->>'{field}' {direction_sql}")
        return "ORDER BY " + ", ".join(parts)
    return ""


# ─── $set operatörü uygulama ─────────────────────────────────────────────────

def _apply_update_operators(current: dict, update: dict) -> dict:
    result = dict(current)
    
    if "$set" in update:
        for k, v in update["$set"].items():
            _nested_set(result, k, v)
    
    if "$push" in update:
        for k, v in update["$push"].items():
            current_list = _nested_get(result, k) or []
            if not isinstance(current_list, list):
                current_list = []
            current_list.append(v)
            _nested_set(result, k, current_list)
    
    if "$pull" in update:
        for k, v in update["$pull"].items():
            current_list = _nested_get(result, k) or []
            if isinstance(current_list, list):
                result_list = [item for item in current_list if item != v]
                _nested_set(result, k, result_list)
    
    if "$addToSet" in update:
        for k, v in update["$addToSet"].items():
            current_list = _nested_get(result, k) or []
            if not isinstance(current_list, list):
                current_list = []
            if v not in current_list:
                current_list.append(v)
            _nested_set(result, k, current_list)
    
    if "$inc" in update:
        for k, v in update["$inc"].items():
            current_val = _nested_get(result, k) or 0
            _nested_set(result, k, current_val + v)
    
    if "$unset" in update:
        for k in update["$unset"]:
            _nested_delete(result, k)
    
    # update direkt (operatörsüz) ise tüm dokümanı değiştir
    if not any(k.startswith("$") for k in update):
        result.update(update)
    
    return result


def _nested_set(doc: dict, key: str, value):
    parts = key.split(".")
    for part in parts[:-1]:
        if part not in doc or not isinstance(doc[part], dict):
            doc[part] = {}
        doc = doc[part]
    doc[parts[-1]] = value


def _nested_get(doc: dict, key: str):
    parts = key.split(".")
    for part in parts:
        if not isinstance(doc, dict):
            return None
        doc = doc.get(part)
    return doc


def _nested_delete(doc: dict, key: str):
    parts = key.split(".")
    for part in parts[:-1]:
        if not isinstance(doc, dict):
            return
        doc = doc.get(part, {})
    if isinstance(doc, dict):
        doc.pop(parts[-1], None)


# ─── Aggregate Pipeline (temel $match, $group, $sort, $limit, $lookup) ───────

async def _run_aggregate(collection: str, pipeline: List[dict]) -> List[dict]:
    pool = await _get_pool()
    async with pool.acquire() as conn:
        await _ensure_table(collection, conn)
        safe = _safe_name(collection)
        
        # Tüm dokümanları çek, Python'da işle (basit ama işlevsel)
        rows = await conn.fetch(f'SELECT doc FROM "{safe}"')
        docs = [json.loads(r["doc"]) for r in rows]
        
        for stage in pipeline:
            if "$match" in stage:
                filter_dict = stage["$match"]
                docs = [d for d in docs if _py_match(d, filter_dict)]
            
            elif "$sort" in stage:
                sort_spec = stage["$sort"]
                for field, direction in reversed(list(sort_spec.items())):
                    docs.sort(key=lambda d: (d.get(field) or ""), reverse=(direction == -1))
            
            elif "$limit" in stage:
                docs = docs[:stage["$limit"]]
            
            elif "$skip" in stage:
                docs = docs[stage["$skip"]:]
            
            elif "$group" in stage:
                docs = _py_group(docs, stage["$group"])
            
            elif "$project" in stage:
                proj = stage["$project"]
                include = {k for k, v in proj.items() if v and k != "_id"}
                exclude = {k for k, v in proj.items() if not v}
                if include:
                    docs = [{k: d.get(k) for k in include} for d in docs]
                elif exclude:
                    docs = [{k: v for k, v in d.items() if k not in exclude} for d in docs]
            
            elif "$lookup" in stage:
                # Basit lookup desteği
                pass
            
            elif "$unwind" in stage:
                field = stage["$unwind"].lstrip("$")
                new_docs = []
                for d in docs:
                    val = d.get(field)
                    if isinstance(val, list):
                        for item in val:
                            nd = dict(d)
                            nd[field] = item
                            new_docs.append(nd)
                    else:
                        new_docs.append(d)
                docs = new_docs
        
        return docs


def _py_match(doc: dict, query: dict) -> bool:
    """Python içinde MongoDB filter kontrolü."""
    for key, value in query.items():
        if key == "$or":
            if not any(_py_match(doc, c) for c in value):
                return False
        elif key == "$and":
            if not all(_py_match(doc, c) for c in value):
                return False
        elif isinstance(value, dict) and any(k.startswith("$") for k in value):
            doc_val = _nested_get(doc, key)
            for op, operand in value.items():
                if op == "$gte" and not (doc_val is not None and str(doc_val) >= str(operand)):
                    return False
                elif op == "$gt" and not (doc_val is not None and str(doc_val) > str(operand)):
                    return False
                elif op == "$lte" and not (doc_val is not None and str(doc_val) <= str(operand)):
                    return False
                elif op == "$lt" and not (doc_val is not None and str(doc_val) < str(operand)):
                    return False
                elif op == "$ne" and doc_val == operand:
                    return False
                elif op == "$in" and doc_val not in (operand or []):
                    return False
                elif op == "$nin" and doc_val in (operand or []):
                    return False
                elif op == "$exists":
                    exists = _nested_get(doc, key) is not None
                    if operand and not exists:
                        return False
                    if not operand and exists:
                        return False
                elif op == "$regex":
                    if not doc_val or not re.search(str(operand), str(doc_val), re.IGNORECASE):
                        return False
        else:
            doc_val = _nested_get(doc, key)
            if doc_val != value:
                return False
    return True


def _py_group(docs: List[dict], group_spec: dict) -> List[dict]:
    """Basit $group operatörü implementasyonu."""
    id_spec = group_spec.get("_id")
    groups = {}
    
    for doc in docs:
        # Grup anahtarını belirle
        if id_spec is None:
            key = None
        elif isinstance(id_spec, str) and id_spec.startswith("$"):
            field = id_spec[1:]
            key = doc.get(field)
        elif isinstance(id_spec, dict):
            key = tuple(
                (k, doc.get(v[1:]) if isinstance(v, str) and v.startswith("$") else v)
                for k, v in id_spec.items()
            )
        else:
            key = id_spec
        
        key_str = json.dumps(key, default=str)
        if key_str not in groups:
            groups[key_str] = {"_id": key, "_docs": []}
        groups[key_str]["_docs"].append(doc)
    
    result = []
    for group_data in groups.values():
        group_docs = group_data.pop("_docs")
        row = {"_id": group_data["_id"]}
        
        for field, expr in group_spec.items():
            if field == "_id":
                continue
            if not isinstance(expr, dict):
                continue
            op = list(expr.keys())[0]
            val_spec = list(expr.values())[0]
            
            if isinstance(val_spec, str) and val_spec.startswith("$"):
                field_name = val_spec[1:]
                values = [d.get(field_name) for d in group_docs if d.get(field_name) is not None]
            else:
                values = [val_spec] * len(group_docs)
            
            if op == "$sum":
                if isinstance(val_spec, (int, float)):
                    row[field] = val_spec * len(group_docs)
                else:
                    row[field] = sum(float(v or 0) for v in values)
            elif op == "$avg":
                row[field] = (sum(float(v or 0) for v in values) / len(values)) if values else 0
            elif op == "$min":
                row[field] = min((str(v) for v in values), default=None)
            elif op == "$max":
                row[field] = max((str(v) for v in values), default=None)
            elif op == "$first":
                row[field] = values[0] if values else None
            elif op == "$last":
                row[field] = values[-1] if values else None
            elif op == "$push":
                row[field] = values
            elif op == "$addToSet":
                seen = []
                for v in values:
                    if v not in seen:
                        seen.append(v)
                row[field] = seen
        
        result.append(row)
    
    return result


# ─── Collection proxy sınıfı ─────────────────────────────────────────────────

class CollectionProxy:
    def __init__(self, collection_name: str):
        self._col = collection_name

    # --- find_one ---
    async def find_one(self, query: dict = None, projection: dict = None) -> Optional[dict]:
        query = query or {}
        pool = await _get_pool()
        async with pool.acquire() as conn:
            await _ensure_table(self._col, conn)
            params = []
            where = _build_where(query, params)
            safe = _safe_name(self._col)
            row = await conn.fetchrow(
                f'SELECT doc FROM "{safe}" WHERE {where} LIMIT 1',
                *params
            )
            if row is None:
                return None
            doc = json.loads(row["doc"])
            return _apply_projection(doc, projection)

    # --- find (cursor) ---
    def find(self, query: dict = None, projection: dict = None):
        return CursorProxy(self._col, query or {}, projection)

    # --- insert_one ---
    async def insert_one(self, document: dict) -> Any:
        doc = dict(document)
        doc.pop("_id", None)
        pool = await _get_pool()
        async with pool.acquire() as conn:
            await _ensure_table(self._col, conn)
            safe = _safe_name(self._col)
            await conn.execute(
                f'INSERT INTO "{safe}" (doc) VALUES ($1::jsonb)',
                json.dumps(doc, default=str)
            )
        return type("InsertResult", (), {"inserted_id": doc.get("id", "")})()

    # --- update_one ---
    async def update_one(self, query: dict, update: dict, upsert: bool = False) -> Any:
        pool = await _get_pool()
        async with pool.acquire() as conn:
            await _ensure_table(self._col, conn)
            params = []
            where = _build_where(query, params)
            safe = _safe_name(self._col)
            
            row = await conn.fetchrow(
                f'SELECT _id, doc FROM "{safe}" WHERE {where} LIMIT 1',
                *params
            )
            
            if row is None:
                if upsert:
                    # Yeni doküman oluştur
                    new_doc = {}
                    if "$setOnInsert" in update:
                        new_doc.update(update["$setOnInsert"])
                    new_doc = _apply_update_operators(new_doc, update)
                    # Query filtre değerlerini ekle
                    for k, v in query.items():
                        if not k.startswith("$") and not isinstance(v, dict):
                            _nested_set(new_doc, k, v)
                    await conn.execute(
                        f'INSERT INTO "{safe}" (doc) VALUES ($1::jsonb)',
                        json.dumps(new_doc, default=str)
                    )
                return type("UpdateResult", (), {"matched_count": 0, "modified_count": 0})()
            
            row_id = row["_id"]
            current = json.loads(row["doc"])
            updated = _apply_update_operators(current, update)
            
            await conn.execute(
                f'UPDATE "{safe}" SET doc = $1::jsonb WHERE _id = $2',
                json.dumps(updated, default=str), row_id
            )
        return type("UpdateResult", (), {"matched_count": 1, "modified_count": 1})()

    # --- update_many ---
    async def update_many(self, query: dict, update: dict) -> Any:
        pool = await _get_pool()
        async with pool.acquire() as conn:
            await _ensure_table(self._col, conn)
            params = []
            where = _build_where(query, params)
            safe = _safe_name(self._col)
            
            rows = await conn.fetch(
                f'SELECT _id, doc FROM "{safe}" WHERE {where}',
                *params
            )
            count = 0
            for row in rows:
                current = json.loads(row["doc"])
                updated = _apply_update_operators(current, update)
                await conn.execute(
                    f'UPDATE "{safe}" SET doc = $1::jsonb WHERE _id = $2',
                    json.dumps(updated, default=str), row["_id"]
                )
                count += 1
        return type("UpdateResult", (), {"matched_count": count, "modified_count": count})()

    # --- delete_one ---
    async def delete_one(self, query: dict) -> Any:
        pool = await _get_pool()
        async with pool.acquire() as conn:
            await _ensure_table(self._col, conn)
            params = []
            where = _build_where(query, params)
            safe = _safe_name(self._col)
            row = await conn.fetchrow(
                f'SELECT _id FROM "{safe}" WHERE {where} LIMIT 1',
                *params
            )
            if row:
                await conn.execute(f'DELETE FROM "{safe}" WHERE _id = $1', row["_id"])
                return type("DeleteResult", (), {"deleted_count": 1})()
        return type("DeleteResult", (), {"deleted_count": 0})()

    # --- delete_many ---
    async def delete_many(self, query: dict) -> Any:
        pool = await _get_pool()
        async with pool.acquire() as conn:
            await _ensure_table(self._col, conn)
            params = []
            where = _build_where(query, params)
            safe = _safe_name(self._col)
            result = await conn.execute(
                f'DELETE FROM "{safe}" WHERE {where}',
                *params
            )
            count = int(result.split()[-1]) if result else 0
        return type("DeleteResult", (), {"deleted_count": count})()

    # --- count_documents ---
    async def count_documents(self, query: dict = None) -> int:
        query = query or {}
        pool = await _get_pool()
        async with pool.acquire() as conn:
            await _ensure_table(self._col, conn)
            params = []
            where = _build_where(query, params)
            safe = _safe_name(self._col)
            row = await conn.fetchrow(
                f'SELECT COUNT(*) as cnt FROM "{safe}" WHERE {where}',
                *params
            )
            return row["cnt"] if row else 0

    # --- replace_one ---
    async def replace_one(self, query: dict, replacement: dict, upsert: bool = False) -> Any:
        pool = await _get_pool()
        async with pool.acquire() as conn:
            await _ensure_table(self._col, conn)
            params = []
            where = _build_where(query, params)
            safe = _safe_name(self._col)
            row = await conn.fetchrow(
                f'SELECT _id FROM "{safe}" WHERE {where} LIMIT 1',
                *params
            )
            new_doc = dict(replacement)
            new_doc.pop("_id", None)
            if row:
                await conn.execute(
                    f'UPDATE "{safe}" SET doc = $1::jsonb WHERE _id = $2',
                    json.dumps(new_doc, default=str), row["_id"]
                )
                return type("UpdateResult", (), {"matched_count": 1, "modified_count": 1, "upserted_id": None})()
            elif upsert:
                await conn.execute(
                    f'INSERT INTO "{safe}" (doc) VALUES ($1::jsonb)',
                    json.dumps(new_doc, default=str)
                )
        return type("UpdateResult", (), {"matched_count": 0, "modified_count": 0, "upserted_id": None})()

    # --- aggregate ---
    def aggregate(self, pipeline: List[dict]):
        return AggregateCursor(self._col, pipeline)

    # --- find_one_and_update ---
    async def find_one_and_update(self, query: dict, update: dict, return_document=None, upsert: bool = False) -> Optional[dict]:
        await self.update_one(query, update, upsert=upsert)
        return await self.find_one(query)

    # --- distinct ---
    async def distinct(self, field: str, query: dict = None) -> List:
        query = query or {}
        pool = await _get_pool()
        async with pool.acquire() as conn:
            await _ensure_table(self._col, conn)
            params = []
            where = _build_where(query, params)
            safe = _safe_name(self._col)
            rows = await conn.fetch(
                f'SELECT DISTINCT doc->>\'{field}\' as val FROM "{safe}" WHERE {where}',
                *params
            )
            return [r["val"] for r in rows if r["val"] is not None]


# ─── Cursor proxy ─────────────────────────────────────────────────────────────

class CursorProxy:
    def __init__(self, collection: str, query: dict, projection: Optional[dict] = None):
        self._col = collection
        self._query = query
        self._projection = projection
        self._sort_spec = None
        self._limit_val = None
        self._skip_val = None

    def sort(self, key_or_list, direction=None):
        if direction is not None:
            self._sort_spec = [(key_or_list, direction)]
        else:
            self._sort_spec = key_or_list
        return self

    def limit(self, n: int):
        self._limit_val = n
        return self

    def skip(self, n: int):
        self._skip_val = n
        return self

    async def to_list(self, length: int = 1000) -> List[dict]:
        pool = await _get_pool()
        async with pool.acquire() as conn:
            await _ensure_table(self._col, conn)
            params = []
            where = _build_where(self._query, params)
            order = _build_order(self._sort_spec)
            safe = _safe_name(self._col)
            
            limit_clause = f"LIMIT {min(length, self._limit_val or length)}"
            skip_clause = f"OFFSET {self._skip_val}" if self._skip_val else ""
            
            sql = f'SELECT doc FROM "{safe}" WHERE {where} {order} {limit_clause} {skip_clause}'
            rows = await conn.fetch(sql, *params)
            
            docs = [json.loads(r["doc"]) for r in rows]
            if self._projection:
                docs = [_apply_projection(d, self._projection) for d in docs]
            return docs

    def __aiter__(self):
        return self._iter()

    async def _iter(self):
        docs = await self.to_list(10000)
        for doc in docs:
            yield doc


# ─── Aggregate cursor ─────────────────────────────────────────────────────────

class AggregateCursor:
    def __init__(self, collection: str, pipeline: List[dict]):
        self._col = collection
        self._pipeline = pipeline

    async def to_list(self, length: int = 1000) -> List[dict]:
        docs = await _run_aggregate(self._col, self._pipeline)
        return docs[:length]

    def __aiter__(self):
        return self._iter()

    async def _iter(self):
        docs = await self.to_list(10000)
        for doc in docs:
            yield doc


# ─── Database proxy ───────────────────────────────────────────────────────────

class DatabaseProxy:
    def __getitem__(self, collection_name: str) -> CollectionProxy:
        return CollectionProxy(collection_name)

    def __getattr__(self, collection_name: str) -> CollectionProxy:
        return CollectionProxy(collection_name)

    def get_collection(self, name: str) -> CollectionProxy:
        return CollectionProxy(name)


# ─── Client proxy (motor uyumlu) ─────────────────────────────────────────────

class ClientProxy:
    def __getitem__(self, db_name: str) -> DatabaseProxy:
        return DatabaseProxy()

    def close(self):
        global _pool
        if _pool:
            asyncio.create_task(_pool.close())
            _pool = None


# ─── Public API ───────────────────────────────────────────────────────────────

def get_pg_client() -> ClientProxy:
    return ClientProxy()


def get_pg_database() -> DatabaseProxy:
    return DatabaseProxy()
