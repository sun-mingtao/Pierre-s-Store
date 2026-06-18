import os

class Config:
    SECRET_KEY = os.getenv("PIERRES_SECRET_KEY")

    DB_HOST = os.getenv("PIERRES_DB_HOST")
    DB_PORT = int(os.getenv("PIERRES_DB_PORT"))
    DB_NAME = os.getenv("PIERRES_DB_NAME")
    DB_USER = os.getenv("PIERRES_DB_USER")
    DB_PASSWORD = os.getenv("PIERRES_DB_PASSWORD")