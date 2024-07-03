import pytest
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool
from starlette.testclient import TestClient

from demo_app.main import app, get_session
from demo_app.models import Order, OrderInput, OrderStatus

NOT_A_NUMER = "not-a-number"
DEFAULT_ORDER_STATUS = OrderStatus.PENDING


def mock_delay():
    pass


@pytest.fixture(name="session")
def session_fixture():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


@pytest.fixture(name="client")
def client_fixture(session: Session):
    def get_session_override():
        return session

    app.dependency_overrides[get_session] = get_session_override
    client = TestClient(app=app)
    yield client
    app.dependency_overrides.clear()


@pytest.mark.anyio
async def test_health_check(client: TestClient):
    """
    GIVEN client for testing
    WHEN health check endpoint is called with GET method
    THEN response with status 200
    AND body OK is returned
    """
    response = client.get("/health-check/")
    assert response.status_code == 200
    assert response.json() == {"message": "OK"}


@pytest.mark.anyio
async def test_get_root(client: TestClient):
    """
    GIVEN client for testing
    WHEN / endpoint is called with GET method
    THEN response with status 200
    AND content type is text/html; charset=utf-8
    """
    response = client.get("/")
    assert response.status_code == 200
    assert response.headers["Content-Type"] == "text/html; charset=utf-8"


@pytest.mark.anyio
async def test_place_order(client: TestClient, monkeypatch):
    """
    GIVEN client for testing
    WHEN /orders endpoint is called with POST method
    THEN response with status 201
    AND the content is equal the inserted element parameters
    """
    monkeypatch.setattr("demo_app.main.delay", mock_delay)
    response = client.post("/orders/", json={"stoks": "EURUSD", "quantity": 66.6})
    data = response.json()

    assert response.status_code == 201
    assert data["stoks"] == "EURUSD"
    assert data["quantity"] == 66.6
    assert data["id"] is not None
    assert data["status"] == OrderStatus.EXECUTED


@pytest.mark.anyio
async def test_place_order_incomplete(client: TestClient, monkeypatch):
    """
    GIVEN client for testing
    WHEN /orders endpoint is called with POST method without a required parameter (quantity)
    THEN response with status 422
    AND the content has a 'Field required' message
    """
    monkeypatch.setattr("demo_app.main.delay", mock_delay)
    response = client.post("/orders/", json={"stoks": "EURUSD"})
    data = response.json()
    assert response.status_code == 422
    assert data["detail"][0]["msg"] == "Field required"


@pytest.mark.parametrize(
    "stoks, quantity, error_msg",
    [
        pytest.param(666, 666, "Input should be a valid string", id="stoks_is_invalid"),
        pytest.param(
            "EURUSD",
            NOT_A_NUMER,
            "Input should be a valid number, unable to parse string as a number",
            id="quantity_is_invalid",
        ),
    ],
)
@pytest.mark.anyio
async def test_place_order_invalid(
    client: TestClient, stoks, quantity, error_msg, monkeypatch
):
    """
    GIVEN client for testing
    WHEN /orders endpoint is called with POST method and the stoks is invalid [id=stoks_is_invalid]
    THEN response with status 422 [id=stoks_is_invalid]
    AND the content has the error message [id=stoks_is_invalid]
    WHEN /orders endpoint is called with POST method and the quantity is invalid [id=quantity_is_invalid]
    THEN response with status 422 [id=quantity_is_invalid]
    AND the content has the error message [id=quantity_is_invalid]
    """
    monkeypatch.setattr("demo_app.main.delay", mock_delay)
    response = client.post("/orders/", json={"stoks": stoks, "quantity": quantity})
    assert response.status_code == 422
    data = response.json()
    assert data["detail"][0]["msg"] == error_msg


@pytest.mark.anyio
async def test_get_orders(session: Session, client: TestClient, monkeypatch):
    """
    GIVEN client for testing
    AND two inserted orders in DB
    WHEN /orders endpoint is called with GET method
    THEN response with status 200
    AND the content has 2 inserted orders
    """
    monkeypatch.setattr("demo_app.main.delay", mock_delay)
    order_input_1 = OrderInput(stoks="USDCHF", quantity="1234")
    order_input_2 = OrderInput(stoks="EURGBP", quantity="12.34")
    db_order_1 = Order.model_validate(order_input_1)
    session.add(db_order_1)
    db_order_2 = Order.model_validate(order_input_2)
    session.add(db_order_2)
    session.commit()

    response = client.get("/orders/")
    data = response.json()

    assert response.status_code == 200

    assert len(data) == 2

    assert data[0]["status"] == OrderStatus.PENDING
    assert data[0]["stoks"] == order_input_1.stoks
    assert data[0]["quantity"] == order_input_1.quantity
    assert data[0]["id"] is not None

    assert data[1]["status"] == OrderStatus.PENDING
    assert data[1]["stoks"] == order_input_2.stoks
    assert data[1]["quantity"] == order_input_2.quantity
    assert data[1]["id"] is not None


@pytest.mark.anyio
async def test_get_orders_empty(client: TestClient, monkeypatch):
    """
    GIVEN client for testing
    AND the DB is empty
    WHEN /orders endpoint is called with GET method
    THEN response with status 200
    AND data of response is empty
    """
    monkeypatch.setattr("demo_app.main.delay", mock_delay)
    response = client.get("/orders/")
    data = response.json()

    assert response.status_code == 200
    assert len(data) == 0


