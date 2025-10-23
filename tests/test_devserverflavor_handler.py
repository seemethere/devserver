import pytest
import kopf
from unittest.mock import MagicMock, AsyncMock

from devserver.operator.devserverflavor.handler import ensure_single_default_flavor

@pytest.mark.asyncio
async def test_ensure_single_default_flavor_no_conflict(monkeypatch):
    """
    Tests that a flavor can be set as default when no other default flavor exists.
    """
    spec = {"default": True}
    name = "flavor-1"
    logger = MagicMock()

    # Mock get_default_flavor to return None, indicating no default flavor exists
    get_default_flavor_mock = AsyncMock(return_value=None)
    monkeypatch.setattr(
        "devserver.operator.devserverflavor.handler.get_default_flavor", get_default_flavor_mock
    )

    # The handler should run without raising an exception
    await ensure_single_default_flavor(spec=spec, name=name, logger=logger)
    get_default_flavor_mock.assert_called_once()


@pytest.mark.asyncio
async def test_ensure_single_default_flavor_with_conflict(monkeypatch):
    """
    Tests that an error is raised when trying to set a flavor as default
    if another default flavor already exists.
    """
    spec = {"default": True}
    name = "flavor-2"
    logger = MagicMock()
    existing_default_flavor = {
        "metadata": {"name": "flavor-1"},
        "spec": {"default": True}
    }

    # Mock get_default_flavor to return an existing default flavor
    get_default_flavor_mock = AsyncMock(return_value=existing_default_flavor)
    monkeypatch.setattr(
        "devserver.operator.devserverflavor.handler.get_default_flavor", get_default_flavor_mock
    )

    # The handler should raise a PermanentError
    with pytest.raises(kopf.PermanentError):
        await ensure_single_default_flavor(spec=spec, name=name, logger=logger)
    
    get_default_flavor_mock.assert_called_once()


@pytest.mark.asyncio
async def test_ensure_single_default_flavor_self_update(monkeypatch):
    """
    Tests that a flavor can be updated when it is already the default flavor.
    """
    spec = {"default": True}
    name = "flavor-1"
    logger = MagicMock()
    existing_default_flavor = {
        "metadata": {"name": "flavor-1"},
        "spec": {"default": True}
    }

    # Mock get_default_flavor to return the same flavor
    get_default_flavor_mock = AsyncMock(return_value=existing_default_flavor)
    monkeypatch.setattr(
        "devserver.operator.devserverflavor.handler.get_default_flavor", get_default_flavor_mock
    )

    # The handler should run without raising an exception
    await ensure_single_default_flavor(spec=spec, name=name, logger=logger)
    get_default_flavor_mock.assert_called_once()


@pytest.mark.asyncio
async def test_ensure_single_default_flavor_not_default(monkeypatch):
    """
    Tests that the handler does nothing if the flavor is not set as default.
    """
    spec = {"default": False}
    name = "flavor-1"
    logger = MagicMock()

    # We don't need to mock get_default_flavor as it should not be called
    get_default_flavor_mock = AsyncMock()
    monkeypatch.setattr(
        "devserver.operator.devserverflavor.handler.get_default_flavor", get_default_flavor_mock
    )

    await ensure_single_default_flavor(spec=spec, name=name, logger=logger)
    get_default_flavor_mock.assert_not_called()
