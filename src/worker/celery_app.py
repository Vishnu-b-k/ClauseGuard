import os
import asyncio
from celery import Celery
import logging

from src.orchestrator.lyzr_orchestrator import LyzrWorkflowOrchestrator
from src.retrieval import get_retrieval_client

RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://guest:guest@localhost:5672//")

celery_app = Celery(
    "contract_worker",
    broker=RABBITMQ_URL,
    backend=os.getenv("CELERY_RESULT_BACKEND", "db+sqlite:///celery_results.sqlite")
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    worker_enable_remote_control=False,
    worker_send_task_events=False,
)

logger = logging.getLogger(__name__)

# Reusing the existing async pipeline inside Celery
# Note: Since the orchestrator is async, we need to run it in a new event loop inside the worker thread
def _run_async_orchestrator(text: str, contract_id: str):
    retrieval_client = get_retrieval_client()
    orchestrator = LyzrWorkflowOrchestrator(retrieval_client=retrieval_client)
    
    # Run the orchestrator
    result = asyncio.run(orchestrator.run(text, contract_id=contract_id))
    return result

@celery_app.task(name="process_contract_task", bind=True, max_retries=3)
def process_contract_task(self, contract_id: str, text: str):
    """
    Background task to process a contract using the AI pipeline.
    """
    logger.info(f"Starting background processing for contract_id: {contract_id}")
    
    try:
        # We don't save to postgres yet since Phase A db.py models were created but not fully wired.
        # But we return the dictionary result so it's stored in the Celery result backend.
        result = _run_async_orchestrator(text, contract_id)
        
        logger.info(f"Completed processing for contract_id: {contract_id}")
        return result.to_dict()
    except Exception as exc:
        logger.error(f"Failed to process contract {contract_id}: {exc}")
        self.retry(exc=exc, countdown=10) # Exponential backoff would be better
