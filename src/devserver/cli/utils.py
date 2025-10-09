from kubernetes import client, config
from kubernetes.config import ConfigException
from kubernetes.client.exceptions import ApiException

def get_user_namespace() -> str:
    """
    Determines the appropriate namespace for the current user.

    It discovers the namespace by querying for the User resource associated 
    with the current Kubernetes user. If no user is found, it defaults to "default".
    """
    try:
        config.load_kube_config()
        username = config.list_kube_config_contexts()[1].get('context', {}).get('user')
        if not username:
            return "default"
        
        api = client.CustomObjectsApi()
        users = api.list_cluster_custom_object("devserver.io", "v1", "devserverusers")
        
        for user in users.get("items", []):
            if user.get("spec", {}).get("username") == username:
                return f"devserver-user-{username}"
                
    except (ConfigException, ApiException, FileNotFoundError):
        return "default"
    
    return "default"
