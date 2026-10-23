import hashlib
from pathlib import Path
from tempfile import TemporaryDirectory

from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth import create_token, current_user, passwords
from app.config import get_settings
from app.database import get_db
from app.extraction import EXTENSIONS, check_container
from app.models import Business, Document, User, new_id
from app.storage import delete_file, save_file
from app.tasks import dispatch_document

app = FastAPI(title="InsightAI", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().cors_origins,
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type"],
)


class Credentials(BaseModel):
    email: str = Field(min_length=3, max_length=254, pattern=r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
    password: str = Field(min_length=12, max_length=128)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value):
        return value.lower().strip()


class Registration(Credentials):
    business_name: str = Field(min_length=2, max_length=120)
    industry: str = Field(default="", max_length=120)


class DocumentView(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    filename: str
    extension: str
    size_bytes: int
    status: str
    error: str | None


@app.get("/api/health")
def health(db: Session = Depends(get_db)):
    db.execute(text("SELECT 1"))
    return {"status": "ok", "service": "insightai", "version": "0.1.0"}


@app.post("/api/auth/register", status_code=201)
def register(data: Registration, db: Session = Depends(get_db)):
    business = Business(name=data.business_name.strip(), industry=data.industry.strip())
    if len(business.name) < 2:
        raise HTTPException(422, "Enter a business name")
    db.add(business)
    db.flush()
    user = User(
        email=data.email, password_hash=passwords.hash(data.password), business_id=business.id
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "This email is already registered") from None
    return {"access_token": create_token(user), "token_type": "bearer"}


@app.post("/api/auth/login")
def login(data: Credentials, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == data.email))
    if user is None or not passwords.verify(data.password, user.password_hash):
        raise HTTPException(401, "Email or password is incorrect")
    return {"access_token": create_token(user), "token_type": "bearer"}


@app.get("/api/workspace")
def workspace(user: User = Depends(current_user), db: Session = Depends(get_db)):
    business = db.get(Business, user.business_id)
    return {
        "id": business.id,
        "name": business.name,
        "industry": business.industry,
        "currency": business.currency,
        "timezone": business.timezone,
        "email": user.email,
    }


@app.get("/api/documents", response_model=list[DocumentView])
def documents(user: User = Depends(current_user), db: Session = Depends(get_db)):
    return db.scalars(
        select(Document)
        .where(Document.business_id == user.business_id)
        .order_by(Document.created_at.desc())
        .limit(100)
    ).all()


def owned_document(document_id: str, user: User, db: Session) -> Document:
    document = db.scalar(
        select(Document).where(
            Document.id == document_id,
            Document.business_id == user.business_id,
        )
    )
    if document is None:
        raise HTTPException(404, "Document not found")
    return document


@app.get("/api/documents/{document_id}")
def document_detail(
    document_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)
):
    document = owned_document(document_id, user, db)
    return {**DocumentView.model_validate(document).model_dump(), "extraction": document.extraction}


@app.post("/api/documents", response_model=DocumentView, status_code=201)
async def upload_document(
    file: UploadFile = File(...),
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    settings = get_settings()
    filename = (file.filename or "").replace("\\", "/").split("/")[-1]
    extension = Path(filename).suffix.lower()
    if extension not in EXTENSIONS or not filename or len(filename) > 240:
        raise HTTPException(415, "Supported files: PDF, XLSX, XLS, CSV, DOCX, JPG and PNG")
    document_id = new_id()
    key = f"{user.business_id}/{document_id}{extension}"
    size = 0
    digest = hashlib.sha256()
    with TemporaryDirectory() as temporary:
        path = Path(temporary) / f"upload{extension}"
        try:
            with path.open("wb") as handle:
                while chunk := await file.read(1024 * 1024):
                    size += len(chunk)
                    if size > settings.max_upload_bytes:
                        raise HTTPException(413, "Maximum upload size is 20 MB")
                    digest.update(chunk)
                    handle.write(chunk)
        finally:
            await file.close()
        if size == 0:
            raise HTTPException(422, "The uploaded file is empty")
        try:
            check_container(path, extension)
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc
        duplicate = db.scalar(
            select(Document).where(
                Document.business_id == user.business_id,
                Document.sha256 == digest.hexdigest(),
            )
        )
        if duplicate is not None:
            raise HTTPException(409, "This file has already been uploaded")
        save_file(key, path)
    document = Document(
        id=document_id,
        business_id=user.business_id,
        filename=filename,
        extension=extension,
        storage_key=key,
        sha256=digest.hexdigest(),
        size_bytes=size,
    )
    db.add(document)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        delete_file(key)
        raise HTTPException(409, "This file has already been uploaded") from None
    except Exception:
        db.rollback()
        delete_file(key)
        raise
    try:
        dispatch_document(document.id)
    except Exception:
        document.status = "failed"
        document.error = "Processing could not be queued. Please retry processing."
        db.commit()
    db.refresh(document)
    return document


@app.post("/api/documents/{document_id}/retry", response_model=DocumentView)
def retry_document(
    document_id: str,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    document = owned_document(document_id, user, db)
    if document.status not in {"failed", "needs_attention"}:
        raise HTTPException(
            409, "Only failed documents or documents needing attention can be retried"
        )
    document.status = "queued"
    document.error = None
    db.commit()
    try:
        dispatch_document(document.id)
    except Exception:
        document.status = "failed"
        document.error = "Processing could not be queued. Please retry processing."
        db.commit()
    db.refresh(document)
    return document
