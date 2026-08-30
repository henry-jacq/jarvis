from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from app.models.jobs import Schedule
from app.schemas.schedule import ScheduleCreate
from app.schemas.job import JobCreate
from app.services.job_manager import JobManager

class SchedulerService:
    """
    Scheduler Service.
    Evaluates active schedules and enqueues background jobs.
    Decoupled: Creates jobs via JobManager rather than calling LLMs directly.
    """

    def __init__(self, db: Session):
        self.db = db
        self.job_manager = JobManager(db)

    def create_schedule(self, payload: ScheduleCreate) -> Schedule:
        now = datetime.now(timezone.utc)
        next_run = self.calculate_next_run(payload.schedule_expression, now)

        sched = Schedule(
            name=payload.name,
            agent_id=payload.agent_id,
            project_id=payload.project_id,
            schedule_expression=payload.schedule_expression,
            timezone=payload.timezone,
            enabled=payload.enabled,
            next_run_at=next_run,
            task_input=payload.task_input
        )
        self.db.add(sched)
        self.db.commit()
        self.db.refresh(sched)
        return sched

    def calculate_next_run(self, expression: str, base_time: datetime) -> datetime:
        if base_time.tzinfo is None:
            base_time = base_time.replace(tzinfo=timezone.utc)
            
        expr = expression.strip().lower()
        if expr.startswith("interval:"):
            seconds = int(expr.split(":")[1])
            return base_time + timedelta(seconds=seconds)
        elif expr.startswith("cron:"):
            return base_time + timedelta(hours=24)
        return base_time + timedelta(hours=1)

    def evaluate_schedules(self) -> List[Dict[str, Any]]:
        """
        Scans enabled schedules due for execution and creates corresponding background jobs.
        """
        now = datetime.now(timezone.utc)
        schedules_due = self.db.query(Schedule).filter(
            Schedule.enabled == True,
            Schedule.next_run_at <= now
        ).all()

        triggered = []
        for sched in schedules_due:
            task_text = sched.task_input.get("task", f"Scheduled execution for {sched.name}")
            
            job = self.job_manager.submit_job(
                JobCreate(
                    task=task_text,
                    agent_id=sched.agent_id,
                    project_id=sched.project_id,
                    job_type="RECURRING",
                    override_config=sched.task_input.get("override_config")
                )
            )

            sched.last_run_at = now
            sched.next_run_at = self.calculate_next_run(sched.schedule_expression, now)
            self.db.commit()

            triggered.append({"schedule_id": sched.id, "job_id": job.id, "name": sched.name})

        return triggered

    def list_schedules(self) -> List[Schedule]:
        return self.db.query(Schedule).all()

    def get_schedule(self, schedule_id: str) -> Optional[Schedule]:
        return self.db.query(Schedule).filter(Schedule.id == schedule_id).first()
