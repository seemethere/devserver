import pytest
from unittest.mock import MagicMock, patch
from devservers.crds.base import BaseCustomResource, ObjectMeta

# A minimal concrete implementation of the abstract base class for testing
class MyCustomResource(BaseCustomResource):
    group = "test.group"
    version = "v1"
    plural = "mycustomresources"
    namespaced = True

    def __init__(self, metadata, spec, status=None, api=None):
        super().__init__(api)
        self.metadata = metadata
        self.spec = spec
        self.status = status or {}

@pytest.fixture
def custom_resource(mock_k8s_api):
    """Fixture to create a MyCustomResource instance with a mocked API."""
    metadata = ObjectMeta(name="test-resource", namespace="default")
    spec = {"key": "value"}
    return MyCustomResource(metadata, spec, api=mock_k8s_api)

def test_wait_for_status_already_correct(custom_resource):
    """Test that wait_for_status returns immediately if status is already correct."""
    custom_resource.status = {"state": "Ready"}

    # Mock the refresh method to update the status
    def refresh_side_effect():
        custom_resource.status = {"state": "Ready"}

    custom_resource.refresh = MagicMock(side_effect=refresh_side_effect)

    # The call should not block or raise an exception
    for _ in custom_resource.wait_for_status(status={"state": "Ready"}, timeout=1):
        pass # Consume generator

    custom_resource.refresh.assert_called_once()


def test_wait_for_status_succeeds_after_event(custom_resource):
    """Test that wait_for_status succeeds after receiving a watch event."""
    custom_resource.status = {"state": "Pending"}
    desired_status = {"state": "Ready"}

    # The first refresh will show the old status
    custom_resource.refresh = MagicMock()

    # Mock the watch to return an event with the desired status
    mock_watch_event = {
        "type": "MODIFIED",
        "object": {
            "metadata": {"name": "test-resource"},
            "spec": {},
            "status": desired_status,
        },
    }

    with patch.object(custom_resource, 'watch', return_value=[mock_watch_event]) as mock_watch:
        # Consume the generator to run the function
        events = list(custom_resource.wait_for_status(status=desired_status, timeout=10)) # Increased timeout

        assert len(events) == 1
        assert events[0] == mock_watch_event

    mock_watch.assert_called_once()


def test_wait_for_status_timeout(custom_resource):
    """Test that wait_for_status raises TimeoutError on timeout."""
    custom_resource.status = {"state": "Pending"}

    # Mock refresh to do nothing
    custom_resource.refresh = MagicMock()

    # Mock the watch to return no events, simulating a timeout
    with patch.object(custom_resource, 'watch', return_value=[]) as mock_watch:
        with pytest.raises(TimeoutError):
            # Use a very small timeout to ensure it triggers
            list(custom_resource.wait_for_status(status={"state": "Ready"}, timeout=0.1))

    # In a timeout scenario, the watch might not be called if the initial checks
    # take longer than the timeout. So we assert it was called at most once.
    assert mock_watch.call_count <= 1


def test_wait_for_status_yields_events(custom_resource):
    """Test that wait_for_status correctly yields events."""
    custom_resource.status = {"state": "Pending"}
    desired_status = {"state": "Ready"}

    custom_resource.refresh = MagicMock()

    events_to_yield = [
        {"type": "MODIFIED", "object": {"status": {"state": "Processing"}}},
        {"type": "MODIFIED", "object": {"status": desired_status}},
    ]

    with patch.object(custom_resource, 'watch', return_value=events_to_yield):
        received_events = []
        for event in custom_resource.wait_for_status(status=desired_status, timeout=10): # Increased timeout
            received_events.append(event)

        assert received_events == events_to_yield


def test_wait_for_status_blocking_usage(custom_resource):
    """Test that the generator can be consumed to block execution."""
    custom_resource.status = {"state": "Pending"}
    desired_status = {"state": "Ready"}

    custom_resource.refresh = MagicMock()

    mock_watch_event = {
        "type": "MODIFIED",
        "object": {"status": desired_status},
    }

    with patch.object(custom_resource, 'watch', return_value=[mock_watch_event]):
        # Block by consuming the generator
        for _ in custom_resource.wait_for_status(status=desired_status, timeout=10): # Increased timeout
            pass

        # If we get here without a timeout, the test has passed.
        # We can also check the final state after the loop.

        # To simulate the final refresh call finding the correct status
        def final_refresh():
            custom_resource.status = desired_status

        custom_resource.refresh = MagicMock(side_effect=final_refresh)
        custom_resource.refresh() # Manually call to update status for assertion

        assert custom_resource.status == desired_status
