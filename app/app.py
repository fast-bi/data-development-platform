#from flask import Flask
from apiflask import APIFlask, APIBlueprint
from flask import jsonify, Blueprint
from flask_cors import CORS
from flask_caching import Cache
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from app.api import setup_routes
from app.api_gcp import setup_gcp_auth_routes
from app.app_frontend import setup_frontend_routes
from app.config import Config
from utils.customer_data_platform_service_versions import DeploymentMetadataCollector
from utils.infra_data_services_latest_versions import InfraDataServicesLatestVersions
from werkzeug.middleware.proxy_fix import ProxyFix
from app.logging_config import configure_logging
from datetime import timedelta
from flask_wtf.csrf import CSRFError

# Shared storage for OAuth states
oauth_states = {}

def create_app():
    app = APIFlask(__name__, title='Fast.BI DBT Project Initialization API', docs_path='/api/v1/docs', version='1.0')
    
    limiter = Limiter(
        key_func=get_remote_address,
        default_limits=["200 per day", "50 per hour"]
    )

    limiter.init_app(app)

    app.wsgi_app = ProxyFix(
        app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1
    )
    # Load configuration
    app.config.from_object(Config)

    # Configure logging
    configure_logging(app)

    # Enable CORS support
    CORS(app)

    # Enable CSRF protection
    # csrf = CSRFProtect(app)

    # Session configuration
    app.config['SESSION_TYPE'] = 'filesystem'
    app.config['SESSION_FILE_DIR'] = '/tmp/flask_session'  # Ensure this directory exists and is writable
    app.config['SESSION_PERMANENT'] = True
    app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=3)
    app.config['SESSION_COOKIE_SECURE'] = False  # Set to True for HTTPS
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
    app.config['SESSION_COOKIE_NAME'] = 'fastbi_session'
    app.config['SESSION_COOKIE_DOMAIN'] = None  # Set this to your domain in production

    # All the OpenAPI field config can be set with the corresponding attributes of the app instance:
    app.description = 'Fast.BI DBT Project Initialization API, used for new dbt projects initialization and starting point configuration.'

    # openapi.info.description
    app.config['DESCRIPTION'] = """
# Fast.BI Metadata Collector API Documentation
## Overview
"""
    # openapi.info.contact
    app.config['CONTACT'] = {
        'name': 'API Support',
        'url': 'https://fast.bi/support',
        'email': 'gediminas@terasky.com'
    }

    # openapi.info.license
    app.config['LICENSE'] = {
        'name': 'Apache 2.0',
        'url': 'http://www.apache.org/licenses/LICENSE-2.0.html'
    }

    # openapi.info.termsOfService
    app.config['TERMS_OF_SERVICE'] = 'https://fast.bi'

    # The four info fields above can be set with the INFO key:
    app.config['INFO'] = {
        'description': '...',
        'termsOfService': 'http://api.fast.bi/terms/',
        'contact': {
            'name': 'API Support',
            'url': 'http://api.fast.bi/support',
            'email': 'gediminas@terasky.com'
        },
        'license': {
             'name': 'Apache 2.0',
             'url': 'http://www.apache.org/licenses/LICENSE-2.0.html'
         }
    }

    # If you don't need to set tag "description" or tag "externalDocs", just pass a list a string:
    # app.config['TAGS'] = ['Fastbi', 'DCDQ', 'Metadata', 'API']

    # openapi.servers
    app.config['SERVERS'] = [
        {
            'name': 'Production Server',
            'url': 'https://nct.fast.bi'
        },
        {
            'name': 'Development Server',
            'url': 'http://localhost:8080'
        },
        {
            'name': 'Testing Server',
            'url': 'http://localhost:8888'
        }
    ]

    # openapi.externalDocs
    app.config['EXTERNAL_DOCS'] = {
        'description': 'Find more info here',
        'url': 'https://apiflask.com/docs'
    }

    app.config['CACHE_TYPE'] = 'SimpleCache'

    app.cache = Cache(app)

    db_config = {
        'dbname': app.config['DB_NAME'],
        'user': app.config['DB_USER'],
        'password': app.config['DB_PASSWORD'],
        'host': app.config['DB_HOST'],
        'port': app.config['DB_PORT']
    }

    metadata_collector = DeploymentMetadataCollector(db_config)
    app.metadata_collector = metadata_collector

    latest_services_versions = InfraDataServicesLatestVersions()
    app.latest_services_versions = latest_services_versions.update

    # Create blueprints
    api_v1_bp = APIBlueprint('api_v1_bp', __name__, url_prefix='/api/v1')
    app_front_bp = Blueprint('app_frontend_bp', __name__, url_prefix='/', static_folder="assets")

    # Apply limiter to blueprints
    limiter.limit("100/day;20/hour")(api_v1_bp)
    limiter.limit("1000/day;100/hour")(app_front_bp)

    # Setup routes
    setup_routes(api_v1_bp)
    setup_gcp_auth_routes(api_v1_bp, oauth_states)
    setup_frontend_routes(app_front_bp, limiter)

    # Register blueprints
    app.register_blueprint(api_v1_bp)
    app.register_blueprint(app_front_bp)

    # Ensure OpenAPI is enabled for the API blueprint
    api_v1_bp.enable_openapi = True

    # @app.teardown_appcontext
    # def close_connection(exception):
    #     metadata_collector = getattr(app, 'metadata_collector', None)
    #     if metadata_collector is not None:
    #         metadata_collector.connection.close()
    #         app.logger.info("Database connection closed.")

    @app.errorhandler(404)
    def handle_404_error(e):
        return jsonify({'error': 'Resource not found'}), 404

    @app.errorhandler(500)
    def handle_500_error(e):
        return jsonify({'error': 'Internal server error'}), 500

    @app.errorhandler(429)
    def ratelimit_handler(e):
        return jsonify(error="ratelimit exceeded", message=str(e.description)), 429
    
    @app.errorhandler(CSRFError)
    def handle_csrf_error(e):
        return jsonify(error=str(e)), 400

    return app

if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=8080)
