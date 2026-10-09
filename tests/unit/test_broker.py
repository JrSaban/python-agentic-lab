from taskiq.serializers import JSONSerializer

from src.core import broker as broker_module
from src.core.config import settings


def test_redis_result_backend_serializes_as_json(monkeypatch):
    """The Redis result backend never uses pickle, whose loading executes code."""
    monkeypatch.setattr(settings, "APP_ENV", "production")

    redis_broker = broker_module._build_broker()

    assert isinstance(redis_broker.result_backend.serializer, JSONSerializer)
