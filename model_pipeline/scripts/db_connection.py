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
    return psycopg2.connect(**DB_CONFIG, cursor_factory=RealDictCursor)
