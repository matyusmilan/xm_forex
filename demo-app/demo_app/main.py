import random
import time

from fastapi import FastAPI, HTTPException, Depends, Query
from fastapi.openapi.docs import get_swagger_ui_html, get_redoc_html
from fastapi.openapi.utils import get_openapi
from starlette import status

from .database import engine, create_db_and_tables, drop_all_tables
from .models import Order, OrderInput, OrderStatus, OrderOutput

from sqlmodel import Session, select
from contextlib import asynccontextmanager


def get_session():  # pragma: no cover
    with Session(engine) as session:
        yield session


def wait_random_time():  # pragma: no cover
    # Each endpoint should have a random short delay between 0.1 and 1 second.
    time.sleep(random.randrange(100, 1_000) / 1_000)


@asynccontextmanager
async def lifespan(app: FastAPI):  # pragma: no cover
    create_db_and_tables()
    yield
    drop_all_tables()


app = FastAPI(
    lifespan=lifespan,
    title="Forex Trading Platform API",
    description='A RESTful API to simulate a Forex trading platform with WebSocket support for real-time order updates.',
    version=f"0.0.1",
    docs_url=None,
    redoc_url=None,
    openapi_url=None
)


@app.get("/health-check/")
async def health_check():
    return {"message": "OK"}


# Route to get Swagger documentation
@app.get("/docs", include_in_schema=False)
async def get_swagger_documentation():
    return get_swagger_ui_html(openapi_url="/openapi.json", title="docs")


# Route to get Redoc documentation
@app.get("/redoc", include_in_schema=False)
async def get_redoc_documentation():
    return get_redoc_html(openapi_url="/openapi.json", title="docs")


# Route to get the OpenAPI JSON schema
@app.get("/openapi.json", include_in_schema=False)
async def openapi():
    return get_openapi(title=app.title, version=app.version, routes=app.routes, description=app.description)


@app.post("/orders", status_code=status.HTTP_201_CREATED)
async def place_order(*, session: Session = Depends(get_session), order_input: OrderInput):
    wait_random_time()
    db_order = Order.model_validate(order_input)
    session.add(db_order)
    session.commit()
    session.refresh(db_order)
    return db_order


@app.get("/orders")
async def get_orders(
    *,
    session: Session = Depends(get_session),
    offset: int = 0,
    limit: int = Query(default=100, le=100),
):
    wait_random_time()
    orders = session.exec(select(Order).offset(offset).limit(limit)).all()
    return orders


@app.get("/orders/{order_id}", response_model=OrderOutput)
async def get_order(*, session: Session = Depends(get_session), order_id: int):
    wait_random_time()
    order = session.get(Order, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order


@app.delete("/orders/{order_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_order(*, session: Session = Depends(get_session), order_id: str):
    wait_random_time()
    db_order = session.get(Order, order_id)
    if not db_order:
        raise HTTPException(status_code=404, detail="Order not found")
    order_data = db_order.model_dump(exclude_unset=True)
    order_data["status"] = OrderStatus.CANCELED
    db_order.sqlmodel_update(order_data)
    session.add(db_order)
    session.commit()
    session.refresh(db_order)
    return db_order
