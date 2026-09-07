import pytest
from pydantic import ValidationError
from app.config import Settings

@pytest.mark.parametrize('size',[0,201])
def test_page_size_rejects_bad_value(size):
    with pytest.raises(ValidationError):
        Settings(secret_key='test',lead_page_size=size,_env_file=None)

@pytest.mark.parametrize('size',[1,50,200])
def test_page_size_accepts_valid_value(size):
    config=Settings(secret_key='test',lead_page_size=size,_env_file=None)
    assert config.lead_page_size==size