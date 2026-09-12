import time
import logging
from typing import Optional
from sqlalchemy.orm import Session
from app.core.db import SessionLocal
from app.services.queue_service import QueueService
from app.services.job_manager import JobManager
from app.runtime.executor import SimpleAgentExecutor
from app.runtime.workflow_executor import StaticWorkflowExecutor
from app.models.jobs import Job

logger = logging.getLogger(__name__)

class WorkerEngine:
    """
    Background Worker Execution Engine.
    Claims generic QueueMessage payloads from QueueService, executes agent & workflow tasks,
    handles backoff retries, and records attempt telemetry.
    """

    def __init__(self, worker_id: str = "worker-1"):
        self.worker_id = worker_id

    def process_one_message(self, db: Session, topic: str = "default") -> bool:
        queue_svc = QueueService(db)
        job_mgr = JobManager(db)
        executor = SimpleAgentExecutor(db)

        msg = queue_svc.claim_next_message(worker_id=self.worker_id, topic=topic)
        if not msg:
            return False

        start_time = time.time()
        job_id = msg.payload.get("job_id")
        
        # Update Job status to RUNNING
        if job_id:
            job = job_mgr.get_job(job_id)
            if job:
                job.status = "RUNNING"
                db.commit()

        try:
            if msg.payload_type == "agent_execution":
                task = msg.payload.get("task")
                agent_id = msg.payload.get("agent_id")
                project_id = msg.payload.get("project_id")
                override_config = msg.payload.get("override_config")

                execution = executor.execute(
                    task=task,
                    agent_id=agent_id,
                    project_id=project_id,
                    override_config=override_config
                )

                latency_ms = round((time.time() - start_time) * 1000, 2)

                if execution.status == "COMPLETED":
                    queue_svc.complete_message(msg.id)
                    if job_id:
                        job = job_mgr.get_job(job_id)
                        if job:
                            job.execution_id = execution.id
                            db.commit()
                        job_mgr.record_attempt(
                            job_id=job_id,
                            attempt_number=msg.attempts,
                            status="SUCCESS",
                            latency_ms=latency_ms
                        )
                else:
                    err = execution.error_message or "Agent execution failed"
                    queue_svc.fail_message(msg.id, err)
                    if job_id:
                        job_mgr.record_attempt(
                            job_id=job_id,
                            attempt_number=msg.attempts,
                            status="FAILURE",
                            latency_ms=latency_ms,
                            error_message=err
                        )

            elif msg.payload_type == "workflow_execution":
                task = msg.payload.get("task")
                workflow_id = msg.payload.get("workflow_id")
                project_id = msg.payload.get("project_id")
                override_config = msg.payload.get("override_config")

                wf_executor = StaticWorkflowExecutor(db)
                execution = wf_executor.execute(
                    workflow_id=workflow_id,
                    task=task,
                    project_id=project_id,
                    override_config=override_config
                )

                latency_ms = round((time.time() - start_time) * 1000, 2)

                if execution.status in ["COMPLETED", "WAITING_FOR_APPROVAL"]:
                    queue_svc.complete_message(msg.id)
                    if job_id:
                        job = job_mgr.get_job(job_id)
                        if job:
                            job.execution_id = execution.id
                            db.commit()
                        job_mgr.record_attempt(
                            job_id=job_id,
                            attempt_number=msg.attempts,
                            status="SUCCESS",
                            latency_ms=latency_ms
                        )
                else:
                    err = execution.error_message or "Workflow execution failed"
                    queue_svc.fail_message(msg.id, err)
                    if job_id:
                        job_mgr.record_attempt(
                            job_id=job_id,
                            attempt_number=msg.attempts,
                            status="FAILURE",
                            latency_ms=latency_ms,
                            error_message=err
                        )

            else:
                # Custom payload types handled successfully
                latency_ms = round((time.time() - start_time) * 1000, 2)
                queue_svc.complete_message(msg.id)
                if job_id:
                    job_mgr.record_attempt(
                        job_id=job_id,
                        attempt_number=msg.attempts,
                        status="SUCCESS",
                        latency_ms=latency_ms
                    )


            return True

        except Exception as e:
            latency_ms = round((time.time() - start_time) * 1000, 2)
            err_msg = str(e)
            logger.error(f"Worker process error on message '{msg.id}': {err_msg}")
            queue_svc.fail_message(msg.id, err_msg)
            if job_id:
                job_mgr.record_attempt(
                    job_id=job_id,
                    attempt_number=msg.attempts,
                    status="FAILURE",
                    latency_ms=latency_ms,
                    error_message=err_msg
                )
            return True

    def run_loop(self, poll_interval: float = 1.0, max_iterations: Optional[int] = None):
        iterations = 0
        while True:
            db = SessionLocal()
            try:
                processed = self.process_one_message(db)
                if not processed:
                    time.sleep(poll_interval)
            finally:
                db.close()

            iterations += 1
            if max_iterations and iterations >= max_iterations:
                break

if __name__ == "__main__":
    worker = WorkerEngine()
    print("Worker engine starting...")
    worker.run_loop()
