from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="LEITNER_", env_file=".env")

    data_dir: Path = Path("/data")
    db_path: Path | None = None
    blob_dir: Path | None = None
    edit_dir: Path | None = None

    vapid_public_key: str = ""
    vapid_private_key: str = ""
    vapid_subject: str = "mailto:admin@gcourtot.fr"

    reminder_check_interval_minutes: int = 5

    @property
    def resolved_db_path(self) -> Path:
        return self.db_path or self.data_dir / "leitner.db"

    @property
    def resolved_blob_dir(self) -> Path:
        return self.blob_dir or self.data_dir / "blobs"

    @property
    def resolved_edit_dir(self) -> Path:
        return self.edit_dir or self.data_dir / "edit"


settings = Settings()
