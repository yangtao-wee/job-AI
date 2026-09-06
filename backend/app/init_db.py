from .database import SessionLocal, engine
from .models import Base, Job

JOBS = [
    {
        'title': 'Python开发工程师',
        'company': '深圳AI科技公司',
        'salary': '15-20K',
        'location': '深圳',
        'skills': 'Python,FastAPI,RAG,MySQL,Redis,Docker,AI',
        'description': (
            '负责使用Python和FastAPI开发AI求职Agent；'
            '负责接入RAG检索能力；'
            '使用MySQL保存数据；使用Redis缓存结果；'
            '通过Docker部署系统。'
        )
    },
    {
        'title': 'Vue前端工程师',
        'company': '互联网公司',
        'salary': '12-18K',
        'location': '广州',
        'skills': 'Vue,JavaScript,CSS',
        'description': (
            '负责使用Vue开发招聘系统前端页面；'
            '使用JavaScript实现页面交互；'
            '使用CSS完成响应式布局；'
            '完成组件开发、接口联调和表单校验。'
        )
    },
    {
        'title': 'AI产品经理',
        'company': '人工智能公司',
        'salary': '20-30K',
        'location': '上海',
        'skills': 'AI,产品设计,大模型',
        'description': (
            '负责AI产品需求调研和产品设计；'
            '围绕大模型应用编写需求文档和原型；'
            '协同研发、设计和运营推进产品上线。'
        )
    }
]


def seed_jobs():
    db = SessionLocal()
    try:
        for data in JOBS:
            job = db.query(Job).filter(
                Job.title == data['title'],
                Job.company == data['company']
            ).first()

            if job is None:
                db.add(Job(**data))
                continue

            for name, value in data.items():
                setattr(job, name, value)

        db.commit()
    finally:
        db.close()


if __name__ == '__main__':
    seed_jobs()