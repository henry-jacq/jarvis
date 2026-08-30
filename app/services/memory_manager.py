from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from app.models.memory import GlobalMemory, AgentMemory, ProjectMemory
from app.schemas.memory import MemoryCandidateCreate

class MemoryManager:
    """
    Manages persistent state outside agents.
    Agents propose candidate memories; Memory Manager classifies, validates,
    deduplicates, and persists curated memory records into MySQL.
    """

    def __init__(self, db: Session):
        self.db = db

    def save_memory_candidate(self, candidate: MemoryCandidateCreate) -> Dict[str, Any]:
        """
        Validates, deduplicates, and saves candidate memory to designated scope.
        """
        scope = candidate.scope.lower()
        key = candidate.key.strip()
        content = candidate.content.strip()

        if scope == "global":
            existing = self.db.query(GlobalMemory).filter(GlobalMemory.key == key).first()
            if existing:
                existing.content = content
                existing.importance = candidate.importance
                existing.provenance = candidate.provenance
                memory_obj = existing
            else:
                memory_obj = GlobalMemory(
                    category=candidate.category,
                    key=key,
                    content=content,
                    importance=candidate.importance,
                    provenance=candidate.provenance
                )
                self.db.add(memory_obj)
        elif scope == "agent":
            if not candidate.target_id:
                raise ValueError("target_id (agent_id) required for agent-scoped memory.")
            existing = self.db.query(AgentMemory).filter(
                AgentMemory.agent_id == candidate.target_id,
                AgentMemory.key == key
            ).first()
            if existing:
                existing.content = content
                existing.importance = candidate.importance
                existing.provenance = candidate.provenance
                memory_obj = existing
            else:
                memory_obj = AgentMemory(
                    agent_id=candidate.target_id,
                    category=candidate.category,
                    key=key,
                    content=content,
                    importance=candidate.importance,
                    provenance=candidate.provenance
                )
                self.db.add(memory_obj)
        elif scope == "project":
            if not candidate.target_id:
                raise ValueError("target_id (project_id) required for project-scoped memory.")
            existing = self.db.query(ProjectMemory).filter(
                ProjectMemory.project_id == candidate.target_id,
                ProjectMemory.key == key
            ).first()
            if existing:
                existing.content = content
                existing.importance = candidate.importance
                existing.provenance = candidate.provenance
                memory_obj = existing
            else:
                memory_obj = ProjectMemory(
                    project_id=candidate.target_id,
                    category=candidate.category,
                    key=key,
                    content=content,
                    importance=candidate.importance,
                    provenance=candidate.provenance
                )
                self.db.add(memory_obj)
        else:
            raise ValueError(f"Unknown memory scope '{scope}'. Supported scopes: global, agent, project.")

        self.db.commit()
        self.db.refresh(memory_obj)
        return {
            "id": memory_obj.id,
            "scope": scope,
            "key": memory_obj.key,
            "content": memory_obj.content,
            "category": memory_obj.category,
            "created_at": memory_obj.created_at
        }

    def get_memory_for_context(
        self,
        scopes: List[str],
        agent_id: Optional[str] = None,
        project_id: Optional[str] = None
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Retrieves relevant memory items across requested scopes.
        """
        results = {"global": [], "agent": [], "project": []}

        if "global" in scopes:
            globals_items = self.db.query(GlobalMemory).all()
            results["global"] = [
                {"key": m.key, "content": m.content, "category": m.category, "importance": m.importance}
                for m in globals_items
            ]

        if "agent" in scopes and agent_id:
            agent_items = self.db.query(AgentMemory).filter(AgentMemory.agent_id == agent_id).all()
            results["agent"] = [
                {"key": m.key, "content": m.content, "category": m.category, "importance": m.importance}
                for m in agent_items
            ]

        if "project" in scopes and project_id:
            project_items = self.db.query(ProjectMemory).filter(ProjectMemory.project_id == project_id).all()
            results["project"] = [
                {"key": m.key, "content": m.content, "category": m.category, "importance": m.importance}
                for m in project_items
            ]

        return results
