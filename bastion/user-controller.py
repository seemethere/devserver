#!/usr/bin/env python3
"""
User Controller Sidecar - Secure User Provisioning
Watches for user registration events and provisions namespaces/ServiceAccounts
"""

import json
import time
import logging
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, Optional
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('user-controller')

class UserController:
    def __init__(self):
        self.registry_file = "/shared/user-registry.json"
        self.tokens_dir = "/shared/user-tokens"
        self.namespace_prefix = "dev-"
        
        # Ensure directories exist
        Path(self.tokens_dir).mkdir(parents=True, exist_ok=True)
        Path("/shared").mkdir(parents=True, exist_ok=True)
        
        # Initialize empty registry if it doesn't exist
        if not os.path.exists(self.registry_file):
            self._save_registry({})
    
    def _load_registry(self) -> Dict:
        """Load user registry from file"""
        try:
            with open(self.registry_file, 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            logger.warning("Failed to load registry, using empty registry")
            return {}
    
    def _save_registry(self, registry: Dict):
        """Save user registry to file"""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, dir="/shared") as tmp:
            json.dump(registry, tmp, indent=2)
            temp_path = tmp.name
        
        # Atomic move
        os.rename(temp_path, self.registry_file)
        logger.debug(f"Registry saved with {len(registry)} users")
    
    def _kubectl(self, *args) -> subprocess.CompletedProcess:
        """Execute kubectl command"""
        cmd = ["kubectl"] + list(args)
        logger.debug(f"Running: {' '.join(cmd)}")
        return subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    
    def _create_namespace(self, username: str) -> bool:
        """Create namespace for user"""
        namespace = f"{self.namespace_prefix}{username}"
        
        # Check if namespace already exists
        result = self._kubectl("get", "namespace", namespace)
        if result.returncode == 0:
            logger.info(f"Namespace {namespace} already exists")
            return True
        
        # Create namespace
        namespace_yaml = f"""
apiVersion: v1
kind: Namespace
metadata:
  name: {namespace}
  labels:
    devserver.io/user: "{username}"
    devserver.io/created-by: "user-controller"
    devserver.io/type: "dev-namespace"
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(namespace_yaml)
            temp_file = f.name
        
        try:
            result = self._kubectl("apply", "-f", temp_file)
            if result.returncode == 0:
                logger.info(f"Created namespace: {namespace}")
                return True
            else:
                logger.error(f"Failed to create namespace {namespace}: {result.stderr}")
                return False
        finally:
            os.unlink(temp_file)
    
    def _create_user_serviceaccount(self, username: str) -> bool:
        """Create ServiceAccount and Role for user"""
        namespace = f"{self.namespace_prefix}{username}"
        sa_name = f"user-{username}"
        
        # ServiceAccount
        sa_yaml = f"""
apiVersion: v1
kind: ServiceAccount
metadata:
  name: {sa_name}
  namespace: {namespace}
  labels:
    devserver.io/user: "{username}"
    devserver.io/created-by: "user-controller"
"""
        
        # Role with limited permissions
        role_yaml = f"""
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: dev-user
  namespace: {namespace}
rules:
# Pod and basic resource management
- apiGroups: [""]
  resources: ["pods", "services", "persistentvolumeclaims", "configmaps", "secrets"]
  verbs: ["get", "list", "create", "update", "patch", "delete"]
# Deployment management  
- apiGroups: ["apps"]
  resources: ["deployments", "statefulsets", "replicasets"]
  verbs: ["get", "list", "create", "update", "patch", "delete"]
# Job management for training
- apiGroups: ["batch"]
  resources: ["jobs"]
  verbs: ["get", "list", "create", "update", "patch", "delete"]
# Read-only access to nodes (for debugging)
- apiGroups: [""]
  resources: ["nodes"]
  verbs: ["get", "list"]
# Event viewing
- apiGroups: [""]
  resources: ["events"]
  verbs: ["get", "list"]
"""
        
        # RoleBinding
        rolebinding_yaml = f"""
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: dev-user-binding
  namespace: {namespace}
subjects:
- kind: ServiceAccount
  name: {sa_name}
  namespace: {namespace}
roleRef:
  kind: Role
  name: dev-user
  apiGroup: rbac.authorization.k8s.io
