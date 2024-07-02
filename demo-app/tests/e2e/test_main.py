import time
from multiprocessing import Process
import pytest
import requests
import uvicorn

from demo_app.main import app
from demo_app.models import OrderStatus, Order


HOST = "127.0.0.1"
PORT = 8080
URL_PREFIX = f"http://{HOST}:{PORT}"


class TestApp:
    def set_up(self):
        """ Bring server up. """
        self.proc = Process(target=uvicorn.run,
                            args=(app,),
                            kwargs={
                                "host": HOST,
                                "port": PORT}
                            )
        self.proc.start()
        time.sleep(0.5)  # time for the server to start

    def tear_down(self):
        """ Shutdown the app. """
        self.proc.terminate()
        time.sleep(0.5)  # time for the server to stop

    @pytest.fixture(name="app_service")
    def app_service_fixture(self):
        self.set_up()
        yield
        self.tear_down()

    def test_health_check(self, app_service):
        """
            GIVEN The API is running (fixture)
            AND DB is empty
            WHEN /health-check endpoint is called with GET method
            THEN response with status 200
            AND content type is application/json
            AND body OK is returned
        """
        response = requests.get(f"{URL_PREFIX}/health-check")

        # Verify status code
        assert response.status_code == 200

        # Verify content-type
        assert response.headers["Content-Type"] == "application/json"

        # Verify response structure
        data = response.json()
        assert data["message"] == "OK"

    def test_place_order(self, app_service):
        """
            GIVEN The API is running (fixture)
            AND DB is empty
            WHEN /orders endpoint is called with POST method
            THEN response with status 201
            AND in response the 'id' is not None
            AND in response the 'stoks' is equal with the input data
            AND in response the 'quantity' is equal with the input data
            AND in response the 'status' is EXECUTED
        """
        order_input = {"stoks": "EURUSD", "quantity": 66.6}
        response = requests.post(f"{URL_PREFIX}/orders/", json=order_input)
        assert response.status_code == 201

        data = response.json()
        assert data["id"] is not None
        assert data["stoks"] == order_input["stoks"]
        assert data["quantity"] == order_input["quantity"]
        assert data["status"] == OrderStatus.EXECUTED

    def test_get_order(self, app_service):
        """
            GIVEN The API is running (fixture)
            AND DB is empty
            WHEN /orders endpoint is called with POST method
            THEN response with status 201
            AND save [order_id] from the response
            WHEN /orders/<order_id> endpoint is called with GET method
            THEN response with status 200
            AND in response the 'id' is equal with the [order_id]
            AND in response the 'stoks' is equal with the input data
            AND in response the 'quantity' is equal with the input data
            AND in response the 'status' is EXECUTED
        """
        # insert
        order_input = {"stoks": "EURUSD", "quantity": 66.6}
        response = requests.post(f"{URL_PREFIX}/orders/", json=order_input)
        assert response.status_code == 201
        order_id = response.json()["id"]

        # get_order_by_id
        response = requests.get(f"{URL_PREFIX}/orders/{order_id}")
        assert response.status_code == 200
        data = response.json()

        assert data["id"] == order_id
        assert data["status"] == OrderStatus.EXECUTED
        assert data["stoks"] == order_input["stoks"]
        assert data["quantity"] == order_input["quantity"]

    def test_get_orders(self, app_service):
        """
            GIVEN The API is running (fixture)
            AND DB is empty
            WHEN /orders endpoint is called with GET method
            THEN response with status 200
            AND data of response is empty
            WHEN /orders endpoint is called with POST method with order_input_1 data
            THEN response with status 201
            WHEN /orders endpoint is called with GET method
            THEN response with status 200
            AND data of response has one element and equals the order_input_1
            WHEN /orders endpoint is called with POST method with order_input_2 data
            THEN response with status 201
            WHEN /orders endpoint is called with GET method
            THEN response with status 200
            AND data of response has two elements and equals the order_input_1 + order_input_2
        """
        # empty
        response = requests.get(f"{URL_PREFIX}/orders/")
        assert response.status_code == 200
        assert len(response.json()) == 0

        # one order
        order_input_1 = {"stoks": "USDCHF", "quantity": "1234"}
        response = requests.post(f"{URL_PREFIX}/orders/", json=order_input_1)
        assert response.status_code == 201

        response = requests.get(f"{URL_PREFIX}/orders/")
        assert response.status_code == 200
        data = response.json()

        assert len(data) == 1

        assert data[0]["status"] == OrderStatus.EXECUTED
        assert data[0]["stoks"] == order_input_1["stoks"]
        assert data[0]["quantity"] == float(order_input_1["quantity"])
        assert data[0]["id"] is not None

        # list of order
        order_input_2 = {"stoks": "CHFUSD", "quantity": "9876"}
        response = requests.post(f"{URL_PREFIX}/orders/", json=order_input_2)
        assert response.status_code == 201

        response = requests.get(f"{URL_PREFIX}/orders/")
        assert response.status_code == 200
        data = response.json()

        assert len(data) == 2

        assert data[0]["status"] == OrderStatus.EXECUTED
        assert data[0]["stoks"] == order_input_1["stoks"]
        assert data[0]["quantity"] == float(order_input_1["quantity"])
        assert data[0]["id"] is not None

        assert data[1]["status"] == OrderStatus.EXECUTED
        assert data[1]["stoks"] == order_input_2["stoks"]
        assert data[1]["quantity"] == float(order_input_2["quantity"])
        assert data[1]["id"] is not None

    @pytest.mark.parametrize(
        "offset, limit, status_code, expected_result",
        [
            pytest.param(
                1,
                1,
                200,
                [1],
                id="one_element"
            ),
            pytest.param(
                3,
                1,
                200,
                [],
                id="empty_result"
            ),
            pytest.param(
                1,
                0,
                200,
                [],
                id="zero_limit"
            ),
            pytest.param(
                1,
                2,
                200,
                [1, 2],
                id="two_element"
            ),
        ],
    )
    def test_get_orders_paging(self, app_service, offset, limit, status_code, expected_result):
        full_result = []
        order_input_1 = {"stoks": "USDCHF", "quantity": "1.123"}
        response = requests.post(f"{URL_PREFIX}/orders/", json=order_input_1)
        order_data = response.json()
        full_result.append(Order(**order_data))
        order_input_2 = {"stoks": "HUFEUR", "quantity": "2.345"}
        response = requests.post(f"{URL_PREFIX}/orders/", json=order_input_2)
        order_data = response.json()
        full_result.append(Order(**order_data))
        order_input_3 = {"stoks": "USDDMK", "quantity": "3.456"}
        response = requests.post(f"{URL_PREFIX}/orders/", json=order_input_3)
        order_data = response.json()
        full_result.append(Order(**order_data))

        response = requests.get(f"{URL_PREFIX}/orders?offset={offset}&limit={limit}")
        assert response.status_code == status_code
        data = response.json()

        if not expected_result:
            assert len(response.json()) == 0
        else:
            for i in range(len(data)):
                result_order = Order(**data[i])
                input_order = full_result[expected_result[i]]
                assert result_order == input_order

    @pytest.mark.parametrize(
        "offset, limit, status_code, error_msg",
        [
            pytest.param(
                "apple",
                1,
                422,
                "Input should be a valid integer, unable to parse string as an integer",
                id="offset_is_string"
            ),
            pytest.param(
                1,
                "apple",
                422,
                "Input should be a valid integer, unable to parse string as an integer",
                id="limit_is_string"
            ),
        ]
    )
    def test_get_orders_paging_invalid_input(self, app_service, offset, limit, status_code, error_msg):
        response = requests.get(f"{URL_PREFIX}/orders?offset={offset}&limit={limit}")
        assert response.status_code == status_code
        data = response.json()
        assert data['detail'][0]['msg'] == error_msg

    def test_delete_order(self, app_service):
        """
            GIVEN The API is running (fixture)
            AND DB is empty
            WHEN /orders endpoint is called with POST method with order_input data
            THEN response with status 201
            AND save [order_id] from the response
            WHEN /orders endpoint is called with DELETE method
            THEN response with status 204
            WHEN /orders/<order_id> endpoint is called with GET method
            THEN response with status 200
            AND in response the 'id' equals [order_id]
            AND in response the 'status' is EXECUTED
            AND data of response equals the order_input
        """
        order_input = {"stoks": "HUFUSD", "quantity": "0012"}
        response = requests.post(f"{URL_PREFIX}/orders/", json=order_input)
        assert response.status_code == 201
        order_id = response.json()["id"]

        response = requests.delete(f"{URL_PREFIX}/orders/{order_id}")
        assert response.status_code == 204

        response = requests.get(f"{URL_PREFIX}/orders/{order_id}")
        assert response.status_code == 200
        data = response.json()

        assert data["status"] == OrderStatus.CANCELED
        assert data["id"] == order_id
        assert data["stoks"] == order_input["stoks"]
        assert data["quantity"] == float(order_input["quantity"])

    def test_docs(self, app_service):
        """
            GIVEN The API is running (fixture)
            WHEN /docs endpoint is called with GET method
            THEN response with status 200
        """
        response = requests.get(f"{URL_PREFIX}/docs")
        assert response.status_code == 200

    def test_redoc(self, app_service):
        """
            GIVEN The API is running (fixture)
            WHEN /redoc endpoint is called with GET method
            THEN response with status 200
        """
        response = requests.get(f"{URL_PREFIX}/redoc")
        assert response.status_code == 200

    def test_openapi_json(self, app_service):
        """
            GIVEN The API is running (fixture)
            WHEN /openapi.json endpoint is called with GET method
            THEN response with status 200
        """
        response = requests.get(f"{URL_PREFIX}/openapi.json")
        assert response.status_code == 200

    def test_non_exist_page(self, app_service):
        """
            GIVEN The API is running (fixture)
            WHEN A non-exists endpoint is called with GET method
            THEN response with status 404 and "Not Found" message
        """
        response = requests.get(f"{URL_PREFIX}/non_exist")
        data = response.json()
        assert response.status_code == 404
        assert data['detail'] == "Not Found"

