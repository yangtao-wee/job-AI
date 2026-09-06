from types import SimpleNamespace
from unittest.mock import MagicMock
import pytest
from app.routers import resumes
from app.models import Application,ResumeAnalysis,SavedReport

def test_delete_keeps_file_when_db_fails(tmp_path,monkeypatch):
    file_path=tmp_path/'a.pdf'
    file_path.write_bytes(b'pdf')
    record=SimpleNamespace(id=1,user_id=7,stored_filename='a.pdf')
    db=MagicMock()
    db.query.return_value.filter.return_value.first.return_value=record
    db.commit.side_effect=RuntimeError('database failed')
    monkeypatch.setattr(resumes,'UPLOAD_DIR',tmp_path)
    with pytest.raises(RuntimeError):
        resumes.delete_resume(1,SimpleNamespace(id=7),db)
    assert file_path.exists()
    db.rollback.assert_called_once()

def test_delete_removes_file_after_commit(tmp_path,monkeypatch):
    file_path=tmp_path/'a.pdf'
    file_path.write_bytes(b'pdf')
    record=SimpleNamespace(id=1,user_id=7,stored_filename='a.pdf')
    db=MagicMock()
    db.query.return_value.filter.return_value.first.return_value=record
    monkeypatch.setattr(resumes,'UPLOAD_DIR',tmp_path)
    resumes.delete_resume(1,SimpleNamespace(id=7),db)
    assert not file_path.exists()
    db.delete.assert_called_once_with(record)
    db.commit.assert_called_once()
    queried=[item.args[0] for item in db.query.call_args_list]
    assert any(item is Application for item in queried)
    assert any(item is SavedReport for item in queried)
    assert any(item is ResumeAnalysis for item in queried)
    assert db.query.return_value.filter.return_value.delete.call_count==3