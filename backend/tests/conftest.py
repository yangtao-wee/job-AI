import os
from pathlib import Path

project_dir = Path(__file__).resolve().parents[2]
test_db = project_dir / 'tmp' / 'pytest.db'
test_db.parent.mkdir(exist_ok=True)
os.environ['DATABASE_URL'] = f"sqlite:///{test_db.as_posix()}"