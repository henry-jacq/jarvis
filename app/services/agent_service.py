from typing import Optional, List, Dict, Any
# pyrefly: ignore [missing-import]
from sqlalchemy.orm import Session
from app.models.agents import Agent, AgentVersion
from app.schemas.agent import AgentCreate, AgentVersionCreate

class AgentService:
    def __init__(self, db: Session):
        self.db = db

    def create_agent(self, payload: AgentCreate) -> Agent:
        agent = Agent(
            name=payload.name,
            role=payload.role,
            purpose=payload.purpose,
            application_id=payload.application_id,
            status=payload.status
        )
        self.db.add(agent)
        self.db.commit()
        self.db.refresh(agent)

        # Create initial version v1
        ver_payload = payload.initial_version
        version = AgentVersion(
            agent_id=agent.id,
            version=1,
            system_prompt=ver_payload.system_prompt,
            model_provider=ver_payload.model_provider,
            model_name=ver_payload.model_name,
            temperature=ver_payload.temperature,
            tool_policy=ver_payload.tool_policy,
            memory_policy=ver_payload.memory_policy,
            context_policy=ver_payload.context_policy,
            config=ver_payload.config
        )
        self.db.add(version)
        self.db.commit()
        self.db.refresh(version)

        agent.active_version_id = version.id
        self.db.commit()
        self.db.refresh(agent)
        return agent

    def publish_new_version(self, agent_id: str, ver_payload: AgentVersionCreate) -> AgentVersion:
        latest = self.db.query(AgentVersion).filter(
            AgentVersion.agent_id == agent_id
        ).order_by(AgentVersion.version.desc()).first()

        next_ver_num = (latest.version + 1) if latest else 1

        version = AgentVersion(
            agent_id=agent_id,
            version=next_ver_num,
            system_prompt=ver_payload.system_prompt,
            model_provider=ver_payload.model_provider,
            model_name=ver_payload.model_name,
            temperature=ver_payload.temperature,
            tool_policy=ver_payload.tool_policy,
            memory_policy=ver_payload.memory_policy,
            context_policy=ver_payload.context_policy,
            config=ver_payload.config
        )
        self.db.add(version)
        self.db.commit()
        self.db.refresh(version)

        # Set as active version on agent
        agent = self.db.query(Agent).filter(Agent.id == agent_id).first()
        if agent:
            agent.active_version_id = version.id
            self.db.commit()
        
        return version

    def get_agent(self, agent_id: str) -> Optional[Agent]:
        return self.db.query(Agent).filter(Agent.id == agent_id).first()

    def get_active_version(self, agent: Agent) -> Optional[AgentVersion]:
        if not agent.active_version_id:
            return None
        return self.db.query(AgentVersion).filter(AgentVersion.id == agent.active_version_id).first()

    def list_agents(self) -> List[Agent]:
        return self.db.query(Agent).all()
