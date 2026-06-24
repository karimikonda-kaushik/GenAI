from dotenv import load_dotenv
from langchain.chat_models import init_chat_model
from pydantic import BaseModel, Field
from typing import List

load_dotenv()


class Rescipe(BaseModel):
    name: str = Field(description="Name of the recipe")
    description:str = Field(description="Brief description of the recipe")
    prep_time: str = Field(description="Estimated preparation time of the recipe")


#instruction -(pydantic)->LLM-> structured output
class Response(BaseModel):
    """ A Single Recipe"""
    ingredients: List[str] = Field(description="List of main ingredients")
    recipes: List[str] = Field(description="List of 3 recipe suggestions")


# Initialize the model
model = init_chat_model("gemini-2.5-flash", model_provider="google_genai")
structured_model = model.with_structured_output(Response) #sens the response to the pydantic model
system_prompt = """
"You are a helpful chef. Identify the main ingredients. Suggest 3 recipes based those ingredients."
"""

# Create message
message = [{"role": "system", "content": system_prompt},
           {"role": "user", "content": "I have broccoli, butter, and eggs."}]

# Get and print the response
response = structured_model.invoke(message)
print(response.model_dump()) #print the response in a dictionary format