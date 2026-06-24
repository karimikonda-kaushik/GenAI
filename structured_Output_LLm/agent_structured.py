from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv
from langchain.agents import create_agent
from pydantic import BaseModel, Field

load_dotenv()

def send_email(email_address: str, sender_name: str, subject: str, body: str):
    """Send an email to an email address on behalf of the sender"""
    # Code that sends the email
    print("Sending email")
    return f"Email sent to {email_address} on behalf of {sender_name}"


# Define the structured output schema
class EmailResponse(BaseModel):
    """Response after sending an email"""
    recipient: str = Field(description="Email address of the recipient")
    subject: str = Field(description="Subject line of the email")
    body: str = Field(description="Body of the email")
    status: str = Field(description="Status of the email (sent/failed)")
    summary: str = Field(description="Brief summary of what was done")


# Initialize Gemini Flash 2.5
llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    temperature=0.7,
)

system_prompt = """
You are a helpful assistant. 
YOUR WORKFLOW:
1. You should help the user with various office tasks.
2. If the user asks you to send an email, use the send_email tool. 
3. Create a relevant body and a subject for the email.
"""

agent = create_agent(
    model=llm,
    tools=[send_email],
    system_prompt=system_prompt,
    response_format=EmailResponse  # Add structured output
)

user_query = "Send an email to John telling him that I finished the task"

response = agent.invoke(
    {"messages": [{'role': 'user', 'content': user_query}]}
)

# Access the structured response
print("Structured Response:")
print(response['structured_response'])
print("\nFull conversation:")
print(response['messages'][-1].content)