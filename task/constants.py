import os

DEFAULT_SYSTEM_PROMPT = "You are an assistant who answers concisely and informatively."
DIAL_ENDPOINT = "https://ai-proxy.lab.epam.com"
DIAL_API_KEY = os.getenv('DIAL_API_KEY', '')
APP_DEBUG = os.getenv('DEBUG', 'False').lower() in ('true', '1', 'on')
