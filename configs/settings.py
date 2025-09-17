import os

class Settings:
    def __init__(self):
        self.REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        self.EXPORT_DIR = os.environ.get("EXPORT_DIR", "/exports")
        self.INSTANCE_ID = f"{os.getenv('HOSTNAME','triosdb')}-{os.getpid()}"
        self.LOCK_KEY   = "triosdb:lock"
        self.LOCK_TTL_MS = 10000
        self.RENEW_EVERY = 3

        self.EXPORT_BACKEND = os.getenv("EXPORT_BACKEND", "fs")  # "fs" or "s3"
        self.S3_BUCKET = os.getenv("S3_BUCKET", "")
        self.S3_PREFIX = os.getenv("S3_PREFIX", "exports/")

        self.undo_list_length = 1000

settings = Settings()
