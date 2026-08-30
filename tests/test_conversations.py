import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.db import Base
from app.models.projects import Project
from app.services.conversation_service import ConversationService
from app.schemas.conversation import ConversationCreate, MessageCreate

@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()

def test_conversation_lifecycle(db_session):
    conv_svc = ConversationService(db_session)

    # 1. Create Standalone Conversation
    conv = conv_svc.create_conversation(
        ConversationCreate(
            title="Database Architecture",
            initial_message=MessageCreate(role="user", content="Should we use MySQL or PostgreSQL?")
        )
    )
    assert conv.id is not None
    assert conv.project_id is None

    # Add turns
    conv_svc.add_message(conv.id, MessageCreate(role="assistant", content="We selected MySQL for unified persistence."))
    conv_svc.add_message(conv.id, MessageCreate(role="user", content="What about ORM?"))
    conv_svc.add_message(conv.id, MessageCreate(role="assistant", content="SQLAlchemy with PyMySQL driver."))
    conv_svc.add_message(conv.id, MessageCreate(role="user", content="Great, let's create a project for this!"))

    # 2. Test Project Suggestion Evaluation
    suggestion = conv_svc.evaluate_project_suggestion(conv.id)
    assert suggestion.suggest_project is True
    assert "Database Architecture" in suggestion.suggested_title

    # 3. Attach Conversation to Project
    proj = Project(name="Database Migration Project", objective="Migrate schema to MySQL")
    db_session.add(proj)
    db_session.commit()

    attached = conv_svc.attach_to_project(conv.id, proj.id)
    assert attached.project_id == proj.id
