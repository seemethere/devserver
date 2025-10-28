import pytest
import kopf
from unittest.mock import MagicMock, AsyncMock

from devservers.operator.devserverflavor.handler import reconcile_devserver_flavor

@pytest.fixture
def reconciler_mock(monkeypatch):
    """ Mocks the DevServerFlavorReconciler to isolate handler logic. """
    mock_reconciler_instance = MagicMock()
    mock_reconciler_instance.reconcile_flavor = AsyncMock()

    mock_reconciler_class = MagicMock(return_value=mock_reconciler_instance)
    monkeypatch.setattr(
        "devservers.operator.devserverflavor.handler.DevServerFlavorReconciler",
        mock_reconciler_class
    )
    return mock_reconciler_instance

@pytest.mark.asyncio
async def test_reconcile_devserver_flavor_no_conflict(monkeypatch, reconciler_mock):
    """
    Tests that a flavor can be set as default when no other default flavor exists.
    """
    spec = {"default": True}
    name = "flavor-1"
    logger = MagicMock()

    get_default_flavor_mock = AsyncMock(return_value=None)
    monkeypatch.setattr(
        "devservers.operator.devserverflavor.handler.get_default_flavor", get_default_flavor_mock
    )

    await reconcile_devserver_flavor(body={}, spec=spec, name=name, logger=logger)

    get_default_flavor_mock.assert_called_once()
    reconciler_mock.reconcile_flavor.assert_called_once()

@pytest.mark.asyncio
async def test_reconcile_devserver_flavor_with_conflict(monkeypatch, reconciler_mock):
    """
    Tests that an error is raised when trying to set a flavor as default
    if another default flavor already exists.
    """
    spec = {"default": True}
    name = "flavor-2"
    logger = MagicMock()
    existing_default_flavor = {"metadata": {"name": "flavor-1"}}

    get_default_flavor_mock = AsyncMock(return_value=existing_default_flavor)
    monkeypatch.setattr(
        "devservers.operator.devserverflavor.handler.get_default_flavor", get_default_flavor_mock
    )

    with pytest.raises(kopf.PermanentError):
        await reconcile_devserver_flavor(body={}, spec=spec, name=name, logger=logger)

    get_default_flavor_mock.assert_called_once()
    reconciler_mock.reconcile_flavor.assert_not_called() # Should fail before reconciling status

@pytest.mark.asyncio
async def test_reconcile_devserver_flavor_self_update(monkeypatch, reconciler_mock):
    """
    Tests that a flavor can be updated when it is already the default flavor.
    """
    spec = {"default": True}
    name = "flavor-1"
    logger = MagicMock()
    existing_default_flavor = {"metadata": {"name": "flavor-1"}}

    get_default_flavor_mock = AsyncMock(return_value=existing_default_flavor)
    monkeypatch.setattr(
        "devservers.operator.devserverflavor.handler.get_default_flavor", get_default_flavor_mock
    )

    await reconcile_devserver_flavor(body={}, spec=spec, name=name, logger=logger)

    get_default_flavor_mock.assert_called_once()
    reconciler_mock.reconcile_flavor.assert_called_once()

@pytest.mark.asyncio
async def test_reconcile_devserver_flavor_not_default(monkeypatch, reconciler_mock):
    """
    Tests that the handler does nothing if the flavor is not set as default.
    """
    spec = {"default": False}
    name = "flavor-1"
    logger = MagicMock()

    get_default_flavor_mock = AsyncMock()
    monkeypatch.setattr(
        "devservers.operator.devserverflavor.handler.get_default_flavor", get_default_flavor_mock
    )

    await reconcile_devserver_flavor(body={}, spec=spec, name=name, logger=logger)

    get_default_flavor_mock.assert_not_called()
    reconciler_mock.reconcile_flavor.assert_called_once()
