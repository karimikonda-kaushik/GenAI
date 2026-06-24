import gradio as gr
import base64
import mimetypes
import os
from dotenv import load_dotenv
from langchain.chat_models import init_chat_model

load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))


model = init_chat_model("gemini-2.5-flash", model_provider="google_genai")
system_prompt = """
you are a helpful chef. Identify the main ingredients. suggest 3 indian recipes based on those ingredients and give small and easy steps in making the dishes each..
"""

def identify_ingredients(image_path):
    mime_type, _ = mimetypes.guess_type(image_path)
    with open(image_path, "rb") as file:
        raw_binary = file.read()
        base64_bytes = base64.b64encode(raw_binary)
        image_base64 = base64_bytes.decode("utf-8")

    message = [
    {"role": "system", "content": system_prompt},
    {
        "role": "user",
        "content": [
            {
                "type": "text",
                "text": "Identify the ingredients in this image and suggest 3 indian recipes and give small and easy steps in making the dishes each.",
            },
            {
                "type": "image",
                "source_type": "base64",
                "data": image_base64,
                "mime_type": mime_type or "image/png",
            },
        ],
    },
]

    response = model.invoke(message)
    return response.content


demo = gr.Interface(
    fn=identify_ingredients,
    inputs=gr.Image(type="filepath"),
    outputs=gr.Markdown(),
    title="Recipe Generator",
    description="Generate recipes based on the ingredients in the image",
    allow_flagging="never",
)

if __name__ == "__main__":
    demo.launch(server_name="127.0.0.1", server_port=7860)