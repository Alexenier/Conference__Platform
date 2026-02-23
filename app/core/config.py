from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "Conference Platform"
    debug: bool = True

    database_url: str

    s3_endpoint: str
    s3_access_key: str
    s3_secret_key: str
    s3_bucket: str
    s3_region: str = "us-east-1"

    class Config:
        env_file = ".env"


settings = Settings()
