import logging
import os
from openai import OpenAI

def init():
    logging.basicConfig(level=logging.INFO)

    global debug
    global client 
    global model
    debug = os.environ.get('DEBUG', 'False').lower() == 'true'
    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
