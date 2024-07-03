import uuid
from enum import Enum

from sqlmodel import Field, SQLModel


class OrderStatus(str, Enum):
    PENDING = "PENDING"
    EXECUTED = "EXECUTED"
    CANCELED = "CANCELED"


class OrderBase(SQLModel):
    stoks: str
    quantity: float


class Order(OrderBase, table=True):
    id: str | None = Field(default_factory=lambda: uuid.uuid4().hex, primary_key=True)
    status: OrderStatus = Field(default=OrderStatus.PENDING)


class OrderInput(OrderBase):
    pass


class OrderOutput(Order):
    pass
