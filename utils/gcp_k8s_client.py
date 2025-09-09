import subprocess
import os
import time
import datetime
from flask import current_app
from app.config import Config
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request


class GCPK8SClient:
    def __init__(self, access_token, refresh_token, token_expiry, token_key):
        self.access_token = access_token
        self.refresh_token = refresh_token
        self.token_expiry = token_expiry
        self.token_key = token_key

    def refresh_access_token_if_needed(self):
        if self.access_token and self.refresh_token:
            if self.is_token_expired():
                current_app.logger.info("Token is expired, attempting to refresh")
                try:
                    creds = Credentials.from_authorized_user_info(
                        {"refresh_token": self.refresh_token, "client_id": Config.CLIENT_ID, "client_secret": Config.CLIENT_SECRET},
                        scopes=['https://www.googleapis.com/auth/cloud-platform']
                    )
                    creds.refresh(Request())
                    current_app.logger.info("Token refreshed successfully")
                    self.access_token = creds.token
                    
                    # Calculate new expiry
                    if creds.expiry:
                        self.token_expiry = creds.expiry.timestamp()
                    else:
                        # If expiry is not set, default to 1 hour from now
                        self.token_expiry = (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=1)).timestamp()
                    
                    current_app.logger.info(f"New token expiry set to: {self.token_expiry}")
                    
                    # Update the token in the database
                    metadata_collector = current_app.metadata_collector
                    metadata_collector.save_token(self.token_key, self.access_token, self.refresh_token, self.token_expiry)
                    current_app.logger.info("Token updated in database")
                except Exception as e:
                    current_app.logger.error(f"Error refreshing token: {str(e)}")
            else:
                current_app.logger.info("Token is still valid, no refresh needed")
        else:
            current_app.logger.warning("No access token or refresh token available")

    def is_token_expired(self):
        if self.token_expiry is None:
            current_app.logger.info("Token expiry is None, considering as expired")
            return True
        current_time = time.time()
        is_expired = self.token_expiry <= current_time + 300
        current_app.logger.info(f"Token expiry: {datetime.datetime.fromtimestamp(self.token_expiry)}, "
                    f"Current time: {datetime.datetime.fromtimestamp(current_time)}, "
                    f"Is expired: {is_expired}")
        return is_expired

    def run_command(self, command):
        self.refresh_access_token_if_needed()
        env = os.environ.copy()
        env['CLOUDSDK_AUTH_ACCESS_TOKEN'] = self.access_token
        # env['GOOGLE_OAUTH_ACCESS_TOKEN'] = self.access_token
        # env['CLOUDSDK_PYTHON'] = "/opt/homebrew/bin/python3.11
        try:
            result = subprocess.run(command, env=env, capture_output=True, text=True)
            if result.returncode != 0:
                return {"error": result.stderr}, 500
            return {"output": result.stdout}, 200
        except Exception as e:
            return {"error": str(e)}, 500

    def test_gcloud_access(self):
        command = ["gcloud", "projects", "list"]
        return self.run_command(command)

    def test_kubectl_access(self):
        commands = [
            ["kubectl", "config", "view", "--minify", "--flatten", "--output=jsonpath={.current-context}"],
            ["kubectl", "config", "view", "--minify", "--flatten", "--output=jsonpath={.clusters[0].cluster.server}"],
            ["kubectl", "get", "pods", "--output=json"]
        ]
        results = {}
        for i, command in enumerate(commands):
            result, status = self.run_command(command)
            results[f"command_{i}"] = result
            if status != 200:
                return result, status
        return results, 200

    def set_gke_context(self, project_id, zone, cluster_name):
        command = ["gcloud", "container", "clusters", "get-credentials", cluster_name, "--zone", zone, "--project", project_id]
        return self.run_command(command)
