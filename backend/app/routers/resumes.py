from pathlib import Path
from uuid import uuid4
import aiofiles
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session
from fastapi.responses import FileResponse

from ..dependencies import get_current_user, get_db
from ..models import Resume, User
from ..schemas import ResumeResponse
from ..services.resume_parser import extract_pdf_text
from ..services.ai_resume_service import analyze_resume_with_ai
from ..services.resume_analysis_service import save_resume_analysis
router = APIRouter()
ALLOWED_CONTENT_TYPES = {
    'application/pdf',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
}
ALLOWED_EXTENSIONS = {
    '.pdf',
    '.docx'
}
MAX_FILE_SIZE = 5 * 1024 * 1024
UPLOAD_DIR = Path(__file__).resolve().parents[2]/'uploads'/'resumes'
CHUNK_SIZE = 1024 * 1024
@router.post('/upload')
async def upload_resume(
    file:UploadFile=File(...),
    current_user:User = Depends(get_current_user),
    db:Session = Depends(get_db)
):
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise  HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail='仅支持 PDF 或 DOCX 简历'
        )
    file_extension = Path(file.filename or '').suffix.lower()
    if file_extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail='简历扩展名必须是 .pdf或 .docx'
        )
    if file.size is not None and file.size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail='简历文件不能超过5MB'
        )
    UPLOAD_DIR.mkdir(parents=True,exist_ok=True)
    stored_filename = f'{current_user.id}_{uuid4().hex}{file_extension}'
    file_path = UPLOAD_DIR / stored_filename
    async with aiofiles.open(file_path,'wb') as output_file:
        while True:
            chunk = await file.read(CHUNK_SIZE)
            if not chunk:
                break
            await output_file.write(chunk)
    resume_record = Resume(
        user_id = current_user.id,
        original_filename=file.filename,
        stored_filename=stored_filename,
        content_type=file.content_type,
        file_size=file.size or 0
        )
    db.add(resume_record)
    db.commit()
    db.refresh(resume_record)
    return{
        'resume_id':resume_record.id,
        'filename':file.filename,
        'stored_filename':stored_filename,
        'content_type':file.content_type,
        'user_id':current_user.id,
        'created_at':resume_record.created_at

    }

@router.get('/me',response_model=list[ResumeResponse])
def get_my_resumes(
    current_user:User = Depends(get_current_user),
    db:Session = Depends(get_db)
):
    return(
        db.query(Resume)
        .filter(Resume.user_id == current_user.id)
        .order_by(Resume.created_at.desc(),Resume.id.desc())
        .all()
    )

@router.delete('/{resume_id}',
status_code=status.HTTP_204_NO_CONTENT)
def delete_resume(
    resume_id:int,
    current_user:User = Depends(get_current_user),
    db:Session = Depends(get_db)
):
    resume_record=(
        db.query(Resume)
        .filter(
            Resume.id == resume_id,
            Resume.user_id == current_user.id
        )
        .first()
    )
    if not resume_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='简历不存在'
        )
    file_path = UPLOAD_DIR / resume_record.stored_filename
    file_path.unlink(missing_ok=True)
    db.delete(resume_record)
    db.commit()

@router.get('/{resume_id}/download')
def download_resume(
    resume_id:int,
    current_user:User = Depends(get_current_user),
    db:Session = Depends(get_db)
):
    resume_record = (
        db.query(Resume)
        .filter(
            Resume.id == resume_id,
            Resume.user_id == current_user.id 
        )
        .first()
    )
    if not resume_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='简历不存在'
        )
    file_path = UPLOAD_DIR / resume_record.stored_filename
    if not file_path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='简历文件不存在'
        )
    return FileResponse(
        path=file_path,
        media_type=resume_record.content_type,
        filename=resume_record.original_filename
    )

@router.post('/{resume_id}/analyze')
def analyze_resume(
    resume_id:int,
    use_ai:bool=False,
    current_user:User = Depends(get_current_user),
    db:Session = Depends(get_db)
):
    resume_record=(
        db.query(Resume)
        .filter(
            Resume.id == resume_id,
            Resume.user_id == current_user.id
        )
        .first()
    )
    if not resume_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='简历不存在'
        )
    if resume_record.content_type != 'application/pdf':
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail='当前仅支持分析PDF简历'
        )
    file_path = UPLOAD_DIR / resume_record.stored_filename
    try:
        text = extract_pdf_text(file_path)
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(error)
        )from error
    if not use_ai:
        return {
            'resume_id':resume_record.id,
            'text':text,
            'character_count':len(text)
        }
    try:
        analysis =  analyze_resume_with_ai(
            resume_id=resume_id,
            resume_text=text
        )
        if analysis.ai_ok:
            save_resume_analysis(
                db=db,
                analysis=analysis
            )
        return analysis
    except RuntimeError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(error)
        )from error