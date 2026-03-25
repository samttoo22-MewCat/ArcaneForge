"""FastAPI dependency providers."""
from fastapi import Request

from server.broadcast.event_bus import EventBus
from server.db.batch_writer import BatchWriter


def get_graph(request: Request):
    return request.app.state.graph


def get_redis(request: Request):
    return request.app.state.redis


def get_event_bus(request: Request) -> EventBus:
    return request.app.state.event_bus


def get_batch_writer(request: Request) -> BatchWriter:
    return request.app.state.batch_writer


def get_item_master(request: Request) -> dict:
    return request.app.state.item_master
