"""
Database Connection Module

This module handles database connectivity for the application.
It provides a function to create database connections that work both in
Cloud Run (using Unix socket) and in local development (using TCP).
"""

import os

import psycopg2
from psycopg2.extras import RealDictCursor

from config import DB_NAME, USER, PASSWORD, HOST, PORT

# Database connection configuration
DB_CONFIG = {
    "dbname": DB_NAME,
    "user": USER,
    "password": PASSWORD,
    "host": HOST,
    "port": PORT,
}


def get_db_connection():
    """
    Get a PostgreSQL database connection.

    Creates a connection to the database using either Unix socket (Cloud Run)
    or TCP (local development) depending on the environment.

    Returns:
        Connection: A psycopg2 database connection with RealDictCursor factory
    """
    # Check if running in Cloud Run
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
