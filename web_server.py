from aiohttp import web

from config import PORT


async def health_check(request: web.Request) -> web.Response:
    """Простой health-check эндпоинт для Render/Railway."""
    return web.json_response({"status": "ok"})


async def start_web_server() -> None:
    """Запускает aiohttp сервер на указанном порту."""
    app = web.Application()
    app.router.add_get("/", health_check)
    app.router.add_get("/health", health_check)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()
    print(f"Health-check server started on port {PORT}")

    # Сервер работает вечно; возвращаем runner, чтобы можно было остановить при 필요
    return runner