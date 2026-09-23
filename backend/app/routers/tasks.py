from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from shared.constants import Role, TaskStatus
from backend.app.auth import current_user, require_roles
from backend.app.db import Task, User, get_db
from backend.app.events import broker, connection_manager
from backend.app.schemas import Page, TaskCreate, TaskRead, TaskUpdate

router = APIRouter(prefix="/api/v1/tasks", tags=["tasks"])


@router.post("", response_model=TaskRead, status_code=201)
def create_task(payload: TaskCreate, db: Session = Depends(get_db), _: User = Depends(require_roles(Role.ADMIN))) -> Task:
    task = Task(id=f"T{db.query(Task).count() + 1:05d}", **payload.model_dump())
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


@router.get("", response_model=Page[TaskRead])
def list_tasks(status_filter: TaskStatus | None = Query(default=None, alias="status"), limit: int = Query(default=50, ge=1, le=100), cursor: str | None = None, db: Session = Depends(get_db), _: User = Depends(current_user)) -> Page[TaskRead]:
    query = select(Task).order_by(Task.created_at.desc())
    if status_filter:
        query = query.where(Task.status == status_filter)
    if cursor:
        query = query.where(Task.id < cursor)
    tasks = list(db.scalars(query.limit(limit + 1)))
    next_cursor = tasks.pop().id if len(tasks) > limit else None
    return Page[TaskRead](items=tasks, next_cursor=next_cursor)


@router.get("/{task_id}", response_model=TaskRead)
def get_task(task_id: str, db: Session = Depends(get_db), _: User = Depends(current_user)) -> Task:
    task = db.get(Task, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.patch("/{task_id}", response_model=TaskRead)
def edit_task(task_id: str, payload: TaskUpdate, db: Session = Depends(get_db), _: User = Depends(require_roles(Role.ADMIN))) -> Task:
    task = db.get(Task, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(task, field, value)
    db.commit()
    db.refresh(task)
    return task


async def update_task_status(task_id: str, new_status: TaskStatus, db: Session, _: User) -> Task:
    task = db.get(Task, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    task.status = new_status
    db.commit()
    db.refresh(task)
    event = {"type": "task.updated", "data": TaskRead.model_validate(task).model_dump(mode="json")}
    await broker.publish(event)
    if not broker.redis_url:
        await connection_manager.broadcast(event)
    return task


@router.post("/{task_id}/start", response_model=TaskRead)
async def start_task(task_id: str, db: Session = Depends(get_db), user: User = Depends(current_user)) -> Task:
    return await update_task_status(task_id, TaskStatus.IN_PROGRESS, db, user)


@router.post("/{task_id}/complete", response_model=TaskRead)
async def complete_task(task_id: str, db: Session = Depends(get_db), user: User = Depends(current_user)) -> Task:
    return await update_task_status(task_id, TaskStatus.COMPLETED, db, user)
