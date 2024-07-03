import time
from contextlib import asynccontextmanager
from typing import Sequence

from fastapi import (
    Depends,
    FastAPI,
    HTTPException,
    Query,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.openapi.docs import get_redoc_html, get_swagger_ui_html
from fastapi.openapi.utils import get_openapi
from fastapi.responses import HTMLResponse
from sqlmodel import Session, select
from starlette import status

from demo_app.database import create_db_and_tables, drop_all_tables, engine
from demo_app.models import Order, OrderInput, OrderOutput, OrderStatus
from demo_app.utils import get_random_delay


class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)


manager = ConnectionManager()


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
    description="A RESTful API to simulate a Forex trading platform with "
    "WebSocket support for real-time order updates.",
    version="1.0.0",
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)

html = """
<!DOCTYPE html>
<html>
    <head>
        <title>Orders</title>
    </head>
    <body>
        <h1>Add an Order</h1>
        <h2>Your ID: <span id="ws-id"></span></h2>
        <form action="" onsubmit="sendMessage(event)">
            stoks <input type="text" id="stoks" autocomplete="off"/>
            quantity <input type="text" id="quantity" autocomplete="off"/>
            <button>Send</button>
        </form>
        <hr>
        <ul id='messages'>
        </ul>
        <script>
            var client_id = Date.now()
            document.querySelector("#ws-id").textContent = client_id;
            var ws = new WebSocket(`ws://127.0.0.1:8080/ws/${client_id}`);
            ws.onmessage = function(event) {
                var messages = document.getElementById('messages')
                var message = document.createElement('li')
                var content = document.createTextNode(event.data)
                message.appendChild(content)
                messages.appendChild(message)
            };
            function sendMessage(event) {
                var stoks = document.getElementById("stoks")
                var quantity = document.getElementById("quantity")
                ws.send(
                    JSON.stringify(
                        {stoks: stoks.value, quantity: quantity.value}
                    )
                )
                stoks.value = ''
                quantity.value = ''
                event.preventDefault()
            }
        </script>
    </body>
</html>
"""


# Route to root - websocket client
@app.get("/")
async def get_root():
    return HTMLResponse(html)


# Route to get Swagger documentation
@app.get(path="/docs", include_in_schema=False)
async def get_swagger_documentation():
    return get_swagger_ui_html(openapi_url="/openapi.json", title="docs")


# Route to get Redoc documentation
@app.get(path="/redoc", include_in_schema=False)
async def get_redoc_documentation():
    return get_redoc_html(openapi_url="/openapi.json", title="docs")


# Route to get the OpenAPI JSON schema
@app.get(path="/openapi.json", include_in_schema=False)
async def openapi():
    return get_openapi(
        title=app.title,
        version=app.version,
        routes=app.routes,
        description=app.description,
    )


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
    },
)
async def get_orders(
    *,
    session: Session = Depends(get_session),
    offset: int = 0,
    limit: int = Query(default=100, le=100),
) -> Sequence[Order]:
    """
    List of Orders with optional pagination.
    - **offset**: (optional) Offset of orders in result list.
    It is non-negative integer (Default: 0)
    - **limit**: (optional)  Quantity of the currency pair to be traded.
    It is integer between 0 and 100. (Default: 100)
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
    operation_id="getOrder",
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
    operation_id="placeOrder",
)
async def place_order(
    *, session: Session = Depends(get_session), order_input: OrderInput
):
    """
    Create an Order with all the information:

    - **order_id**: generated id of order (UUID).
    - **stoks**: (required) Currency pair symbol (e.g. 'EURUSD').
    - **quantity**: (required) Quantity of the currency pair to be traded.
    - **status**: Status of the order.
    One of  [pending, executed, canceled] list.
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
    operation_id="cancelOrder",
)
async def delete_order(*, session: Session = Depends(get_session), order_id: str):
    """
    Cancel an Order.
    If order with <order_id> is exiting then the status will be CANCELLED.
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
    operation_id="healthCheck",
)
async def health_check():
    """
    Health check endpoint for maintenance.
    """
    return {"message": "OK"}


@app.websocket("/ws/{client_id}")
async def websocket_endpoint(
    websocket: WebSocket, client_id: int, session: Session = Depends(get_session)
):
    await manager.connect(websocket)
    try:
        await manager.send_personal_message("Connection...", websocket)
        while True:
            data = await websocket.receive_json()
            order = await place_order(session=session, order_input=data)
            message = f"ORDER_ID: {order.id}. STATUS: {order.status}'"
            await manager.send_personal_message(message, websocket)
            await manager.broadcast(f"Client #{client_id} says: {data}")
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        await manager.broadcast(f"Client #{client_id} left the chat")
