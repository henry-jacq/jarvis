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
        project_id: Optional[str] = None,
        min_importance: float = 0.0
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Retrieves relevant memory items across requested scopes with optional min_importance threshold.
        """
        results = {"global": [], "agent": [], "project": []}

        if "global" in scopes:
            globals_items = self.db.query(GlobalMemory).filter(GlobalMemory.importance >= min_importance).all()
            results["global"] = [
                {"key": m.key, "content": m.content, "category": m.category, "importance": m.importance}
                for m in globals_items
            ]

        if "agent" in scopes and agent_id:
            agent_items = self.db.query(AgentMemory).filter(
                AgentMemory.agent_id == agent_id,
                AgentMemory.importance >= min_importance
            ).all()
            results["agent"] = [
                {"key": m.key, "content": m.content, "category": m.category, "importance": m.importance}
                for m in agent_items
            ]

        if "project" in scopes and project_id:
            project_items = self.db.query(ProjectMemory).filter(
                ProjectMemory.project_id == project_id,
                ProjectMemory.importance >= min_importance
            ).all()
            results["project"] = [
                {"key": m.key, "content": m.content, "category": m.category, "importance": m.importance}
                for m in project_items
            ]

        return results

    def apply_memory_decay(self, decay_factor: float = 0.9) -> int:
        """
        Decays memory importance across records to support soft eviction/pruning.
        Returns total records updated.
        """
        updated_count = 0
        for model in [GlobalMemory, AgentMemory, ProjectMemory]:
            records = self.db.query(model).all()
            for rec in records:
                rec.importance = round(rec.importance * decay_factor, 2)
                updated_count += 1
        self.db.commit()
        return updated_count

    def search_vector_stubs(
        self,
        query: str,
        scopes: List[str],
        agent_id: Optional[str] = None,
        project_id: Optional[str] = None,
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Vector similarity retrieval stub compatible with future embeddings index over MySQL.
        Performs keyword match filtering over memory contents.
        """
        all_memories = self.get_memory_for_context(scopes, agent_id, project_id)
        flat_list = []
        for scope, items in all_memories.items():
            for item in items:
                item_copy = dict(item)
                item_copy["scope"] = scope
                flat_list.append(item_copy)

        q_terms = query.lower().split()
        matched = []
        for item in flat_list:
            text = (item["key"] + " " + item["content"]).lower()
            score = sum(1 for term in q_terms if term in text)
            if score > 0:
                item["score"] = score
                matched.append(item)

        matched.sort(key=lambda x: x.get("score", 0), reverse=True)
        return matched[:top_k]

