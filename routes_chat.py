# routes_chat.py
import re
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
import json
from ml.ai_analyzer import analyze_task_with_commands, analyze_task
from config.db import get_db
from database import User, Task, TaskStatus, Tag, TaskTag
from schemas import TaskResponse
from dependencies import get_current_user



router = APIRouter()


class ChatMessage(BaseModel):
    message: str


class ChatResponse(BaseModel):
    reply: str
    task_created: TaskResponse | None = None


@router.post("/api/chat", response_model=ChatResponse)
def chat_with_ai(
    chat: ChatMessage,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Принимает естественный язык и создаёт задачу.
    Пример: "Создай задачу 'Купить фрукты' на 12.12.2025, статус В работе, тег срочно"
    """
    statuses = [{"code": s.code, "name": s.name} for s in db.query(TaskStatus).all()]
    tags = [t.name for t in db.query(Tag).all()]

    ai_response = analyze_task_with_commands(
        user_message=chat.message,
        available_statuses=statuses,
        available_tags=tags
    )

    if not ai_response.get("commands"):
        return ChatResponse(reply=ai_response["reply"])

    cmd = ai_response["commands"][0]
    if cmd.get("action") != "create_task":
        return ChatResponse(reply="Я пока умею только создавать задачи.")

    task_data = cmd.get("task_data", {})
    title = str(task_data.get("title", "")).strip()
    if not title:
        return ChatResponse(reply="Не удалось определить название задачи.")

    status_code = str(task_data.get("status_code", "todo")).strip()
    status_obj = db.query(TaskStatus).filter(TaskStatus.code == status_code).first()
    if not status_obj:
        fallback_status = db.query(TaskStatus).first()
        if fallback_status:
            status_obj = fallback_status
        else:
            status_obj = TaskStatus(code="todo", name="К выполнению")
            db.add(status_obj)
            db.commit()
            db.refresh(status_obj)

    due_date_raw = task_data.get("due_date")
    due_date = due_date_raw

    description = str(task_data.get("description", "")).strip()
    ai_analysis = analyze_task(title, description)
    estimated_points = ai_analysis["estimated_points"]

    new_task = Task(
        user_id=current_user["user"].id,
        status_id=status_obj.id,
        title=title,
        description=description,
        estimated_points=estimated_points,
        ai_analysis_metadata=ai_analysis,
        due_date=due_date,
        awarded_points=0
    )
    db.add(new_task)
    db.commit()
    db.refresh(new_task)

    attached_tags = []
    for tag_name in task_data.get("tags", []):
        if not isinstance(tag_name, str) or not tag_name.strip():
            continue
        tag_name = tag_name.strip()
        tag = db.query(Tag).filter(Tag.name == tag_name).first()
        if not tag:
            tag = Tag(name=tag_name)
            db.add(tag)
            db.commit()
            db.refresh(tag)
        existing = db.query(TaskTag).filter(
            TaskTag.task_id == new_task.id,
            TaskTag.tag_id == tag.id
        ).first()
        if not existing:
            db.add(TaskTag(task_id=new_task.id, tag_id=tag.id))
            attached_tags.append(tag.name)

    db.commit()

    reply = f" Задача «{title}» создана"
    if due_date:
        reply += f" Срок: {due_date}."
    if attached_tags:
        reply += f" Теги: {', '.join(attached_tags)}."
    reply += f" Статус: {status_obj.name}."

    return ChatResponse(
        reply=ai_response["reply"] + " " + reply,
        task_created=TaskResponse.from_orm(new_task)
    )