"""
        
        # Apply all resources
        all_yaml = sa_yaml + "---\n" + role_yaml + "---\n" + rolebinding_yaml
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(all_yaml)
            temp_file = f.name
        
        try:
            result = self._kubectl("apply", "-f", temp_file)
            if result.returncode == 0:
                logger.info(f"Created ServiceAccount and RBAC for user: {username}")
                return True
            else:
                logger.error(f"Failed to create ServiceAccount for {username}: {result.stderr}")
                return False
        finally:
            os.unlink(temp_file)
    
    def _extract_user_token(self, username: str) -> Optional[str]:
        """Extract user ServiceAccount token"""
        namespace = f"{self.namespace_prefix}{username}"
        sa_name = f"user-{username}"
        
        # Get ServiceAccount token secret
        result = self._kubectl("get", "serviceaccount", sa_name, "-n", namespace, "-o", "json")
        if result.returncode != 0:
            logger.error(f"Failed to get ServiceAccount {sa_name}: {result.stderr}")
            return None
        
        try:
            sa_data = json.loads(result.stdout)
            
            # For newer Kubernetes versions, we need to create a token manually
            # Create a token request
            result = self._kubectl("create", "token", sa_name, "-n", namespace, "--duration=8760h")
            if result.returncode == 0:
                token = result.stdout.strip()
                logger.info(f"Created token for user: {username}")
                return token
            else:
                logger.error(f"Failed to create token for {username}: {result.stderr}")
                return None
                
        except json.JSONDecodeError:
            logger.error(f"Failed to parse ServiceAccount JSON for {username}")
            return None
    
    def _save_user_token(self, username: str, token: str):
        """Save user token to shared volume"""
        user_token_dir = Path(self.tokens_dir) / username
        user_token_dir.mkdir(parents=True, exist_ok=True)
        
        token_file = user_token_dir / "token"
        with open(token_file, 'w') as f:
            f.write(token)
        
        # Get user UID - for development, testuser is 1000
        # In production, this would lookup the actual UID
        user_uid = 1000  # Default UID for testuser
        if username != "testuser":
            # For other users, we'd need a proper UID lookup
            # For now, use a high UID to avoid conflicts
            user_uid = 2000 + hash(username) % 1000
        
        # Set correct ownership and restrictive permissions
        os.chown(token_file, user_uid, user_uid)
        os.chown(user_token_dir, user_uid, user_uid)
        os.chmod(token_file, 0o600)
        os.chmod(user_token_dir, 0o700)
        
        logger.info(f"Saved token for user: {username} (UID: {user_uid})")
    
    def provision_user(self, username: str) -> bool:
        """Provision all resources for a user"""
        logger.info(f"Provisioning user: {username}")
        
        # Step 1: Create namespace
        if not self._create_namespace(username):
            return False
        
        # Step 2: Create ServiceAccount and RBAC
        if not self._create_user_serviceaccount(username):
            return False
        
        # Step 3: Wait a moment for SA to be ready
        time.sleep(2)
        
        # Step 4: Extract and save token
        token = self._extract_user_token(username)
        if not token:
            return False
        
        self._save_user_token(username, token)
        
        logger.info(f"Successfully provisioned user: {username}")
        return True
    
    def process_pending_users(self):
        """Process all users with pending status"""
        registry = self._load_registry()
        updated = False
        
        for username, user_data in registry.items():
            if user_data.get('status') == 'pending':
                logger.info(f"Processing pending user: {username}")
                
                if self.provision_user(username):
                    user_data['status'] = 'provisioned'
                    user_data['provisionedAt'] = datetime.utcnow().isoformat() + 'Z'
                    updated = True
                else:
                    logger.error(f"Failed to provision user: {username}")
                    user_data['status'] = 'failed'
                    user_data['lastError'] = datetime.utcnow().isoformat() + 'Z'
                    updated = True
        
        if updated:
            self._save_registry(registry)
    
    def run(self):
        """Main controller loop"""
        logger.info("Starting User Controller")
        
        while True:
            try:
                self.process_pending_users()
                time.sleep(5)  # Check every 5 seconds
            except KeyboardInterrupt:
                logger.info("Shutting down User Controller")
                break
            except Exception as e:
                logger.error(f"Error in controller loop: {e}")
                time.sleep(10)  # Back off on errors

if __name__ == "__main__":
    controller = UserController()
    controller.run()
