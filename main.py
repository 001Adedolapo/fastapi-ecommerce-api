from fastapi import FastAPI
from pydantic import BaseModel, Field
app = FastAPI()

db = []

class Book(BaseModel):
  title: str
  price: float


@app.get('/')
def null():
  return {"Hello world welcome to FastAPI"}


@app.post('/book')
def create(book: Book):
  db.append(book)
  return{'Book': book}

@app.get('/book')
def read_book():
  return{
    'books': db
  }

@app.get('/book/{book_id}')
def get_book_id(book_id: int):
  if book_id < len(db):
    return db[book_id]

@app.put('/book/{book_id}')
def update(book_id: int,  updated_book: Book):
   if book_id < len(db):
    db[book_id] = updated_book
    return {"updated": f"your api has been updated sucessfully {updated_book}"}