from pydantic_settings import BaseSettings
import json


class Settings(BaseSettings):
    app_name: str = "Conference Platform"
    debug: bool = True

    database_url: str

    s3_endpoint: str
    s3_access_key: str
    s3_secret_key: str
    s3_bucket: str
    s3_region: str = "us-east-1"

    es_host: str = "http://elasticsearch:9200"

    secret_key: str = "change-me-in-production"
    access_token_expire_minutes: int = 60 * 24

    admin_email: str = "admin@conference.com"
    admin_password: str = "admin123"
    admin_full_name: str = "Адміністратор"

    # ------------------------------------------------------------------
    # Брендинг — змінюється через .env при деплої під іншу організацію
    # ------------------------------------------------------------------
    ministry_text: str = "МІНІСТЕРСТВО ОСВІТИ І НАУКИ УКРАЇНИ"

    institution1_text: str = (
        "Державний заклад\n"
        "«ПІВДЕННОУКРАЇНСЬКИЙ НАЦІОНАЛЬНИЙ\n"
        "ПЕДАГОГІЧНИЙ УНІВЕРСИТЕТ\n"
        "імені К. Д. Ушинського»"
    )

    institution2_text: str = (
        "ОДЕСЬКИЙ НАЦІОНАЛЬНИЙ УНІВЕРСИТЕТ\n"
        "імені І. І. Мечникова"
    )

    conference_city: str = "Одеса"
    conference_location: str = "ОНУ імені І. І. Мечнікова"

    # ------------------------------------------------------------------
    # Метадані секцій у форматі JSON-рядка в .env:
    #
    # SECTION_CONFIGS_JSON='{
    #   "Інтелектуальні системи": {
    #     "heads": ["к. ф-м. н., доцент Пенко Валерій Георгійович"],
    #     "secretary": "ст. викладач Трубіна Наталія Федорівна",
    #     "location": "ОНУ імені І. І. Мечнікова"
    #   }
    # }'
    # ------------------------------------------------------------------
    section_configs_json: str = "{}"

    @property
    def section_configs(self) -> dict:
        try:
            return json.loads(self.section_configs_json)
        except (json.JSONDecodeError, TypeError):
            return {}

    class Config:
        env_file = ".env"


settings = Settings()