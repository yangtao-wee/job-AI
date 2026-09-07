import gzip
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKUP_DIR = ROOT / 'backups'
KEEP = 7


def load_env(path: Path) -> dict:
    data = {}
    if not path.exists():
        return data
    for line in path.read_text(encoding='utf-8').splitlines():
        line = line.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        key, value = line.split('=', 1)
        data[key.strip()] = value.strip()
    return data

def dump_mysql(env: dict, out: Path) -> None:
    user = env.get('MYSQL_USER')
    password = env.get('MYSQL_PASSWORD')
    database = env.get('MYSQL_DATABASE')
    if not (user and password and database):
        sys.exit('缺少 MYSQL_USER / MYSQL_PASSWORD / MYSQL_DATABASE')
    cmd = [
        'docker', 'compose', 'exec', '-T',
        '-e', f'MYSQL_PWD={password}',
        'mysql',
        'mysqldump', '-u', user, '--single-transaction', database,
    ]
    with out.open('wb') as f:
        result = subprocess.run(cmd, cwd=ROOT, stdout=f, stderr=subprocess.PIPE)
    if result.returncode != 0:
        out.unlink(missing_ok=True)
        sys.exit(f'导出失败：{result.stderr.decode(errors="replace")[:300]}')

def prune(pattern: str) -> None:
    files = sorted(BACKUP_DIR.glob(pattern))
    for old in files[:-KEEP]:
        old.unlink()
        print(f'删除旧备份 {old.name}')


def main() -> None:
    BACKUP_DIR.mkdir(exist_ok=True)
    env = load_env(ROOT / '.env')
    stamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    raw = BACKUP_DIR / f'mysql_{stamp}.sql'
    dump_mysql(env, raw)
    gz = raw.with_suffix('.sql.gz')
    with raw.open('rb') as src, gzip.open(gz, 'wb') as dst:
        shutil.copyfileobj(src, dst)
    raw.unlink()
    print(f'备份完成 {gz.name}  {gz.stat().st_size // 1024} KB')
    prune('mysql_*.sql.gz')


if __name__ == '__main__':
    main()