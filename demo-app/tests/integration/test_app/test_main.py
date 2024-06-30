import pytest
from starlette.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

from demo_app.main import app, get_session
from demo_app.models import OrderStatus, Order, OrderInput, OrderBase


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
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


def test_health_check(client: TestClient):
    """
        GIVEN
        WHEN health check endpoint is called with GET method
        THEN response with status 200 and body OK is returned
    """
    response = client.get("/health-check/")
    assert response.status_code == 200
    assert response.json() == {"message": "OK"}


def test_place_order(client: TestClient):
    response = client.post("/orders/", json={"stoks": "EURUSD", "quantity": 666})
    data = response.json()

    assert response.status_code == 201
    assert data["stoks"] == "EURUSD"
    assert data["quantity"] == 666
    assert data["id"] is not None
    assert data["status"] == OrderStatus.PENDING.value


def test_place_order_incomplete(client: TestClient):
    # No quantity
    response = client.post("/orders/", json={"stoks": "EURUSD"})
    data = response.json()
    assert response.status_code == 422
    assert data['detail'][0]['msg'] == 'Field required'


@pytest.mark.parametrize(
    "stoks, quantity, error_msg",
    [
        pytest.param(
            666,
            666,
            "Input should be a valid string",
            id="stoks"
        ),
        pytest.param(
            "EURUSD",
            "not-a-number",
            "Input should be a valid number, unable to parse string as a number",
            id="quantity"
        ),
    ],
)
def test_place_order_invalid(client: TestClient, stoks, quantity, error_msg):
    response = client.post("/orders/", json={"stoks": stoks, "quantity": quantity})
    assert response.status_code == 422
    data = response.json()
    assert data['detail'][0]['msg'] == error_msg


def test_get_orders(session: Session, client: TestClient):
    order_1 = Order(id=1,status=OrderStatus.PENDING,stoks="USDCHF",quantity="1234")
    order_2 = Order(id=2, status=OrderStatus.PENDING, stoks="EURGBP", quantity="12.34")
    session.add(order_1)
    session.add(order_2)
    session.commit()

    response = client.get("/orders/")
    data = response.json()

    assert response.status_code == 200

    assert len(data) == 2

    assert data[0]["status"] == order_1.status
    assert data[0]["stoks"] == order_1.stoks
    assert data[0]["quantity"] == order_1.quantity
    assert data[0]["id"] == order_1.id

    assert data[1]["status"] == order_2.status
    assert data[1]["stoks"] == order_2.stoks
    assert data[1]["quantity"] == order_2.quantity
    assert data[1]["id"] == order_2.id


def test_get_orders_empty(client: TestClient):
    response = client.get("/orders/")
    data = response.json()

    assert response.status_code == 200
    assert len(data) == 0


def test_get_order(session: Session, client: TestClient):
    order_1 = Order(id=1, status=OrderStatus.PENDING, stoks="USDCHF", quantity="1234")
    session.add(order_1)
    session.commit()

    response = client.get(f"/orders/{order_1.id}")
    data = response.json()

    assert response.status_code == 200

    assert data["id"] == order_1.id
    assert data["status"] == order_1.status
    assert data["stoks"] == order_1.stoks
    assert data["quantity"] == order_1.quantity


def test_get_order_empty(session: Session, client: TestClient):
    response = client.get(f"/orders/1")
    data = response.json()

    assert response.status_code == 404
    assert data['detail'] == 'Order not found'


def test_get_order_non_exist_id(session: Session, client: TestClient):
    order_1 = Order(id=1, status=OrderStatus.PENDING, stoks="USDCHF", quantity="1234")
    session.add(order_1)
    session.commit()

    response = client.get(f"/orders/2")
    data = response.json()

    assert response.status_code == 404
    assert data['detail'] == 'Order not found'


def test_delete_order(session: Session, client: TestClient):
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


def test_delete_order_non_exist_id(session: Session, client: TestClient):
    order_1 = Order(id=1, status=OrderStatus.PENDING, stoks="USDCHF", quantity="1234")
    session.add(order_1)
    session.commit()

    response = client.delete(f"/orders/2")
    data = response.json()

    assert response.status_code == 404
    assert data['detail'] == 'Order not found'
