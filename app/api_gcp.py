import os
import traceback
import logging
import requests
import subprocess
from flask import session, request, redirect, current_app, Response, jsonify
from flask_session import Session
import json
from apiflask import Schema, abort
from apiflask.fields import String, Boolean
from apiflask.validators import Length
from utils.gcp_k8s_client import GCPK8SClient
from urllib.parse import quote
from uuid import uuid4
import time
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from app.config import Config
from app.security import auth
from datetime import timedelta

logger = logging.getLogger(__name__)

# Define the schemas
class GoogleLoginInputSchema(Schema):
    # Usually empty as login is typically initiated without input
    pass

class GoogleLoginOutputSchema(Schema):
    auth_url = String(metadata={'description': 'The Google authorization URL'})

class GoogleCallbackInputSchema(Schema):
    state = String(metadata={'description': 'The state token for CSRF protection'})

class GoogleCallbackOutputSchema(Schema):
    message = String(metadata={'description': 'Success message'})
    token_key = String(metadata={'description': 'The token key for retrieving the access token'})
    has_refresh_token = Boolean(metadata={'description': 'Indicates if a refresh token was received'})

class GoogleTestAuthInputSchema(Schema):
    gcp_project_id = String(required=True, validate=Length(min=1, max=64), metadata={'description': 'The project ID of GCP.'})
    gcp_gke_region = String(required=True, validate=Length(min=1, max=64), metadata={'description': 'The region of the GKE Kubernetes Cluster.'})
    gcp_gke_name = String(required=True, validate=Length(min=1, max=64), metadata={'description': 'The name of GKE Kubernetes instance.'})
class GoogleTestAuthHeaderInputSchema(Schema):
    X_Token_Key = String(
        required=True, 
        validate=Length(1, 255),
        data_key='X-Token-Key',
        metadata={
            'description': 'The token key for retrieving the access token',
            'location': 'headers',
            'header_name': 'X-Token-Key'
        }
    )

class GoogleTestAuthOutputSchema(Schema):
    message = String(metadata={'description': 'Result message'})
    gcloud_result = String(metadata={'description': 'Result of gcloud access test'})
    kubectl_results = String(metadata={'description': 'Result of kubectl access test'})

class TokenCleanupSchema(Schema):
    token_key = String(required=True, validate=Length(1, 255))

class TokenCleanupResponseSchema(Schema):
    message = String()

def make_authenticated_request(url):
    access_token = session.get('access_token')
    headers = {'Authorization': f'Bearer {access_token}'}
    response = requests.get(url, headers=headers)
    return response.json()

def run_command_with_oauth2(command, access_token):
    # Set up the environment with the access token
    env = os.environ.copy()
    env['GOOGLE_OAUTH_ACCESS_TOKEN'] = access_token
    
    # Run the subprocess with the modified environment
    result = subprocess.run(command, env=env, capture_output=True, text=True)
    
    # Check for errors
    if result.returncode != 0:
        print(f"Command failed with error: {result.stderr}")
    else:
        print(f"Command succeeded with output: {result.stdout}")

#def setup_gcp_auth_routes(bp, oauth_states):
    # @app.route('/login_gcp')
    # @app.doc(tags=['Google Provider Authentication'])
    # @app.input(GoogleLoginInputSchema, location='json')
    # @app.output(GoogleLoginOutputSchema)
    # def login_gcp(json_data):
    #     #state = current_app.config['SECRET_KEY']
    #     state = str(uuid4())
    #     session['oauth_state'] = state
    #     session.modified = True

    #     encoded_scopes = quote(current_app.config['SCOPES'])
        
    #     auth_url = (
    #         f"{current_app.config['AUTHORIZATION_URL']}?response_type=code&client_id={current_app.config['CLIENT_ID']}"
    #         f"&redirect_uri={current_app.config['REDIRECT_URI']}&scope={encoded_scopes}&state={state}"
    #         f"&access_type=offline&prompt=consent"
    #     )
    #     print(f"Setting oauth_state: {state}")
    #     print(f"Session data before redirect: {session}")
    #     return redirect(auth_url)

    # @app.route('/oauth2/gcp_callback')
    # @app.doc(tags=['Google Provider Authentication'])
    # @app.input(GoogleCallbackInputSchema, location='json')
    # @app.output(GoogleCallbackOutputSchema)
    # def callback(json_data):
    #     print(f"Callback received. Session data: {session}")
    #     state = request.args.get('state')
    #     print(f"Received state: {state}")
    #     session_state = session.get('oauth_state')
    #     print(f"Retrieved session state: {session_state}")
        
    #     if not state or state != session_state:
    #         print(f"State mismatch. Received: {state}, Session: {session_state}")
    #         abort(400, description="Invalid state parameter")

    #     code = request.args.get('code')
    #     if not code:
    #         abort(400, description="Authorization code not received")

    #     data = {
    #         'code': code,
    #         'client_id': current_app.config['CLIENT_ID'],
    #         'client_secret': current_app.config['CLIENT_SECRET'],
    #         'redirect_uri': current_app.config['REDIRECT_URI'],
    #         'grant_type': 'authorization_code'
    #     }
    #     token_url = current_app.config['TOKEN_URL']
    #     response = requests.post(token_url, data=data)
    #     token_response = response.json()

    #     access_token = token_response.get('access_token')
    #     refresh_token = token_response.get('refresh_token')
    #     expires_in = token_response.get('expires_in', 1800)  # Default to 30 minutes if not provided
        
    #     # Calculate expiry with a safety check
    #     expiry = max(time.time() + expires_in, time.time() + 300)  # At least 5 minutes in the future

    #     if not access_token:
    #         abort(400, message="Failed to obtain access token")

    #     token_key = str(uuid4())

    #     try:
    #         metadata_collector = current_app.metadata_collector
    #         metadata_collector.save_token(token_key, access_token, refresh_token, expiry)
    #     except Exception as e:
    #         current_app.logger.error(f"Error saving token: {str(e)}")
    #         abort(500, message="Failed to save token")

    #     response = {
    #         "message": "Authorization successful. Use this key to retrieve your token.",
    #         "token_key": token_key,
    #         "has_refresh_token": refresh_token is not None
    #     }

    #     # Add a small JavaScript snippet to the response
    #     js_snippet = f"""
    #     <script>
    #     window.opener.postMessage({{ token_key: "{token_key}" }}, '*');
    #     </script>
    #     """

    #     return Response(js_snippet + json.dumps(response), mimetype='text/html')

    # @app.route('/debug_session')
    # def debug_session():
    #     return jsonify(dict(session))

