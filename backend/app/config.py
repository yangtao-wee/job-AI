from pathlib import Path
from pydantic_settings import BaseSettings,SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent

class Settings(BaseSettings):
    secret_key:str
    algorithm:str = 'HS256'
    access_token_expire_minutes:int = 60
    llm_api_key:str | None=None
    llm_base_url:str | None=None
    llm_model:str | None=None
    llm_mock_mode:bool=False
    llm_timeout:float=30.0
    # 30.0：一次请求最多等待30秒。
    llm_max_retries:int=2
    # 2：首次请求失败后，最多再重试2次。
    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / '.env',
        env_file_encoding='utf-8'
    )
settings=Settings()