"""Quick import verification — run with: python scripts/verify_imports.py"""
import sys, importlib

results = {}
packages = [
    "fastapi", "pydantic", "pydantic_settings", "sqlalchemy",
    "alembic", "redis", "structlog", "jose", "passlib",
    "prometheus_client", "httpx", "orjson", "starlette",
]

for pkg in packages:
    try:
        m = importlib.import_module(pkg)
        results[pkg] = getattr(m, "__version__", "ok")
    except ImportError as e:
        results[pkg] = f"MISSING: {e}"

print("\n=== Dependency Check ===")
failed = []
for pkg, status in results.items():
    icon = "✓" if "MISSING" not in str(status) else "✗"
    print(f"  {icon} {pkg}: {status}")
    if "MISSING" in str(status):
        failed.append(pkg)

print()
if failed:
    print(f"MISSING: {', '.join(failed)}")
    sys.exit(1)
else:
    print("All dependencies present.")
    sys.exit(0)
