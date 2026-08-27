from sqlalchemy import inspect
# inspect：【第三方库SQLAlchemy提供】- 中文是“检查器”。
from app.database import engine

columns = {
    column['name']
    for column in inspect(engine).get_columns('jobs')
    # get_columns获取某张数据库表的所有列信息。
}
if 'description' not in columns:
    with engine.begin() as connection:
        # with：【语言固定】，安全管理数据库连接。安全地使用一次数据库连接，用完自动处理收尾。
        # begin()【第三方库】，开启一次数据库事务。
        # as把 engine.begin() 提供出来的数据库连接对象，保存到变量 connection 里。
        connection.exec_driver_sql(
            # exec_driver_sql=直接执行SQL
            "ALTER TABLE jobs ADD COLUMN description TEXT NOT NULL DEFAULT ''"
        )
        # = 修改 jobs 表，新增 description 列
        # ALTER TABLE修改 jobs 表的结构。ADD COLUMN 增加一列，名字叫 description。
        # TEXT 是数据库字段类型。因为岗位描述可能很长：NOT NULL 这个字段不能是 NULL。
        # DEFAULT新增 description，不能为空；以前那些岗位暂时给空字符串。
if 'desrciption' in columns:
    with engine.begin() as connection:
        connection.exec_driver_sql(
            'ALTER TABLE jobs DROP COLUMN desrciption'
            # DROP COLUMN：【SQL固定】，删除指定字段。
        )
print('岗位描述字段已准备')