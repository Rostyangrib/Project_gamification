from sqlalchemy import (
    Column, String, Integer, Text, ForeignKey, JSON, DateTime,
    create_engine, text, MetaData
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from config.db import engine
from sqlalchemy.orm import Session

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(PG_UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False)
    password_hash = Column(Text, nullable=False)
    total_points = Column(Integer, default=0)
    role = Column(String, default="admin")
    created_at = Column(DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP"))
    updated_at = Column(DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP"), onupdate=text("CURRENT_TIMESTAMP"))
    #boards = relationship("Board", back_populates="user")
    tasks = relationship("Task", back_populates="user")
    #categories = relationship("Category", back_populates="user")
    rewards = relationship("Reward", back_populates="user")

# class Board(Base):
#     __tablename__ = "boards"
#     id = Column(PG_UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
#     user_id = Column(PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
#     name = Column(String, nullable=False)
#     description = Column(Text)
#     created_at = Column(DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP"))
#     updated_at = Column(DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP"), onupdate=text("CURRENT_TIMESTAMP"))
#     user = relationship("User", back_populates="boards")
#     tasks = relationship("Task", back_populates="board")

class TaskStatus(Base):
    __tablename__ = "task_status"
    id = Column(PG_UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    code = Column(String, unique=True, nullable=False)
    name = Column(String, nullable=False)

# class Category(Base):
#     __tablename__ = "categories"
#     id = Column(PG_UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
#     user_id = Column(PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
#     name = Column(String, nullable=False)
#     color = Column(String)
#     user = relationship("User", back_populates="categories")
#     tasks = relationship("Task", back_populates="category")

class Tag(Base):
    __tablename__ = "tags"
    id = Column(PG_UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    name = Column(String, unique=True, nullable=False)
    tasks = relationship("Task", secondary="task_tags", back_populates="tags")

class TaskTag(Base):
    __tablename__ = "task_tags"
    task_id = Column(PG_UUID(as_uuid=True), ForeignKey("tasks.id"), primary_key=True)
    tag_id = Column(PG_UUID(as_uuid=True), ForeignKey("tags.id"), primary_key=True)

class Task(Base):
    __tablename__ = "tasks"
    id = Column(PG_UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    user_id = Column(PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
   # board_id = Column(PG_UUID(as_uuid=True), ForeignKey("boards.id"), nullable=False)
    status_id = Column(PG_UUID(as_uuid=True), ForeignKey("task_status.id"), nullable=False)
    #category_id = Column(PG_UUID(as_uuid=True), ForeignKey("categories.id"), nullable=False)
    title = Column(String, nullable=False)
    description = Column(Text)
    ai_analysis_metadata = Column(JSON)
    estimated_points = Column(Integer, default=0)
    awarded_points = Column(Integer, default=0)
    due_date = Column(DateTime)
    completed_at = Column(DateTime)
    created_at = Column(DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP"))
    updated_at = Column(DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP"), onupdate=text("CURRENT_TIMESTAMP"))
    user = relationship("User", back_populates="tasks")
   # board = relationship("Board", back_populates="tasks")
    status = relationship("TaskStatus")
    #category = relationship("Category", back_populates="tasks")
    tags = relationship("Tag", secondary="task_tags", back_populates="tasks")

class RewardType(Base):
    __tablename__ = "reward_types"
    id = Column(PG_UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    code = Column(String, unique=True, nullable=False)
    name = Column(String, nullable=False)
    description = Column(Text)
    rewards = relationship("Reward", back_populates="type")

class Reward(Base):
    __tablename__ = "rewards"
    id = Column(PG_UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    user_id = Column(PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    type_id = Column(PG_UUID(as_uuid=True), ForeignKey("reward_types.id"), nullable=False)
    points_amount = Column(Integer, nullable=False)
    awarded_at = Column(DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP"))
    reason = Column(Text)
    user = relationship("User", back_populates="rewards")
    type = relationship("RewardType", back_populates="rewards")

def init_db():
    Base.metadata.create_all(bind=engine)
    with Session(engine) as db:
        if not db.query(TaskStatus).first():
            statuses = [
                TaskStatus(code="todo", name="К выполнению"),
                TaskStatus(code="in_progress", name="В работе"),
                TaskStatus(code="done", name="Выполнено")
            ]
            db.add_all(statuses)
            db.commit()

        if not db.query(Tag).first():
            tag = [
                Tag(name="несрочно"),
                Tag(name="срочно"),
                Tag(name="очень срочно")
            ]
            db.add_all(tag)
            db.commit()