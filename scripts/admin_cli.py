import sys
import os
import argparse

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.db import SessionLocal
from app.services.workflow_service import WorkflowService
from app.services.queue_service import QueueService
from app.services.job_manager import JobManager
from app.services.memory_manager import MemoryManager
from app.services.scheduler_service import SchedulerService

def cmd_status():
    db = SessionLocal()
    try:
        wf_svc = WorkflowService(db)
        queue_svc = QueueService(db)
        job_mgr = JobManager(db)
        sched_svc = SchedulerService(db)

        pending_approvals = wf_svc.list_pending_approvals()
        queue_status = queue_svc.get_queue_status()
        jobs = job_mgr.list_jobs()
        schedules = sched_svc.list_schedules()

        print("==================================================")
        print("         JARVIS AGENT PLATFORM STATUS            ")
        print("==================================================")
        print(f"Pending HITL Approvals : {len(pending_approvals)}")
        print(f"Queue Status           : Pending={queue_status.get('PENDING', 0)}, Claimed={queue_status.get('CLAIMED', 0)}, Completed={queue_status.get('COMPLETED', 0)}, DeadLetter={queue_status.get('DEAD_LETTER', 0)}")
        print(f"Total Jobs Registered  : {len(jobs)}")
        print(f"Active Schedules       : {len(schedules)}")
        print("==================================================")


        if pending_approvals:
            print("\n[PENDING APPROVALS]")
            for appr in pending_approvals:
                print(f"  ID: {appr.id} | Exec: {appr.execution_id} | Type: {appr.request_type} | Node/Tool: {appr.node_key or appr.tool_name}")

    finally:
        db.close()

def cmd_resolve_approval(approval_id: str, decision: str, feedback: str = None):
    db = SessionLocal()
    try:
        from app.runtime.workflow_executor import StaticWorkflowExecutor
        wf_executor = StaticWorkflowExecutor(db)
        wf_svc = WorkflowService(db)
        appr = wf_svc.get_approval_request(approval_id)
        if not appr:
            print(f"Error: Approval request '{approval_id}' not found.")
            return

        exec_rec = wf_executor.resume_execution(
            execution_id=appr.execution_id,
            approval_id=approval_id,
            decision=decision,
            feedback=feedback
        )
        print(f"Successfully resolved approval '{approval_id}' as {decision.upper()}.")
        print(f"Execution status is now: {exec_rec.status}")
    finally:
        db.close()

def cmd_decay_memory(factor: float):
    db = SessionLocal()
    try:
        mem_mgr = MemoryManager(db)
        count = mem_mgr.apply_memory_decay(decay_factor=factor)
        print(f"Applied memory importance decay factor ({factor}). Updated {count} records.")
    finally:
        db.close()

def main():
    parser = argparse.ArgumentParser(description="Jarvis Platform Admin CLI")
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("status", help="Display system status overview")
    
    appr_p = subparsers.add_parser("approve", help="Approve a pending approval request")
    appr_p.add_argument("id", help="Approval Request ID")
    appr_p.add_argument("--feedback", default=None, help="Optional feedback note")

    rej_p = subparsers.add_parser("reject", help="Reject a pending approval request")
    rej_p.add_argument("id", help="Approval Request ID")
    rej_p.add_argument("--feedback", default=None, help="Optional feedback note")

    decay_p = subparsers.add_parser("decay", help="Run memory importance decay")
    decay_p.add_argument("--factor", type=float, default=0.9, help="Decay multiplier factor")

    args = parser.parse_args()

    if args.command == "status":
        cmd_status()
    elif args.command == "approve":
        cmd_resolve_approval(args.id, "APPROVED", args.feedback)
    elif args.command == "reject":
        cmd_resolve_approval(args.id, "REJECTED", args.feedback)
    elif args.command == "decay":
        cmd_decay_memory(args.factor)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
