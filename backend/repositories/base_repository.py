"""
Base Repository Pattern - PostgreSQL JSONB adaptörü üzerinde çalışır.
"""
from typing import Dict, List, Optional, Any
from config.database import db as _global_db


class BaseRepository:
    def __init__(self, collection_name: str, db=None):
        self.db = db or _global_db
        self.collection = self.db[collection_name]
        self.collection_name = collection_name

    async def find_one(self, query: Dict, projection: Optional[Dict] = None) -> Optional[Dict]:
        return await self.collection.find_one(query, projection or {"_id": 0})

    async def find_many(self, query: Dict, projection: Optional[Dict] = None,
                        limit: int = 100, skip: int = 0, sort: Optional[List] = None) -> List[Dict]:
        cursor = self.collection.find(query, projection or {"_id": 0})
        if sort:
            cursor = cursor.sort(sort)
        if skip > 0:
            cursor = cursor.skip(skip)
        if limit > 0:
            cursor = cursor.limit(limit)
        return await cursor.to_list(length=None)

    async def insert_one(self, document: Dict) -> str:
        result = await self.collection.insert_one(document)
        return str(result.inserted_id)

    async def insert_many(self, documents: List[Dict]) -> List[str]:
        ids = []
        for doc in documents:
            result = await self.collection.insert_one(doc)
            ids.append(str(result.inserted_id))
        return ids

    async def update_one(self, query: Dict, update: Dict) -> bool:
        result = await self.collection.update_one(query, {"$set": update})
        return result.modified_count > 0

    async def update_many(self, query: Dict, update: Dict) -> int:
        result = await self.collection.update_many(query, {"$set": update})
        return result.modified_count

    async def delete_one(self, query: Dict) -> bool:
        result = await self.collection.delete_one(query)
        return result.deleted_count > 0

    async def delete_many(self, query: Dict) -> int:
        result = await self.collection.delete_many(query)
        return result.deleted_count

    async def count(self, query: Dict = {}) -> int:
        return await self.collection.count_documents(query)

    async def exists(self, query: Dict) -> bool:
        return await self.collection.count_documents(query) > 0


def get_database():
    return _global_db
