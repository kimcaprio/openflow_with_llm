"""
NiFi Integration Package

This package contains modules for integrating with Apache NiFi.
"""

from .api_client import NiFiAPIClient, NiFiConnectionConfig, create_nifi_client

__all__ = [
    "NiFiAPIClient",
    "NiFiConnectionConfig", 
    "create_nifi_client"
]
