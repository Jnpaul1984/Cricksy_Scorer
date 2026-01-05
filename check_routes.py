import asyncio
from httpx import ASGITransport, AsyncClient
from backend.app import create_app


async def test():
    _, app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/openapi.json")
        paths = resp.json()["paths"]
        markers = [p for p in paths if "markers" in p]
        print("Marker routes in test app:")
        for m in markers:
            print(f"  {m}")


asyncio.run(test())
