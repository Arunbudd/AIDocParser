from openai import AsyncOpenAI
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = "sk-proj-..."

if not OPENAI_API_KEY:
    raise RuntimeError("Missing OPENAI_API_KEY in environment variables!")

# Single client instance
openai_client = OpenAI(api_key=OPENAI_API_KEY)
async_openai_client = AsyncOpenAI(api_key=OPENAI_API_KEY)

