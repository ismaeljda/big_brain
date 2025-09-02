import google.generativeai as genai
import os
from dotenv import load_dotenv

load_dotenv()
genai.configure(api_key=os.getenv("GOOGLE_AI_API_KEY"))

# Convertir le générateur en liste
models = list(genai.list_models())
print(models)
