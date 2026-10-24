"""The one place that connects to Temporal, always with the Pydantic data converter."""

from temporalio.client import Client
from temporalio.contrib.pydantic import pydantic_data_converter

from cairn.settings import Settings


async def connect(settings: Settings) -> Client:
    return await Client.connect(
        settings.temporal_address,
        namespace=settings.temporal_namespace,
        data_converter=pydantic_data_converter,
    )
