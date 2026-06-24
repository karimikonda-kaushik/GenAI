import base64
import mimetypes
import os

from dotenv import load_dotenv
from langchain.chat_models import init_chat_model

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))

image_path = os.path.join(BASE_DIR, "images", "img.png")
mime_type, _ = mimetypes.guess_type(image_path)

with open(image_path, "rb") as file:
    image_base64 = base64.b64encode(file.read()).decode("utf-8")

model = init_chat_model("gemini-2.5-flash", model_provider="google_genai")

message = [
    {
        "role": "user",
        "content": [
            {"type": "text", "text": "Describe what you see in this image."},
            {
                "type": "image",
                "source_type": "base64",
                "data": image_base64,
                "mime_type": mime_type or "image/png",
            },
        ],
    }
]

response = model.invoke(message)
print(response.content)
