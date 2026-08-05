import hashlib
import json
import os
from typing import Any

import numpy as np

from gateway.config import get_settings

SENSITIVE_KEYS = {"password", "token", "secret", "api_key", "authorization", "pat", "private_key"}


def redact_arguments(args: dict[str, Any]) -> dict[str, Any]:
    redacted = {}
    for key, value in args.items():
        if any(s in key.lower() for s in SENSITIVE_KEYS):
            redacted[key] = "***REDACTED***"
        elif isinstance(value, dict):
            redacted[key] = redact_arguments(value)
        else:
            redacted[key] = value
    return redacted
