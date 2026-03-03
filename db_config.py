# # import asyncpg
# # from typing import Optional

# # _pool: Optional[asyncpg.Pool] = None


# # async def get_pool() -> asyncpg.Pool:
# #     global _pool
# #     if _pool is None:
# #         _pool = await asyncpg.create_pool(
# #             user="postgres",
# #             password="testpass123",
# #             database="employees",
# #             host="localhost",
# #             port=5432,
# #             min_size=1,
# #             max_size=10,
# #         )
# #     return _pool

# # async def close_pool():
# #     global _pool
# #     if _pool and not _pool._closed:
# #         await _pool.close()
# #         _pool = None

# # async def execute(query: str, *args):
# #     pool = await get_pool()
# #     async with pool.acquire() as conn:
# #         return await conn.execute(query, *args)


# # async def fetch(query: str, *args):
# #     pool = await get_pool()
# #     async with pool.acquire() as conn:
# #         return await conn.fetch(query, *args)


# # async def fetchrow(query: str, *args):
# #     pool = await get_pool()
# #     async with pool.acquire() as conn:
# #         return await conn.fetchrow(query, *args)



# import aioodbc
# from typing import Optional, Any, Sequence

# _pool: Optional[aioodbc.pool.Pool] = None


# async def get_pool() -> aioodbc.pool.Pool:
#     """
#     Initialize (or return) a global aioodbc connection pool for Azure SQL.
#     """
#     global _pool
#     if _pool is None:
#         # Update these values with your Azure SQL details
#         server = "upsdatabase.database.windows.net"
#         database = "upslandb"
#         username = "Mangesh"
#         password = "Techm@2026"

#         # ODBC connection string for Azure SQL (Driver 18 recommended)
#         dsn = (
#             "{ODBC Driver 17 for SQL Server};"
#             f"Server=tcp:{server},1433;"
#             f"Database={database};"
#             f"Uid={username};"
#             f"Pwd={password};"
#             "Encrypt=yes;"
#             "TrustServerCertificate=no;"
#             "Connection Timeout=30;"
#         )

#         # Create a pool; tweak minsize/maxsize to your workload
#         _pool = await aioodbc.create_pool(
#             dsn=dsn,
#             minsize=1,
#             maxsize=10,
#             autocommit=True,  # mimic asyncpg.execute() autocommit behavior
#         )
#     return _pool


# async def close_pool():
#     """
#     Gracefully close the pool (if open).
#     """
#     global _pool
#     if _pool is not None and not _pool.closed:
#         _pool.close()
#         await _pool.wait_closed()
#         _pool = None


# async def execute(query: str, *args: Any):
#     """
#     Execute a non-SELECT statement (INSERT/UPDATE/DELETE/DDL).
#     Returns the rowcount (to be close to asyncpg's 'execute' semantics).
#     """
#     pool = await get_pool()
#     async with pool.acquire() as conn:
#         async with conn.cursor() as cur:
#             # SQL Server uses '?' placeholders
#             await cur.execute(query, args if args else None)
#             # rowcount is best-effort (may be -1 for some statements)
#             return cur.rowcount


# async def fetch(query: str, *args: Any):
#     """
#     Run a SELECT returning multiple rows.
#     Returns a list of dicts (column -> value) for convenience.
#     """
#     pool = await get_pool()
#     async with pool.acquire() as conn:
#         # DictCursor gives row as mapping; if not available, we convert manually
#         async with conn.cursor() as cur:
#             await cur.execute(query, args if args else None)
#             columns = [desc[0] for desc in cur.description] if cur.description else []
#             rows = await cur.fetchall()
#             # convert tuples to dicts keyed by column name
#             return [dict(zip(columns, row)) for row in rows]


