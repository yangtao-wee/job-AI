from openai import OpenAI
from ..config import settings

def get_llm_client()->OpenAI:
    if not settings.llm_api_key:
        raise RuntimeError('未配置 LLM_API_KEY')
    return OpenAI(
        api_key=settings.llm_api_key,
        base_url=settings.llm_base_url or None,
        timeout=settings.llm_timeout,
        max_retries=settings.llm_max_retries
    )