@pytest.mark.anyio
async def test_get_order(session: Session, client: TestClient, monkeypatch):
    """
    GIVEN client for testing
    AND the DB contains one order
    AND <order_id> of the inserted element is known
    WHEN /orders/<order_id> endpoint is called with GET method
    THEN response with status 200
    AND data of response contains the inserted order parameters
    """
    monkeypatch.setattr("demo_app.main.delay", mock_delay)
    order_input_1 = OrderInput(stoks="USDUSD", quantity="0")
    db_order_1 = Order.model_validate(order_input_1)
    session.add(db_order_1)
    session.commit()
    session.refresh(db_order_1)

    response = client.get(f"/orders/{db_order_1.id}")
    data = response.json()

    assert response.status_code == 200

    assert data["id"] == db_order_1.id
    assert data["status"] == db_order_1.status
    assert data["stoks"] == db_order_1.stoks
    assert data["quantity"] == db_order_1.quantity


@pytest.mark.anyio
async def test_get_order_empty(client: TestClient, monkeypatch):
    """
    GIVEN client for testing
    AND the DB is empty
    WHEN /orders/<order_id> endpoint is called with GET method, the <order_id> is not existing
    THEN response with status 404
    AND the content has a 'Order not found' message
    """
    monkeypatch.setattr("demo_app.main.delay", mock_delay)
    response = client.get("/orders/1")
    data = response.json()

    assert response.status_code == 404
    assert data["detail"] == "Order not found"


@pytest.mark.skip(reason="Order ID changed from integer to string")
@pytest.mark.anyio
async def test_get_order_type_error(client: TestClient):
    response = client.get(f"/orders/{NOT_A_NUMER}")
    data = response.json()

    assert response.status_code == 422
    assert (
        data["detail"][0]["msg"]
        == "Input should be a valid integer, unable to parse string as an integer"
    )


@pytest.mark.anyio
async def test_get_order_non_exist_id(
    session: Session, client: TestClient, monkeypatch
):
    """
    GIVEN client for testing
    AND the DB contains one order
    WHEN /orders/<order_id> endpoint is called with GET method, the <order_id> is not equal with the inserted one
    THEN response with status 404
    AND the content has a 'Order not found' message
    """
    monkeypatch.setattr("demo_app.main.delay", mock_delay)
    order_input_1 = OrderInput(stoks="USDCHF", quantity="1234567")
    db_order_1 = Order.model_validate(order_input_1)
    session.add(db_order_1)
    session.commit()
    session.refresh(db_order_1)

    response = client.get("/orders/0")
    data = response.json()

    assert response.status_code == 404
    assert data["detail"] == "Order not found"


@pytest.mark.anyio
async def test_delete_order(session: Session, client: TestClient, monkeypatch):
    """
    GIVEN client for testing
    AND the DB contains one order
    AND <order_id> of the inserted element is known
    WHEN /orders/<order_id> endpoint is called with DELETE method
    THEN response with status 204
    AND the content has the inserted order with CANCELLED status
    """
    monkeypatch.setattr("demo_app.main.delay", mock_delay)
    order_1 = Order(id=1, status=OrderStatus.PENDING, stoks="USDCHF", quantity="1234")
    session.add(order_1)
    session.commit()

    response = client.delete(f"/orders/{order_1.id}")
    assert response.status_code == 204

    order_in_db = session.get(Order, order_1.id)
    assert order_in_db.status == OrderStatus.CANCELED.value
    assert order_in_db.id == order_1.id
    assert order_in_db.quantity == order_1.quantity
    assert order_in_db.stoks == order_1.stoks


@pytest.mark.anyio
async def test_delete_order_non_exist_id(
    session: Session, client: TestClient, monkeypatch
):
    """
    GIVEN client for testing
    AND the DB contains one order
    WHEN /orders/<order_id> endpoint is called with DELETE method, the <order_id> is not equal with the inserted one
    THEN response with status 404
    AND the content has a 'Order not found' message
    """
    monkeypatch.setattr("demo_app.main.delay", mock_delay)
    order_1 = Order(id=1, status=OrderStatus.PENDING, stoks="USDCHF", quantity="1234")
    session.add(order_1)
    session.commit()

    response = client.delete("/orders/2")
    data = response.json()

    assert response.status_code == 404
    assert data["detail"] == "Order not found"


@pytest.mark.anyio
async def test_docs(client: TestClient):
    """
    GIVEN client for testing
    WHEN /docs endpoint is called with GET method
    THEN response with status 200
    """
    response = client.get("/docs")
    assert response.status_code == 200


@pytest.mark.anyio
async def test_redoc(client: TestClient):
    """
    GIVEN client for testing
    WHEN /redoc endpoint is called with GET method
    THEN response with status 200
    """
    response = client.get("/redoc")
    assert response.status_code == 200


@pytest.mark.anyio
async def test_openapi_json(client: TestClient):
    """
    GIVEN client for testing
    WHEN /openapi.json endpoint is called with GET method
    THEN response with status 200
    """
    response = client.get("/openapi.json")
    assert response.status_code == 200


@pytest.mark.anyio
async def test_non_exist_page(client: TestClient):
    """
    GIVEN client for testing
    WHEN /non_exist invalid endpoint is called with GET method
    THEN response with status 404
    AND the content has a 'Not Found' message
    """
    response = client.get("/non_exist")
    data = response.json()
    assert response.status_code == 404
    assert data["detail"] == "Not Found"


def test_websocket():
    """
    GIVEN
    WHEN /ws/1234 websocket endpoint
    THEN response contains the "Connection..." message
    """
    client = TestClient(app)
    with client.websocket_connect("/ws/1234") as websocket:
        data = websocket.receive_text()
        assert data == "Connection..."