def setup_gcp_auth_routes(bp, oauth_states):
    @bp.route('/login_gcp')
    @bp.doc(tags=['Google Provider Authentication'])
    @bp.input(GoogleLoginInputSchema, location='json')
    @bp.output(GoogleLoginOutputSchema)
    def login_gcp(json_data):
        state = str(uuid4())
        session['oauth_state'] = state
        oauth_states[state] = True
        session.modified = True

        encoded_scopes = quote(current_app.config['SCOPES'])
        
        auth_url = (
            f"{current_app.config['AUTHORIZATION_URL']}?response_type=code&client_id={current_app.config['CLIENT_ID']}"
            f"&redirect_uri={current_app.config['REDIRECT_URI']}&scope={encoded_scopes}&state={state}"
            f"&access_type=offline&prompt=consent"
        )
        print(f"Setting oauth_state: {state}")
        print(f"Session data before redirect: {dict(session)}")
        print(f"OAuth states before redirect: {oauth_states}")
        print(f"Auth URL: {auth_url}")
        response = redirect(auth_url)
        return response

    @bp.route('/oauth2/gcp_callback')
    @bp.doc(tags=['Google Provider Authentication'])
    @bp.input(GoogleCallbackInputSchema, location='json')
    @bp.output(GoogleCallbackOutputSchema)
    def callback(json_data):
        print(f"Callback received. Session data: {dict(session)}")
        print(f"Callback received. OAuth states: {oauth_states}")
        state = request.args.get('state')
        print(f"Received state: {state}")
        session_state = session.get('oauth_state')
        stored_state = state in oauth_states
        print(f"Retrieved session state: {session_state}")
        print(f"State in shared storage: {stored_state}")
        
        if not state:
            print("No state received in callback")
            return jsonify({"error": "No state parameter received"}), 400
        
        if not stored_state and state != session_state:
            print(f"State mismatch. Received: {state}, Session: {session_state}, Stored: {stored_state}")
            return jsonify({"error": "Invalid state parameter"}), 400

        # State is valid, proceed with the OAuth flow
        print("State validated successfully")

        # Clear the state from both session and shared storage after successful validation
        session.pop('oauth_state', None)
        oauth_states.pop(state, None)
        session.modified = True

        code = request.args.get('code')
        if not code:
            print("No authorization code received")
            return jsonify({"error": "Authorization code not received"}), 400

        data = {
            'code': code,
            'client_id': current_app.config['CLIENT_ID'],
            'client_secret': current_app.config['CLIENT_SECRET'],
            'redirect_uri': current_app.config['REDIRECT_URI'],
            'grant_type': 'authorization_code'
        }
        token_url = current_app.config['TOKEN_URL']
        response = requests.post(token_url, data=data)
        token_response = response.json()

        access_token = token_response.get('access_token')
        refresh_token = token_response.get('refresh_token')
        expires_in = token_response.get('expires_in', 1800)  # Default to 30 minutes if not provided
        
        # Calculate expiry with a safety check
        expiry = max(time.time() + expires_in, time.time() + 300)  # At least 5 minutes in the future

        if not access_token:
            abort(400, message="Failed to obtain access token")

        token_key = str(uuid4())

        try:
            metadata_collector = current_app.metadata_collector
            metadata_collector.save_token(token_key, access_token, refresh_token, expiry)
        except Exception as e:
            current_app.logger.error(f"Error saving token: {str(e)}")
            abort(500, message="Failed to save token")

        response = {
            "message": "Authorization successful. Use this key to retrieve your token.",
            "token_key": token_key,
            "has_refresh_token": refresh_token is not None
        }

        # Store the token key in the session or a server-side cache
        session['gcp_auth_token_key'] = token_key

        # Add a small JavaScript snippet to the response
        html_response = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Authentication Successful</title>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    height: 100vh;
                    margin: 0;
                    background-color: #f0f0f0;
                }}
                .container {{
                    text-align: center;
                    background-color: white;
                    padding: 2rem;
                    border-radius: 8px;
                    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
                }}
                h1 {{
                    color: #6788ff;
                    margin-bottom: 1rem;
                }}
                p {{
                    color: #333;
                    margin-bottom: 1rem;
                }}
                .loader {{
                    border: 4px solid #f3f3f3;
                    border-top: 4px solid #a7b8ff;
                    border-radius: 50%;
                    width: 40px;
                    height: 40px;
                    animation: spin 1s linear infinite;
                    margin: 1rem auto;
                }}
                @keyframes spin {{
                    0% {{ transform: rotate(0deg); }}
                    100% {{ transform: rotate(360deg); }}
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>Authentication Successful</h1>
                <p>You have been successfully authenticated.</p>
                <div class="loader"></div>
                <p>This window will close automatically...</p>
            </div>

            <script>
                if (window.opener) {{
                    window.opener.postMessage({{ token_key: "{token_key}", status: "success" }}, '*');
                }}
                setTimeout(function() {{
                    window.close();
                }}, 2000);  // Close after 2 seconds to ensure the message is sent and the user sees the success message
            </script>
        </body>
        </html>
        """

        print(f"OAuth flow completed successfully. Token key: {token_key}")
        return Response(html_response, mimetype='text/html')

    @bp.route('/gcp_authentication_test', methods=['POST'])
    @bp.auth_required(auth)
    @bp.doc(tags=['Google Provider Authentication'])
    @bp.input(GoogleTestAuthInputSchema, location='form_and_files')
    @bp.input(GoogleTestAuthHeaderInputSchema, location='headers')
    @bp.output(GoogleTestAuthOutputSchema)
    def test_access_gcp(headers_data, form_and_files_data):
        token_key = request.headers.get('X-Token-Key')
        token_key_headers_data = headers_data['X_Token_Key']
        project_id = form_and_files_data.get('gcp_project_id')
        region = form_and_files_data.get('gcp_gke_region')
        cluster_name = form_and_files_data.get('gcp_gke_name')
        if not token_key:
            abort(400, message="X-Token-Key header is required")

        metadata_collector = current_app.metadata_collector
        token_data = metadata_collector.get_access_token(token_key)

        if not token_data:
            abort(401, message="Invalid or expired token key")

        access_token, refresh_token, token_expiry = token_data

        gcp_k8s_client = GCPK8SClient(access_token, refresh_token, token_expiry, token_key)

        try:
            context_result, context_status = gcp_k8s_client.set_gke_context(project_id, region, cluster_name)
            if context_status != 200:
                abort(context_status, message=context_result.get('error', 'Failed to set GKE context'))

            gcloud_result, gcloud_status = gcp_k8s_client.test_gcloud_access()
            if gcloud_status != 200:
                abort(gcloud_status, message=gcloud_result.get('error', 'Failed to access gcloud'))

            kubectl_results, kubectl_status = gcp_k8s_client.test_kubectl_access()
            if kubectl_status != 200:
                abort(kubectl_status, message=kubectl_results.get('error', 'Failed to access kubectl'))

            return {
                "message": "Authentication and access tests successful",
                "gcloud_result": gcloud_result["output"],
                "kubectl_results": kubectl_results
            }

        except Exception as e:
            current_app.logger.error(f"Error in GCP authentication test: {str(e)}")
            current_app.logger.error(traceback.format_exc())
            abort(500, message=f"An unexpected error occurred: {str(e)}")

    @bp.route('/cleanup_cp_token', methods=['POST'])
    @bp.auth_required(auth)
    @bp.doc(tags=['Google Provider Authentication'])
    @bp.input(TokenCleanupSchema, location='json')
    @bp.output(TokenCleanupResponseSchema)
    def cleanup_cp_token(json_data):
        token_key = json_data.get('token_key')
        if not token_key:
            abort(400, message="token_key is required")
        try:
            metadata_collector = current_app.metadata_collector
            result = metadata_collector.mark_token_as_used(token_key)
            if result:
                return {"message": "Token marked as used successfully"}, 200
            else:
                return {"message": "Token not found or already marked as used"}, 404
        except Exception as e:
            current_app.logger.error(f"Error marking token as used: {str(e)}")
            abort(500, message="Internal server error")
