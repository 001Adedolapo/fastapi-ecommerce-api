from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel

app = FastAPI()

# Task management API

task_db = []

class Task(BaseModel):
  Title : str
  completed: bool

@app.post('/task')
def create_task(task: Task):
  task_db.append(task)
  return task_db

@app.get('/task')
def read_task():
  return task_db

@app.get('/task/{task_id}')
def get_id(task_id: int):
  if task_id >= len(task_db) or task_id < 0:
    raise HTTPException(status_code=404, detail= "Task not found")
  else:
    return task_db[task_id]

@app.put('/task/{task_id}')
def update(task_id: int, update_task: Task):
  if task_id < len(task_db):
    task_db[task_id] = update_task
    return update_task

@app.delete('/task/{task_id}')
def delete_task(task_id: int):
  if task_id < len(task_db):
    task_db.pop(task_id)
    return {"Message": "Task has been deleted successfuflly"}