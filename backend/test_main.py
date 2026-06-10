from main import app
from app.services import testing

# Temporarily register the Testing Router
app.include_router(testing.router)

print("⚠️ Temporary testing server started!")
print("⚠️ Testing endpoints are ENABLED and registered under /test.")