
import csv
import getpass
import os
import time
from datetime import datetime, timezone
from pathlib import Path

from google import genai
from google.genai import errors

# Use an environment variable or enter the key securely.
api_key = os.getenv("GEMINI_API_KEY") or getpass.getpass(
    "Gemini API key: "
)

client = genai.Client(api_key=api_key)

LOG_FILE = Path("logs/gemini_diagnostics.csv")
LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

# Choose a model actually returned by your account's list.
MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")


def record(model, result, status, duration, detail=""):
    new_file = not LOG_FILE.exists()

    with LOG_FILE.open("a", newline="") as f:
        writer = csv.writer(f)

        if new_file:
            writer.writerow([
                "timestamp_utc",
                "model",
                "result",
                "http_status",
                "duration_seconds",
                "detail",
            ])

        writer.writerow([
            datetime.now(timezone.utc).isoformat(),
            model,
            result,
            status,
            round(duration, 2),
            detail[:300],
        ])


print("\n1. Checking accessible Gemini models...")

try:
    models = list(client.models.list())

    flash_models = [
        model.name for model in models
        if "flash" in model.name.lower()
    ]

    for name in flash_models:
        print(" ", name)

except errors.APIError as exc:
    print("Model listing failed:", exc.code, exc.message)
    raise SystemExit(1)


print(f"\n2. Testing simple generation with {MODEL}...")

started = time.perf_counter()

try:
    response = client.models.generate_content(
        model=MODEL,
        contents="Reply with exactly: API connection successful.",
    )

    duration = time.perf_counter() - started

    print("SUCCESS")
    print("Duration:", round(duration, 2), "seconds")
    print("Response:", response.text)

    record(MODEL, "success", 200, duration)

except errors.APIError as exc:
    duration = time.perf_counter() - started

    status = exc.code
    message = str(exc.message)

    print("API FAILURE")
    print("HTTP status:", status)
    print("Duration:", round(duration, 2), "seconds")
    print("Reason:", message)

    record(MODEL, "failure", status, duration, message)

except Exception as exc:
    duration = time.perf_counter() - started

    print("LOCAL/NETWORK FAILURE:", type(exc).__name__)

    record(
        MODEL,
        "failure",
        "local_error",
        duration,
        type(exc).__name__,
    )

finally:
    client.close()

print("\nDiagnostic log:", LOG_FILE)
