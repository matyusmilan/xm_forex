import uuid
from enum import Enum
from typing import Optional

from sqlmodel import SQLModel, Field


class OrderStatus(str, Enum):
    PENDING = "PENDING"
    EXECUTED = "EXECUTED"
    CANCELED = "CANCELED"


class OrderBase(SQLModel):
    stoks: str
    quantity: float


class Order(OrderBase, table=True):
    id: int | None = Field(default=None, primary_key=True)
    status: OrderStatus = Field(default=OrderStatus.PENDING)


class OrderPublic(OrderBase):
    id: int


class OrderInput(OrderBase):
    pass


class OrderOutput(Order):
    pass
