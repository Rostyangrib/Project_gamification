from sqlalchemy import (
    Column, String, Integer, Text, ForeignKey, JSON, DateTime, text
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

from auth import get_password_hash
from config.db import engine
from sqlalchemy.orm import Session

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, autoincrement=True)
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False)
    password_hash = Column(Text, nullable=False)
    total_points = Column(Integer, default=0)
    role = Column(String, default="user")
    cur_comp = Column(Integer, ForeignKey("competitions.id"), nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP"))
    updated_at = Column(DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP"), onupdate=text("CURRENT_TIMESTAMP"))
    #boards = relationship("Board", back_populates="user")
    tasks = relationship("Task", back_populates="user")
    #categories = relationship("Category", back_populates="user")
    rewards = relationship("Reward", back_populates="user")
    competition = relationship("Competition", back_populates="users")

class Competition(Base):
    __tablename__ = "competitions"
    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String, nullable=False)
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=False)
    created_at = Column(DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP"))
    updated_at = Column(DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP"), onupdate=text("CURRENT_TIMESTAMP"))
    users = relationship("User", back_populates="competition")

class TaskStatus(Base):
    __tablename__ = "task_status"
    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String, unique=True, nullable=False)
    name = Column(String, nullable=False)

class Tag(Base):
    __tablename__ = "tags"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, unique=True, nullable=False)
    tasks = relationship("Task", secondary="task_tags", back_populates="tags")

class TaskTag(Base):
    __tablename__ = "task_tags"
    task_id = Column(Integer, ForeignKey("tasks.id"), primary_key=True)
    tag_id = Column(Integer, ForeignKey("tags.id"), primary_key=True)

class Task(Base):
    __tablename__ = "tasks"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    #board_id = Column(Integer, ForeignKey("boards.id"), nullable=False)
    status_id = Column(Integer, ForeignKey("task_status.id"), nullable=False)
    #category_id = Column(Integer, ForeignKey("categories.id"), nullable=False)
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
    #board = relationship("Board", back_populates="tasks")
    status = relationship("TaskStatus")
    #category = relationship("Category", back_populates="tasks")
    tags = relationship("Tag", secondary="task_tags", back_populates="tasks")

class RewardType(Base):
    __tablename__ = "reward_types"
    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String, unique=True, nullable=False)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    rewards = relationship("Reward", back_populates="type")

class Reward(Base):
    __tablename__ = "rewards"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    type_id = Column(Integer, ForeignKey("reward_types.id"), nullable=False)
    points_amount = Column(Integer, nullable=False)
    awarded_at = Column(DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP"))
    reason = Column(Text)
    user = relationship("User", back_populates="rewards")
    type = relationship("RewardType", back_populates="rewards")

def init_db():
    Base.metadata.create_all(bind=engine)
    with Session(engine) as db:
        db.execute(text("TRUNCATE TABLE users, reward_types, tasks, task_status, tags, task_tags, rewards, competitions RESTART IDENTITY CASCADE;"))
        db.commit()

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

        if not db.query(User).first():
            users = [
                User(
              first_name="admin",
                    last_name="admin",
                    email="admin@admin.com",
                    password_hash=get_password_hash("maximadmin"),
                    total_points=52,
                    role="admin"
                ),
                User(
                    first_name="u1_name",
                    last_name="u1_lastname",
                    email="u1@user.com",
                    password_hash=get_password_hash("rost_user"),
                    total_points=228,
                    role="user"
                ),
                User(
                    first_name="u2_name",
                    last_name="u2_lastname",
                    email="u2@user.com",
                    password_hash=get_password_hash("rost_user"),
                    total_points=42,
                    role="user"
                ),
                User(
                    first_name="sss",
                    last_name="ssss",
                    email="sss@ss.s",
                    password_hash=get_password_hash("999999"),
                    total_points=32,
                    role="admin"
                ),
                # Добавленные пользователи
                User(
                    first_name="Анна",
                    last_name="Иванова",
                    email="manager@work.com",
                    password_hash=get_password_hash("999999"),
                    total_points=150,
                    role="manager"
                ),
                User(
                    first_name="Дмитрий",
                    last_name="Сидоров",
                    email="dmitry@work.com",
                    password_hash=get_password_hash("999999"),
                    total_points=180,
                    role="user"
                ),
                User(
                    first_name="Елена",
                    last_name="Петрова",
                    email="elena@work.com",
                    password_hash=get_password_hash("password123"),
                    total_points=210,
                    role="user"
                ),
                User(
                    first_name="Михаил",
                    last_name="Козлов",
                    email="mikhail@work.com",
                    password_hash=get_password_hash("password123"),
                    total_points=95,
                    role="user"
                ),
                User(
                    first_name="Ольга",
                    last_name="Смирнова",
                    email="olga@work.com",
                    password_hash=get_password_hash("password123"),
                    total_points=300,
                    role="user"
                ),
                User(
                    first_name="Сергей",
                    last_name="Волков",
                    email="sergey@work.com",

                    password_hash=get_password_hash("password123"),
                    total_points=110,
                    role="user"
                )
            ]
            db.add_all(users)
            db.commit()

            reward_types = [
                RewardType(code="bonus1", name="bonus1"),
                RewardType(code="bonus2", name="bonus2"),
                RewardType(code="bonus3", name="bonus3"),
            ]
            db.add_all(reward_types)
            db.commit()

            if not db.query(Competition).first():
                competitions = [
                    Competition(
                        title="Ирниту марафон 2025",
                        start_date="2025-06-01 00:00:00",
                        end_date="2025-08-31 23:59:59"
                    ),
                    Competition(
                        title="Кучка умников",
                        start_date="2025-01-15 00:00:00",
                        end_date="2025-03-15 23:59:59"
                    ),
                    Competition(
                        title="Майский марафон",
                        start_date="2025-04-20 00:00:00",
                        end_date="2025-05-31 23:59:59"
                    )
                ]
                db.add_all(competitions)
                db.commit()


