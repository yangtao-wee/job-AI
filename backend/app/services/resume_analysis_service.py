from sqlalchemy.orm import Session
from ..models import ResumeAnalysis
from  ..schemas import ResumeAIAnalysis

def save_resume_analysis(
        db:Session,
        analysis:ResumeAIAnalysis
)->ResumeAnalysis:
    record=(
        db.query(ResumeAnalysis)
        .filter(
            ResumeAnalysis.resume_id==analysis.resume_id
        )
        .first()
    )
    if not record:
        record = ResumeAnalysis(
            resume_id=analysis.resume_id
        )
        db.add(record)
    record.summary = analysis.summary
    record.skills = analysis.skills
    record.strengths = analysis.strengths
    record.improvement_suggestions=(
        analysis.improvement_suggestions
    )
    record.recommended_positions=(
        analysis.recommended_positions
    )
    db.commit()
    db.refresh(record)
    return record