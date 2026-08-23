"""Client implementations for Amazon APIs."""

from amazon.clients.creators import AmazonCreatorsAPI, AsyncAmazonCreatorsAPI
from amazon.clients.paapi5 import AmazonPAAPI5, AsyncAmazonPAAPI5
from amazon.clients.unified import AmazonAPI, AsyncAmazonAPI

__all__ = [
    "AmazonAPI",
    "AsyncAmazonAPI",
    "AmazonCreatorsAPI",
    "AsyncAmazonCreatorsAPI",
    "AmazonPAAPI5",
    "AsyncAmazonPAAPI5",
]