# async def fetchrow(query: str, *args: Any):
#     """
#     Run a SELECT returning a single row.
#     Returns a dict (column -> value) or None if no row.
#     """
#     pool = await get_pool()
#     async with pool.acquire() as conn:
#         async with conn.cursor() as cur:
#             await cur.execute(query, args if args else None)
#             row = await cur.fetchone()
#             if row is None:
#                 return None
#             columns = [desc[0] for desc in cur.description] if cur.description else []
#             return dict(zip(columns, row))


import os
import aioodbc
import pyodbc  # for drivers() check
from typing import Optional, Any, List, Dict

_pool: Optional[aioodbc.pool.Pool] = None

SQL_SERVER = "upsdatabase.database.windows.net"
SQL_DB     = "upslandb"         # e.g., "MyDbName"
SQL_USER   = "Mangesh"         # e.g., "myuser@mytenant"
SQL_PASS   = "Techm@2026"       # e.g., "myp@ssw0rd!"

def _ensure_driver():
    drivers = [d.lower() for d in pyodbc.drivers()]
    if "odbc driver 17 for sql server" not in drivers:
        raise RuntimeError(
            "Required driver 'ODBC Driver 17 for SQL Server' not found. "
            "Install the 64-bit Microsoft ODBC Driver 18 for SQL Server and retry."
        )

async def close_pool():
    global _pool
    if _pool is not None:
        _pool.close()
        await _pool.wait_closed()
        _pool = None

async def execute_sql(sqlQuery: str) -> List[Dict[str, Any]]:
    pool = await get_pool()
 
    async with pool.acquire() as conn:
        async with conn.cursor() as cursor:
            await cursor.execute(sqlQuery)
 
            if cursor.description:  # SELECT query
                columns = [col[0] for col in cursor.description]
                rows = await cursor.fetchall()
                return [dict(zip(columns, row)) for row in rows]
 
            return []
# def _build_dsn() -> str:
#     # If you use Azure AD instead of SQL auth, see the note below
#     return (
#         "Driver={ODBC Driver 17 for SQL Server};"
#         f"Server=tcp:{SQL_SERVER},1433;"
#         f"Database={SQL_DB};"
#         f"Uid={SQL_USER};"
#         f"Pwd={SQL_PASS};"
#         "Encrypt=yes;"
#         "TrustServerCertificate=no;"
#         "Connection Timeout=30;"
#     )
def _build_dsn() -> str:
    # Valid for Microsoft ODBC Driver 17 for SQL Server (Azure SQL compatible)
    return (
        "Driver={ODBC Driver 17 for SQL Server};"
        f"Server={SQL_SERVER},1433;"
        f"Database={SQL_DB};"
        f"UID={SQL_USER};"
        f"PWD={SQL_PASS};"
        "Encrypt=yes;"                 # recommended for Azure SQL
        "TrustServerCertificate=no;"   # Azure's certs are trusted
    )

async def get_pool() -> aioodbc.pool.Pool:
    global _pool
    if _pool is None:
        _ensure_driver()
        missing = [k for k, v in {
            "AZSQL_DATABASE": SQL_DB,
            "AZSQL_USERNAME": SQL_USER,
            "AZSQL_PASSWORD": SQL_PASS
        }.items() if not v]
        if missing:
            raise RuntimeError(
                f"Missing required env vars: {', '.join(missing)}. "
                "Set them or hardcode values before connecting."
            )

        dsn = _build_dsn()
        _pool = await aioodbc.create_pool(
            dsn=dsn,
            minsize=1,
            maxsize=10,
            autocommit=True,
        )
    return _pool

async def execute(query: str, *args: Any):
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(query, *args)  # <-- spread args
            return cur.rowcount

async def fetch(query: str, *args: Any):
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(query, *args)  # <-- spread args
            columns = [d[0] for d in cur.description] if cur.description else []
            rows = await cur.fetchall()
            return [dict(zip(columns, row)) for row in rows]

async def fetchrow(query: str, *args: Any):
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(query, *args)  # <-- spread args
            row = await cur.fetchone()
            if row is None:
                return None
            columns = [d[0] for d in cur.description] if cur.description else []
            return dict(zip(columns, row))