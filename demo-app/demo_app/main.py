import time
from typing import Sequence

from fastapi import FastAPI, HTTPException, Depends, Query, WebSocket, WebSocketDisconnect
from websockets.exceptions import ConnectionClosed
from fastapi.openapi.docs import get_swagger_ui_html, get_redoc_html
from fastapi.openapi.utils import get_openapi
from starlette import status

from demo_app.utils import get_random_delay
from demo_app.database import engine, create_db_and_tables, drop_all_tables
from demo_app.models import Order, OrderInput, OrderStatus, OrderOutput

from sqlmodel import Session, select
from contextlib import asynccontextmanager


def delay():
    time.sleep(get_random_delay())


def get_session():  # pragma: no cover
    with Session(engine) as session:
        yield session


@asynccontextmanager
async def lifespan(app: FastAPI):  # pragma: no cover
    create_db_and_tables()
    yield
    drop_all_tables()

app = FastAPI(
    lifespan=lifespan,
    title="Forex Trading Platform API",
    description='A RESTful API to simulate a Forex trading platform with WebSocket support for real-time order updates.',
    version=f"1.0.0",
    docs_url=None,
    redoc_url=None,
    openapi_url=None
)


# Route to get Swagger documentation
@app.get(
    path="/docs",
    include_in_schema=False
)
async def get_swagger_documentation():
    return get_swagger_ui_html(openapi_url="/openapi.json", title="docs")


# Route to get Redoc documentation
@app.get(
    path="/redoc",
    include_in_schema=False
)
async def get_redoc_documentation():
    return get_redoc_html(openapi_url="/openapi.json", title="docs")


# Route to get the OpenAPI JSON schema
@app.get(
    path="/openapi.json",
    include_in_schema=False
)
async def openapi():
    return get_openapi(title=app.title, version=app.version, routes=app.routes, description=app.description)


# Route to getOrders()
@app.get(
    path="/orders",
    summary="Retrieve all orders",
    operation_id="getOrders",
    response_model=list[Order],
    responses={
        200: {
            "description": "A list of orders",
        }
    }
)
async def get_orders(
    *,
    session: Session = Depends(get_session),
    offset: int = 0,
    limit: int = Query(default=100, le=100),
) -> Sequence[Order]:
    """
    List of Orders with optional pagination.
    - **offset**: (optional) Offset of orders in result list. It is non-negative integer (Default: 0)
    - **limit**: (optional)  Quantity of the currency pair to be traded. It is integer between 0 and 100. (Default: 100)
    \f
    :param session: Session.
    :param offset: Offset of orders in result list.
    :param limit: Size of the result list.
    """
    delay()
    orders = session.exec(select(Order).offset(offset).limit(limit)).all()
    return orders


# Route to getOrder()
@app.get(
    path="/orders/{order_id}",
    response_model=OrderOutput,
    summary="Retrieve a specific order",
    operation_id="getOrder"
)
async def get_order(*, session: Session = Depends(get_session), order_id: str):
    """
    Get an Order by id.
    - **order_id**: generated id of order (UUID).
    \f
    :param session: Session.
    :param order_id: Oid of order (UUID).
    """
    delay()
    order = session.get(Order, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order


# Route to placeOrder()
@app.post(
    path="/orders",
    status_code=status.HTTP_201_CREATED,
    summary="Place a new order",
    operation_id="placeOrder"
)
async def place_order(*, session: Session = Depends(get_session), order_input: OrderInput):
    """
    Create an Order with all the information:

    - **order_id**: generated id of order (UUID).
    - **stoks**: (required) Currency pair symbol (e.g. 'EURUSD').
    - **quantity**: (required)  Quantity of the currency pair to be traded.
    - **status**: Status of the order. One of  [pending, executed, canceled] list.
    \f
    :param order_input: Order input.
    :param session: Session.
    """
    # PENDING
    db_order = Order.model_validate(order_input)
    session.add(db_order)
    session.commit()
    session.refresh(db_order)
    # --- something ---
    delay()
    # EXECUTED
    order_data = db_order.model_dump(exclude_unset=True)
    order_data["status"] = OrderStatus.EXECUTED
    db_order.sqlmodel_update(order_data)
    session.add(db_order)
    session.commit()
    session.refresh(db_order)
    return db_order


# Route to cancelOrder()
@app.delete(
    path="/orders/{order_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Cancel an order",
    operation_id="cancelOrder"
)
async def delete_order(*, session: Session = Depends(get_session), order_id: str):
    """
    Cancel an Order. If order with <order_id> is exiting then the status will be CANCELLED.
    - **order_id**: id of order (UUID).
    \f
    :param order_id: id of order (UUID).
    :param session: Session.
    """
    delay()
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


@app.get(
    path="/health-check/",
    summary="Health check for the API maintenance",
    operation_id="healthCheck"
)
async def health_check():
    """
    Health check endpoint for maintenance.
    """
    return {"message": "OK"}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, session: Session = Depends(get_session)):
    # await for connections
    await websocket.accept()

    try:
        # send "Connection established" message to client
        await websocket.send_text("Connection established!")

        # await for messages and send messages
        while True:
            msg = await websocket.receive_json()
            order = await place_order(session=session, order_input=msg)
            await websocket.send_text(f"Your message was: ORDER_ID: {order.id}. STATUS: {order.status}'")

    except (WebSocketDisconnect, ConnectionClosed):
        print("Client disconnected")
