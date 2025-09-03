import inspect
import pytest_asyncio


@pytest_asyncio.fixture(autouse=True)
async def _run_async_setup(request):
    """Автоматически запускает async setup_method у тестовых классов.
    Нужно, потому что pytest по умолчанию не ожидает async setup_method.
    """
    instance = getattr(request.node, "instance", None)
    if instance is None:
        return

    setup = getattr(instance, "setup_method", None)
    if setup is None:
        return

    # Если setup_method является асинхронной функцией — выполнить её
    if inspect.iscoroutinefunction(setup):
        # Выполняем асинхронный setup_method заранее
        await setup()
        # Заменяем его на no-op, чтобы pytest не пытался вызвать корутину синхронно
        def _noop(*args, **kwargs):
            return None
        setattr(instance, "setup_method", _noop)
