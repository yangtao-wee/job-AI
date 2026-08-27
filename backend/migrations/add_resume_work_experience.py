from sqlalchemy import inspect
from app.database import engine

columns = {
    column['name']
    for column in inspect(engine).get_columns('resume_analyses')
}
if 'work_experience' not in columns:
    with engine.begin() as connection:
        connection.exec_driver_sql(
            "ALTER TABLE resume_analyses ADD COLUMN work_experience JSON NOT NULL DEFAULT '[]'"
        )
print('工作经历字段已准备')