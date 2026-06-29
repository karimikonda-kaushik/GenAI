import os
from dotenv import load_dotenv
from google import genai

load_dotenv()

user_prompt = "create a beautiful image of nature with a river and a mountain in the background"

client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))

response = client.models.generate_content(
    model="gemini-2.5-flash",
    contents=[user_prompt],
    config={
        "response_mime_type": "image/png",
    }
)

for part in response.parts:
    if part.inline_data is not None:
        image = part.as_image()

image.save("generated_image.png")
