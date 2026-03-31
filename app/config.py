import os

SALES_EXPERT_BASE_URL = os.getenv(
    "SALES_EXPERT_BASE_URL",
    "http://localhost:8015"
)
TIMEOUT_SECONDS = int(os.getenv("PLUGIN_TIMEOUT_SECONDS", "30"))
