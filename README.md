# 🛒 E-Commerce REST API (FastAPI + SQLModel + SQLite)

A robust, production-ready RESTful API built with **FastAPI** and **SQLModel** (combining SQLAlchemy ORM and Pydantic validation). The system manages e-commerce products and orders, featuring persistent SQLite database storage, dynamic inventory tracking, and backend-enforced price calculations.

## ✨ Features

- **Database Persistence**: Fully migrated from in-memory storage to SQLite using SQLModel ORM.
- **Strict Payload Validation**: Utilizes separate request schemas (`ProductCreate`, `OrderCreate`) to prevent client-side ID spoofing and ensure clean payload boundaries.
- **Secure Price Calculation**: Order totals are computed strictly on the backend to prevent pricing manipulation.
- **Dynamic Inventory Management**:
  - Restocking (`PUT /product/{id}`) uses additive (`+=`) logic.
  - Order updates adjust product stock dynamically based on quantity deltas.
  - Order cancellations (`DELETE /order/{id}`) automatically restore inventory stock.
- **Relational Integrity**: Foreign keys link orders directly to products.

## 🛠️ Tech Stack

- **Framework**: FastAPI
- **ORM / Database**: SQLModel, SQLAlchemy
- **Database Engine**: SQLite
- **Validation**: Pydantic v2
- **ASGI Server**: Uvicorn

## 🚀 Quick Start

1. **Clone the repository**:
   ```bash
   git clone [https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git](https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git)
   cd YOUR_REPO_NAME