import asyncio
from io import BytesIO
from types import SimpleNamespace as NS
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException, UploadFile
from sqlalchemy.exc import SQLAlchemyError
from starlette.datastructures import Headers

from app.routers import resumes


def make_file(data: bytes) -> UploadFile:
    return UploadFile(
        file=BytesIO(data),
        size=None,
        filename='resume.pdf',
        headers=Headers({'content-type': 'application/pdf'}),
    )


def call_upload(data: bytes, db: MagicMock):
    return asyncio.run(
        resumes.upload_resume(make_file(data), NS(id=7), db)
    )


def test_upload_pdf_saves_real_size(monkeypatch, tmp_path):
    monkeypatch.setattr(resumes, 'UPLOAD_DIR', tmp_path)
    db = MagicMock()
    data = b'%PDF-1.4\nvalid'

    result = call_upload(data, db)

    saved = db.add.call_args.args[0]
    assert result['filename'] == 'resume.pdf'
    assert saved.file_size == len(data)
    assert len(list(tmp_path.glob('*.pdf'))) == 1
    assert not list(tmp_path.glob('*.part'))


def test_upload_rejects_fake_pdf(monkeypatch, tmp_path):
    monkeypatch.setattr(resumes, 'UPLOAD_DIR', tmp_path)
    db = MagicMock()

    with pytest.raises(HTTPException) as caught:
        call_upload(b'not a pdf', db)

    assert caught.value.status_code == 415
    assert not list(tmp_path.iterdir())
    db.add.assert_not_called()


def test_upload_checks_real_size(monkeypatch, tmp_path):
    monkeypatch.setattr(resumes, 'UPLOAD_DIR', tmp_path)
    monkeypatch.setattr(resumes, 'MAX_FILE_SIZE', 8)
    db = MagicMock()

    with pytest.raises(HTTPException) as caught:
        call_upload(b'%PDF-1.4x', db)

    assert caught.value.status_code == 413
    assert not list(tmp_path.iterdir())
    db.add.assert_not_called()


def test_upload_db_failure_removes_file(monkeypatch, tmp_path):
    monkeypatch.setattr(resumes, 'UPLOAD_DIR', tmp_path)
    db = MagicMock()
    db.commit.side_effect = SQLAlchemyError('commit failed')

    with pytest.raises(HTTPException) as caught:
        call_upload(b'%PDF-1.4\nvalid', db)

    assert caught.value.status_code == 500
    db.rollback.assert_called_once()
    assert not list(tmp_path.iterdir())
