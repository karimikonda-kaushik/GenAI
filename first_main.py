import os

from dotenv import load_dotenv
from langchain.chat_models import init_chat_model

load_dotenv()
GOOGLE_API_KEY = os.environ["GOOGLE_API_KEY"]
model = init_chat_model(
    model='gemini-3-flash-preview',
    model_provider="google-genai", 
    api_key=GOOGLE_API_KEY)

with open('cars.txt', 'r') as file:
    cars = file.read()
#response = model.invoke("hi, how are you?")
response = model.invoke(f"which of this cars are best to buy for a common man with luxury and efficiency? {cars}")
print(response.content)
