from fastapi import FastAPI, HTTPException, status, Depends
from typing import Optional, List
from sqlmodel import Field, SQLModel, create_engine, Session, select
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
import jwt
from passlib.context import CryptContext

# ---------------------------------------------------------
# SECURITY CONFIGURATION
# ---------------------------------------------------------
SECRET_KEY = "super-secret-key-change-this-in-production"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

# 1. Database Connection & Engine Setup
sqlite_file_name = "ecommerce.db"
sqlite_url = f"sqlite:///{sqlite_file_name}"

engine = create_engine(sqlite_url, echo=True)

def create_db_and_tables():
    SQLModel.metadata.create_all(engine)

def get_session():
    with Session(engine) as session:
        yield session

@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    yield

app = FastAPI(lifespan=lifespan)

# USER MODELS & SCHEMAS
class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(index=True, unique=True)
    hashed_password: str
    role: str = Field(default="user")  # "user" or "admin"

class UserRegister(SQLModel):
    username: str
    password: str
    role: Optional[str] = "user"

class UserResponse(SQLModel):
    id: int
    username: str
    role: str

# ---------------------------------------------------------
# PASSWORD & TOKEN HELPERS
# ---------------------------------------------------------
def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

# ---------------------------------------------------------
# AUTH DEPENDENCIES
# ---------------------------------------------------------
def get_current_user(
    token: str = Depends(oauth2_scheme), 
    session: Session = Depends(get_session)
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except jwt.PyJWTError:
        raise credentials_exception

    statement = select(User).where(User.username == username)
    user = session.exec(statement).first()
    if user is None:
        raise credentials_exception
    return user

def require_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required"
        )
    return current_user


# ---------------------------------------------------------
# AUTH ROUTES
# ---------------------------------------------------------
@app.post("/register", response_model=UserResponse)
def register(user_data: UserRegister, session: Session = Depends(get_session)):
    # 1. Check if username already exists in SQLite
    statement = select(User).where(User.username == user_data.username)
    if session.exec(statement).first():
        raise HTTPException(status_code=400, detail="Username already registered")
    
    # 2. Hash raw password and create new User database row
    new_user = User(
        username=user_data.username,
        hashed_password=hash_password(user_data.password),
        role=user_data.role if user_data.role in ["user", "admin"] else "user"
    )
    session.add(new_user)
    session.commit()
    session.refresh(new_user)
    
    # 3. Return user (filtered by UserResponse to exclude hashed_password)
    return new_user

@app.post("/login")
def login(
    form_data: OAuth2PasswordRequestForm = Depends(), 
    session: Session = Depends(get_session)
):
    # 1. Look up user by username in SQLite
    statement = select(User).where(User.username == form_data.username)
    user = session.exec(statement).first()
    
    # 2. Verify password hash
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Incorrect username or password")
    
    # 3. Create signed 60-minute JWT token
    access_token = create_access_token(data={"sub": user.username, "role": user.role})
    return {"access_token": access_token, "token_type": "bearer"}

# 2. Database Models & Schemas
class ProductCreate(SQLModel):
    Title: str
    Price: float
    Stock: int

