import logging
from pathlib import Path
from tempfile import TemporaryDirectory

from celery import Celery

from app.config import get_settings
from app.database import session_factory
from app.extraction import ReviewRequired, extract
from app.models import Document
from app.storage import materialize

settings = get_settings()
celery = Celery("insightai", broker=settings.redis_url)
celery.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    task_time_limit=180,
    task_soft_time_limit=150,
    worker_prefetch_multiplier=1,
    broker_connection_retry_on_startup=True,
)
logger = logging.getLogger(__name__)


@celery.task(name="documents.extract")
def process_document(document_id: str):
    with session_factory()() as db:
        document = db.get(Document, document_id)
        if document is None or document.status == "extracted":
            return
        document.status = "processing"
        document.error = None
        db.commit()
        try:
            with TemporaryDirectory() as temporary:
                path = materialize(
                    document.storage_key, Path(temporary) / f"input{document.extension}"
                )
                document.extraction = extract(path, document.extension)
            document.status = "extracted"
        except ReviewRequired as exc:
            document.status = "needs_attention"
            document.error = str(exc)
        except Exception:
            logger.exception("Extraction failed for document %s", document.id)
            document.status = "failed"
            document.error = "Could not read this document. Check the file and upload a new copy."
        db.commit()


def dispatch_document(document_id: str):
    if get_settings().task_mode == "inline":
        process_document(document_id)
    else:
        process_document.delay(document_id)
