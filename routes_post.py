@router.post("/task", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
def create_task_single(
        task: TaskCreate,
        current_user: dict = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    """Создает новую задачу для текущего пользователя"""
    if not db.query(TaskStatus).filter(TaskStatus.id == task.status_id).first():
        raise HTTPException(status_code=404, detail="TaskStatus не найден")

    db_task = Task(
        user_id=current_user["user"].id,
        status_id=task.status_id,
        title=task.title,
        description=task.description,
        estimated_points=task.estimated_points or 0,
        ai_analysis_metadata=task.ai_analysis_metadata,
        due_date=task.due_date,
        awarded_points=0
    )
    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    return db_task