# Database Table Model
class Product(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    Title: str
    Price: float
    Stock: int
    Stock: int

class OrderCreate(SQLModel):
    Product_id: int
    Quantity: int

class Order(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    Product_id: int = Field(foreign_key="product.id")
    Quantity: int
    Total: float


# 1. CREATE PRODUCT
@app.post('/product', dependencies=[Depends(require_admin)])
def create_product(product_data: ProductCreate, session: Session = Depends(get_session)):
    db_product = Product.model_validate(product_data)
    session.add(db_product)
    session.commit()
    session.refresh(db_product)
    return db_product

# 2. GET ALL PRODUCTS (with optional max_price filter)
@app.get('/product')
def get_all_product(max_price: Optional[float] = None, session: Session = Depends(get_session)):
    statement = select(Product)
    if max_price is not None:
        statement = statement.where(Product.Price <= max_price)
    
    products = session.exec(statement).all()
    return products

# 3. GET PRODUCT BY ID
@app.get('/product/{product_id}')
def read_id(product_id: int, session: Session = Depends(get_session)):
    product = session.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product

# 4. UPDATE / RESTOCK PRODUCT
@app.put('/product/{product_id}', dependencies=[Depends(require_admin)])
def update_product(product_id: int, updated_data: ProductCreate, session: Session = Depends(get_session)):
    db_product = session.get(Product, product_id)
    if not db_product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    db_product.Title = updated_data.Title
    db_product.Price = updated_data.Price
    db_product.Stock += updated_data.Stock  # Additive restock
    
    session.add(db_product)
    session.commit()
    session.refresh(db_product)
    return db_product 

# 5. DELETE PRODUCT
@app.delete('/product/{product_id}', dependencies=[Depends(require_admin)])
def delete_product(product_id: int, session: Session = Depends(get_session)):
    db_product = session.get(Product, product_id)
    if not db_product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    session.delete(db_product)
    session.commit()
    return {"message": f"Product {product_id} deleted successfully"}

# ==========================================
# ORDER ENDPOINTS (SQLite + SQLModel)
# ==========================================

# 1. CREATE ORDER
@app.post('/order')
def create_order(order_data: OrderCreate, 
                 session: Session = Depends(get_session), 
                 current_user: User = Depends(get_current_user)): # Enforces that the user is logged in
    # Fetch product from SQLite database
    product = session.get(Product, order_data.Product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Check inventory availability
    if product.Stock < order_data.Quantity:
        raise HTTPException(status_code=400, detail="Insufficient stock")
    
    # Deduct stock from product
    product.Stock -= order_data.Quantity
    session.add(product)
    
    # Calculate total securely on backend
    calculated_total = product.Price * order_data.Quantity
    
    # Build and commit Order database model
    db_order = Order(
        Product_id=order_data.Product_id,
        Quantity=order_data.Quantity,
        Total=calculated_total
    )
    session.add(db_order)
    session.commit()
    session.refresh(db_order)
    
    # Return custom response body with Product details
    return {
        "id": db_order.id,
        "Product_id": db_order.Product_id,
        "Product_title": product.Title,
        "Unit_price": product.Price,
        "Quantity": db_order.Quantity,
        "Total": db_order.Total
    }


# 2. GET ALL ORDERS
@app.get('/order')
def get_all_orders(session: Session = Depends(get_session)):
    orders = session.exec(select(Order)).all()
    
    response = []
    for order in orders:
        product = session.get(Product, order.Product_id)
        response.append({
            "id": order.id,
            "Product_id": order.Product_id,
            "Product_title": product.Title if product else "Unknown Product",
            "Quantity": order.Quantity,
            "Total": order.Total
        })
        
    return response


# 3. GET ORDER BY ID
@app.get('/order/{order_id}')
def get_order_by_id(order_id: int, session: Session = Depends(get_session)):
    order = session.get(Order, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    # Fetch the linked product details from SQLite
    product = session.get(Product, order.Product_id)
    
    return {
        "id": order.id,
        "Product_id": order.Product_id,
        "Product_title": product.Title if product else "Unknown Product",
        "Quantity": order.Quantity,
        "Total": order.Total
    }

# 4. UPDATE ORDER (QUANTITY ADJUSTMENT & STOCK SYNCHRONIZATION)
@app.put('/order/{order_id}')
def update_order(order_id: int, updated_data: OrderCreate, session: Session = Depends(get_session)):
    # Fetch target order
    db_order = session.get(Order, order_id)
    if not db_order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    # Guard against product swapping
    if updated_data.Product_id != db_order.Product_id:
        raise HTTPException(status_code=400, detail="Changing Product ID on an existing order is not allowed")
    
    # Fetch linked product
    product = session.get(Product, db_order.Product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product no longer exists")
    
    # Calculate change in quantity (Delta)
    quantity_diff = updated_data.Quantity - db_order.Quantity
    
    # Adjust stock based on difference
    if quantity_diff > 0:
        if product.Stock < quantity_diff:
            raise HTTPException(status_code=400, detail="Insufficient stock to increase order quantity")
        product.Stock -= quantity_diff
    elif quantity_diff < 0:
        product.Stock += abs(quantity_diff)
        
    # Recalculate order total and update quantity
    db_order.Quantity = updated_data.Quantity
    db_order.Total = product.Price * updated_data.Quantity
    
    # Stage changes and commit transaction
    session.add(product)
    session.add(db_order)
    session.commit()
    session.refresh(db_order)
    
    return db_order


# 5. DELETE ORDER (CANCELLATION & STOCK RESTORATION)
@app.delete('/order/{order_id}')
def delete_order(order_id: int, session: Session = Depends(get_session)):
    # Fetch target order
    db_order = session.get(Order, order_id)
    if not db_order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    # Restore stock to corresponding product
    product = session.get(Product, db_order.Product_id)
    if product:
        product.Stock += db_order.Quantity
        session.add(product)
        
    # Remove order record from database
    session.delete(db_order)
    session.commit()
    
    return {
        "message": f"Order {order_id} canceled successfully",
        "restored_quantity": db_order.Quantity
    }