import os
from kubernetes import config
from typing import Tuple, Optional


def get_current_context() -> Tuple[Optional[str], Optional[str]]:
    """
    Returns the current user and namespace from the active kubeconfig context.
    Respects the KUBECONFIG environment variable.
    """
    try:
        contexts, active_context = config.list_kube_config_contexts(
            config_file=os.environ.get("KUBECONFIG")
        )
        context_data = active_context.get("context", {})
        return context_data.get("user"), context_data.get("namespace", "default")
    except (config.ConfigException, IndexError):
        # Fallback if no config is found or context is incomplete
        return None, "default"
