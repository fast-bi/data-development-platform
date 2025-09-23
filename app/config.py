import os

class Config:
    DEBUG = os.getenv('DEBUG', "false")

    SECRET_KEY = os.getenv('SECRET_KEY')
    if SECRET_KEY is None:
        raise ValueError("Environment variable SECRET_KEY is required")
    
    # FrontEnd User register form disabled
    FRONTEND_REGISTER = os.getenv('FRONTEND_REGISTER', "false")

    # Mail configuration
    MAIL_SERVER = os.getenv('MAIL_SERVER', 'mail.smtp2go.com')
    if MAIL_SERVER is None:
        raise ValueError("Environment variable MAIL_SERVER is required")

    MAIL_PORT = os.getenv('MAIL_PORT', "2525")
    if MAIL_PORT is None:
        raise ValueError("Environment variable MAIL_PORT is required")
    MAIL_PORT = int(MAIL_PORT)

    MAIL_USE_TLS = os.getenv('MAIL_USE_TLS', 'False').lower() == 'true'
    MAIL_USE_SSL = os.getenv('MAIL_USE_SSL', 'False').lower() == 'true'

    MAIL_USERNAME = os.getenv('MAIL_USERNAME')
    if MAIL_USERNAME is None:
        raise ValueError("Environment variable MAIL_USERNAME is required")

    MAIL_PASSWORD = os.getenv('MAIL_PASSWORD')
    if MAIL_PASSWORD is None:
        raise ValueError("Environment variable MAIL_PASSWORD is required")

    MAIL_DEFAULT_SENDER = os.getenv('MAIL_DEFAULT_SENDER', 'no-reply@fast.bi')
    if MAIL_DEFAULT_SENDER is None:
        raise ValueError("Environment variable MAIL_DEFAULT_SENDER is required")

    MAIL_DEBUG = os.getenv('MAIL_DEBUG', 'False').lower() == 'true'

    # Database configuration
    DB_HOST = os.getenv('DB_HOST')
    if DB_HOST is None:
        raise ValueError("Environment variable DB_HOST is required")

    DB_PORT = os.getenv('DB_PORT', "5432")
    if DB_PORT is None:
        raise ValueError("Environment variable DB_PORT is required")
    DB_PORT = int(DB_PORT)

    DB_USER = os.getenv('DB_USER')
    if DB_USER is None:
        raise ValueError("Environment variable DB_USER is required")

    DB_PASSWORD = os.getenv('DB_PASSWORD')
    if DB_PASSWORD is None:
        raise ValueError("Environment variable DB_PASSWORD is required")

    DB_NAME = os.getenv('DB_NAME')
    if DB_NAME is None:
        raise ValueError("Environment variable DB_NAME is required")

    # Auth Google Configuration
    CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID')
    if CLIENT_ID is None:
        raise ValueError("Environment variable GOOGLE_CLIENT_ID is required")

    CLIENT_SECRET = os.getenv('GOOGLE_CLIENT_SECRET')
    if CLIENT_SECRET is None:
        raise ValueError("Environment variable GOOGLE_CLIENT_SECRET is required")

    REDIRECT_URI = os.getenv('GOOGLE_REDIRECT_URI')
    if REDIRECT_URI is None:
        raise ValueError("Environment variable GOOGLE_REDIRECT_URI is required")

    # Fast.BI Repository access key
    GITLAB_ADMIN_ACCESS_TOKEN = os.getenv("GITLAB_ADMIN_ACCESS_TOKEN")
    if GITLAB_ADMIN_ACCESS_TOKEN is None:
        raise ValueError("Environment variable GITLAB_ADMIN_ACCESS_TOKEN is required")

    # Static Auth Google configuration variables
    SCOPES = 'https://www.googleapis.com/auth/cloud-platform https://www.googleapis.com/auth/compute'
    AUTHORIZATION_URL = 'https://accounts.google.com/o/oauth2/v2/auth'
    TOKEN_URL = 'https://oauth2.googleapis.com/token'

    #Optional env variables.
    FASTBI_VAULT_CLIENT_ID = os.getenv("FASTBI_VAULT_CLIENT_ID", None) 
    FASTBI_VAULT_CLIENT_SECRET = os.getenv("FASTBI_VAULT_CLIENT_SECRET", None) 
    FASTBI_ADMIN_EMAIL = os.getenv("FASTBI_ADMIN_EMAIL", None) 

