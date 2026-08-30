from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from app.models.conversations import Conversation, Message
from app.schemas.conversation import ConversationCreate, MessageCreate, ProjectSuggestionResponse

class ConversationService:
    def __init__(self, db: Session):
        self.db = db

    def create_conversation(self, payload: ConversationCreate) -> Conversation:
        conv = Conversation(
            title=payload.title or "New Conversation",
            project_id=payload.project_id,
            metadata_info=payload.metadata_info or {}
        )
        self.db.add(conv)
        self.db.commit()
        self.db.refresh(conv)

        if payload.initial_message:
            self.add_message(conv.id, payload.initial_message)

        return conv

    def add_message(self, conversation_id: str, payload: MessageCreate) -> Message:
        msg = Message(
            conversation_id=conversation_id,
            role=payload.role,
            content=payload.content,
            metadata_info=payload.metadata_info or {}
        )
        self.db.add(msg)
        self.db.commit()
        self.db.refresh(msg)
        return msg

    def get_conversation(self, conversation_id: str) -> Optional[Conversation]:
        return self.db.query(Conversation).filter(Conversation.id == conversation_id).first()

    def get_messages(self, conversation_id: str, limit: int = 50) -> List[Message]:
        return self.db.query(Message).filter(
            Message.conversation_id == conversation_id
        ).order_by(Message.created_at.asc()).limit(limit).all()

    def attach_to_project(self, conversation_id: str, project_id: str) -> Conversation:
        conv = self.get_conversation(conversation_id)
        if not conv:
            raise ValueError(f"Conversation '{conversation_id}' not found.")
        conv.project_id = project_id
        self.db.commit()
        self.db.refresh(conv)
        return conv

    def evaluate_project_suggestion(self, conversation_id: str) -> ProjectSuggestionResponse:
        """
        Evaluates whether an ongoing standalone conversation represents a substantial body of work
        and suggests creating a Project.
        """
        conv = self.get_conversation(conversation_id)
        if not conv:
            raise ValueError(f"Conversation '{conversation_id}' not found.")

        messages = self.get_messages(conversation_id, limit=100)
        user_msg_count = sum(1 for m in messages if m.role == "user")
        total_len = sum(len(m.content) for m in messages)

        # Suggest project if standalone and has >= 3 user turns or > 300 chars
        should_suggest = (conv.project_id is None) and (user_msg_count >= 3 or total_len > 300)

        suggested_title = conv.title if conv.title != "New Conversation" else "Proposed Project Workspace"
        suggested_objective = (
            f"Consolidate research and tasks initiated in conversation '{conv.title}'"
        )

        reason = (
            f"Conversation has {user_msg_count} user turns and {total_len} characters of discussion, "
            "indicating a long-lived activity suitable for a dedicated Project workspace."
            if should_suggest else "Conversation is short and focused."
        )

        return ProjectSuggestionResponse(
            conversation_id=conversation_id,
            suggest_project=should_suggest,
            reason=reason,
            suggested_title=suggested_title,
            suggested_objective=suggested_objective
        )
