import json
import ibm_db
import ibm_db_dbi
import pandas as pd
from pathlib import Path


def load_credentials(path: str = "config/credentials.json") -> dict:
    creds_path = Path(path)
    if not creds_path.exists():
        raise FileNotFoundError(
            f"Credentials not found at {path}. Copy config/credentials_template.json "
            "to config/credentials.json and fill in your IBM Cloud DB2 details."
        )
    with open(creds_path) as f:
        return json.load(f)["db2"]


def build_dsn(creds: dict) -> str:
    return (
        f"DATABASE={creds['database']};"
        f"HOSTNAME={creds['hostname']};"
        f"PORT={creds['port']};"
        f"PROTOCOL=TCPIP;"
        f"UID={creds['username']};"
        f"PWD={creds['password']};"
        f"Security=SSL;"
    )


class DB2Connector:
    def __init__(self, credentials_path: str = "config/credentials.json"):
        creds = load_credentials(credentials_path)
        dsn = build_dsn(creds)
        self._conn_ibm = ibm_db.connect(dsn, "", "")
        self._conn_dbi = ibm_db_dbi.Connection(self._conn_ibm)

    def execute(self, sql: str) -> None:
        ibm_db.exec_immediate(self._conn_ibm, sql)

    def query(self, sql: str) -> pd.DataFrame:
        return pd.read_sql(sql, self._conn_dbi)

    def insert_dataframe(self, df: pd.DataFrame, table: str, batch_size: int = 5000) -> None:
        cols = ", ".join(df.columns)
        placeholders = ", ".join(["?" for _ in df.columns])
        sql = f"INSERT INTO {table} ({cols}) VALUES ({placeholders})"
        stmt = ibm_db.prepare(self._conn_ibm, sql)

        # Normalize to native Python types (ibm_db cannot bind numpy scalars).
        # Booleans -> int so they map cleanly to SMALLINT columns.
        df_native = df.copy()
        bool_cols = df_native.select_dtypes(include="bool").columns
        if len(bool_cols):
            df_native[bool_cols] = df_native[bool_cols].astype("int64")
        rows = df_native.astype(object).where(pd.notnull(df_native), None).values.tolist()

        # execute_many batches each chunk into a single server round-trip — orders of
        # magnitude faster than per-row ibm_db.execute over the network.
        for i in range(0, len(rows), batch_size):
            batch = tuple(tuple(r) for r in rows[i : i + batch_size])
            ibm_db.execute_many(stmt, batch)
            print(f"  Inserted rows {i} – {min(i + batch_size, len(rows))}")

    def close(self) -> None:
        ibm_db.close(self._conn_ibm)

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()
