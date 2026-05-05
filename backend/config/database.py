"""
PostgreSQL JSONB üzerinde çalışan MongoDB-uyumlu veritabanı katmanı.
motor/AsyncIOMotorClient kullanımını şeffaf biçimde PostgreSQL'e yönlendirir.
"""
from config.pg_mongo_adapter import get_pg_client, get_pg_database, DatabaseProxy

class Database:
    _db: DatabaseProxy = None

    @classmethod
    def get_client(cls):
        return get_pg_client()

    @classmethod
    def get_database(cls) -> DatabaseProxy:
        if cls._db is None:
            cls._db = get_pg_database()
        return cls._db

    @classmethod
    def close_connection(cls):
        pass  # PostgreSQL bağlantı havuzu otomatik yönetilir

db = Database.get_database()
