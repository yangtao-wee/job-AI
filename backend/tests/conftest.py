import os
from pathlib import Path

project_dir = Path(__file__).resolve().parents[2]
test_db = project_dir / 'tmp' / 'pytest.db'
test_db.parent.mkdir(exist_ok=True)
test_db.unlink(missing_ok=True)
os.environ['DATABASE_URL'] = f"sqlite:///{test_db.as_posix()}"

from alembic import command
from alembic.config import Config

cfg = Config(str(project_dir / 'backend' / 'alembic.ini'))
command.upgrade(cfg, 'head')