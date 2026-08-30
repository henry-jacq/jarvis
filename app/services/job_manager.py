import time
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from app.models.jobs import Job, JobAttempt
from app.models.executions import Execution
from app.schemas.job import JobCreate
from app.schemas.queue import QueueMessageCreate
from app.services.queue_service import QueueService

class JobManager:
    """
    Manages background Job lifecycle, retries, and attempt logs.
    Enqueues generic agent work payloads into QueueService.
    """

    def __init__(self, db: Session):
        self.db = db
        self.queue_service = QueueService(db)

    def submit_job(self, payload: JobCreate) -> Job:
        now = datetime.now(timezone.utc)

        # 1. Create Pending Job Record
        job = Job(
            job_type=payload.job_type,
            status="PENDING",
            priority=payload.priority,
            max_attempts=payload.max_attempts,
            scheduled_at=now,
            metadata_info={"task": payload.task, "override_config": payload.override_config or {}}
        )
        self.db.add(job)
        self.db.commit()
        self.db.refresh(job)

        # 2. Enqueue Generic Work Payload in QueueService
        queue_msg = self.queue_service.enqueue(
            QueueMessageCreate(
                topic="default",
                payload_type="agent_execution",
                payload={
                    "job_id": job.id,
                    "task": payload.task,
                    "agent_id": payload.agent_id,
                    "project_id": payload.project_id,
                    "override_config": payload.override_config or {}
                },
                priority=payload.priority,
                max_attempts=payload.max_attempts,
                delay_seconds=payload.delay_seconds
            )
        )

        job.queue_message_id = queue_msg.id
        job.status = "QUEUED"
        self.db.commit()
        self.db.refresh(job)
        return job

    def cancel_job(self, job_id: str) -> Job:
        job = self.db.query(Job).filter(Job.id == job_id).first()
        if not job:
            raise ValueError(f"Job '{job_id}' not found.")
        
        job.status = "CANCELLED"
        job.completed_at = datetime.now(timezone.utc)
        
        if job.queue_message_id:
            msg = self.queue_service.complete_message(job.queue_message_id)
            if msg:
                msg.status = "DEAD_LETTER"
                msg.last_error = "Job cancelled by user"
                self.db.commit()

        self.db.commit()
        self.db.refresh(job)
        return job

    def record_attempt(
        self,
        job_id: str,
        attempt_number: int,
        status: str,
        latency_ms: float,
        error_message: Optional[str] = None
    ) -> JobAttempt:
        attempt = JobAttempt(
            job_id=job_id,
            attempt_number=attempt_number,
            status=status,
            error_message=error_message,
            execution_latency_ms=latency_ms,
            started_at=datetime.now(timezone.utc),
            completed_at=datetime.now(timezone.utc)
        )
        self.db.add(attempt)
        
        job = self.db.query(Job).filter(Job.id == job_id).first()
        if job:
            job.attempts = attempt_number
            if status == "SUCCESS":
                job.status = "COMPLETED"
                job.completed_at = datetime.now(timezone.utc)
            elif status == "FAILURE":
                job.error = error_message
                if attempt_number >= job.max_attempts:
                    job.status = "FAILED"
                    job.completed_at = datetime.now(timezone.utc)

        self.db.commit()
        self.db.refresh(attempt)
        return attempt

    def get_job(self, job_id: str) -> Optional[Job]:
        return self.db.query(Job).filter(Job.id == job_id).first()

    def list_jobs(self) -> List[Job]:
        return self.db.query(Job).order_by(Job.created_at.desc()).all()

    def get_job_attempts(self, job_id: str) -> List[JobAttempt]:
        return self.db.query(JobAttempt).filter(JobAttempt.job_id == job_id).order_by(JobAttempt.attempt_number.asc()).all()
