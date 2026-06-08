import logging
import os

from openai import OpenAI


# not the best way to do a config, but it works
def init():
    logging.basicConfig(level=logging.INFO)
    logging.getLogger("DeepFace").setLevel(logging.WARNING)
    logging.getLogger("deepface").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)

    global debug
    global client
    global model
    debug = os.environ.get("DEBUG", "False").strip().lower() == "true"
    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
