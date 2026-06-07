import os

class Config:
    SECRET_KEY = os.getenv("PIERRES_SECRET_KEY", "dev-pierre-store-secret")

    DB_HOST = os.getenv("PIERRES_DB_HOST", "localhost")
    DB_PORT = int(os.getenv("PIERRES_DB_PORT", "3306"))
    DB_NAME = os.getenv("PIERRES_DB_NAME", "pierres_store")
    DB_USER = os.getenv("PIERRES_DB_USER", "sunmingtao")
    DB_PASSWORD = os.getenv("PIERRES_DB_PASSWORD", "2400310520")