

from fastapi import FastAPI, Request, Form, Depends, HTTPException
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates

from sqlalchemy.orm import Session

from database import SessionLocal, engine, Base
from models import User, Task

from passlib.context import CryptContext

Base.metadata.create_all(bind=engine)

app = FastAPI()

templates = Jinja2Templates(directory="templates")

pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto"
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# REGISTER PAGE
@app.get("/register", response_class=HTMLResponse)
def register_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="register.html",
        context={}
    )


# REGISTER
@app.post("/register")
def register(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):

    existing_user = db.query(User).filter(
        User.username == username
    ).first()

    if existing_user:
        return templates.TemplateResponse(
            request=request,
            name="register.html",
            context={
                "error": "Username already exists"
            }
        )

    hashed_password = pwd_context.hash(password)

    new_user = User(
        username=username,
        hashed_password=hashed_password
    )

    db.add(new_user)
    db.commit()

    return RedirectResponse(
        url="/login",
        status_code=303
    )


# LOGIN PAGE
@app.get("/login")
def login_page(request: Request):

    return templates.TemplateResponse(
        request=request,
        name="login.html",
        context={}
    )


# LOGIN
@app.post("/login")
def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):

    user = db.query(User).filter(
        User.username == username
    ).first()

    if not user:
        return templates.TemplateResponse(
            request=request,
            name="login.html",
            context={
                "error": "User not found"
            }
        )

    if not pwd_context.verify(
        password,
        user.hashed_password
    ):
        return templates.TemplateResponse(
            request=request,
            name="login.html",
            context={
                "error": "Wrong Password"
            }
        )

    response = RedirectResponse(
        url="/",
        status_code=303
    )

    response.set_cookie(
        key="user_id",
        value=str(user.id),
        httponly=True
    )

    return response


# LOGOUT
@app.get("/logout")
def logout():

    response = RedirectResponse(
        url="/login",
        status_code=303
    )

    response.delete_cookie("user_id")

    return response


# HOME PAGE
@app.get("/", response_class=HTMLResponse)
def home(
    request: Request,
    search: str = "",
    db: Session = Depends(get_db)
):

    user_id = request.cookies.get("user_id")

    if not user_id:
        return RedirectResponse(
            url="/login",
            status_code=303
        )

    user = db.query(User).filter(
        User.id == int(user_id)
    ).first()

    tasks_query = db.query(Task).filter(
    Task.owner_id == int(user_id)
)
    if search:
        tasks_query = tasks_query.filter(
            Task.title.contains(search)
        )

    tasks = tasks_query.all()
    total_tasks = len(tasks)

    completed_tasks = len(
        [task for task in tasks if task.completed]
    )

    progress = 0

    if total_tasks > 0:
        progress = int(
            (completed_tasks / total_tasks) * 100
        )

    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "user": user,
            "tasks": tasks,
            "search": search,
            "total_tasks": total_tasks,
            "completed_tasks": completed_tasks,
            "progress": progress
        }
    )


# ADD TASK PAGE
@app.get("/add-task", response_class=HTMLResponse)
def add_task_page(request: Request):

    return templates.TemplateResponse(
        request=request,
        name="add_task.html",
        context={}
    )

# CREATE TASK
@app.post("/tasks")
def create_task(
    request: Request,
    title: str = Form(...),
    description: str = Form(""),
    category: str = Form(""),
    deadline: str = Form(""),
    priority: str = Form("Medium"),
    db: Session = Depends(get_db)
):

    user_id = request.cookies.get("user_id")

    if not user_id:
        return RedirectResponse(
            url="/login",
            status_code=303
        )

    task = Task(
        title=title,
        description=description,
        category=category,
        deadline=deadline,
        priority=priority,
        owner_id=int(user_id)
    )

    db.add(task)
    db.commit()

    return RedirectResponse(
        url="/",
        status_code=303
    )


# COMPLETE TASK
@app.post("/tasks/{task_id}/toggle")
def toggle_task(
    task_id: int,
    request: Request,
    db: Session = Depends(get_db)
):

    task = db.query(Task).filter(
        Task.id == task_id
    ).first()

    if task:
        task.completed = not task.completed
        db.commit()

    return RedirectResponse(
        url="/",
        status_code=303
    )


# DELETE TASK
@app.post("/tasks/{task_id}/delete")
def delete_task(
    task_id: int,
    db: Session = Depends(get_db)
):

    task = db.query(Task).filter(
        Task.id == task_id
    ).first()

    if task:
        db.delete(task)
        db.commit()

    return RedirectResponse(
        url="/",
        status_code=303
    )

# EDIT TASK PAGE
@app.get("/tasks/{task_id}/edit", response_class=HTMLResponse)
def edit_task_page(
    task_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    task = db.query(Task).filter(Task.id == task_id).first()

    return templates.TemplateResponse(
        request=request,
        name="edit_task.html",
        context={
            "task": task
        }
    )


# UPDATE TASK
@app.post("/tasks/{task_id}/edit")
def update_task(
    task_id: int,
    title: str = Form(...),
    description: str = Form(""),
    category: str = Form(""),
    deadline: str = Form(""),
    priority: str = Form("Medium"),
    db: Session = Depends(get_db)
):

    task = db.query(Task).filter(Task.id == task_id).first()

    task.title = title
    task.description = description
    task.category = category
    task.deadline = deadline
    task.priority = priority

    db.commit()

    return RedirectResponse(
        url="/",
        status_code=303
    )