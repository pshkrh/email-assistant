import os
import psycopg2
from psycopg2.extras import RealDictCursor
from config import DB_NAME, USER, PASSWORD, HOST, PORT

DB_CONFIG = {
    "dbname": DB_NAME,
    "user": USER,
    "password": PASSWORD,
    "host": HOST,
    "port": PORT,
}


def get_db_connection():
    # For Cloud Run connecting to Cloud SQL
    if os.environ.get("K_SERVICE"):
        # Cloud SQL connection using Unix socket
        db_socket_dir = os.environ.get("DB_SOCKET_DIR", "/cloudsql")
        instance_connection_name = os.environ.get("INSTANCE_CONNECTION_NAME")

        return psycopg2.connect(
            dbname=DB_NAME,
            user=USER,
            password=PASSWORD,
            host=f"{db_socket_dir}/{instance_connection_name}",
            cursor_factory=RealDictCursor,
        )
    else:
        # Local development connection using TCP
        return psycopg2.connect(
            dbname=DB_NAME,
            user=USER,
            password=PASSWORD,
            host=HOST,
            port=PORT,
            cursor_factory=RealDictCursor,
        )
