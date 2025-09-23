from apiflask import HTTPTokenAuth
from app.config import Config  # make sure to import Config correctly based on your project structure

auth = HTTPTokenAuth(scheme='Bearer')

def verify_token(token):
    return token == Config.SECRET_KEY  # Use the SECRET_KEY from your Config class

auth.verify_token(verify_token)

