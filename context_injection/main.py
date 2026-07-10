import os
from pathlib import Path
from tkinter import W
from pypdf import PdfReader

from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage


#Load API key 
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))


#Documents and systems prompt
directory = Path(BASE_DIR) / "My Documents"

#iterate over each file
def load_documents(directory = 'My Documents'):

    documents = []

    for file_path in directory.rglob('*'):
        if file_path.suffix in {'.pdf', '.docx', '.doc', '.txt', '.md'}:
            if file_path.suffix == '.pdf':
                reader = PdfReader(file_path)
                content = '\n'.join([page.extract_text() for page in reader.pages])
            else:
                content = file_path.read_text()
            documents.append({
                'path': file_path,
                'content': content,
            })
    return documents


def create_context(document_list):
    context = ''
    for doc in document_list:
        context = context + f"_____________{doc['path']}_____________\n{doc['content']}\n\n"
    return context

documents = load_documents(directory)
context = create_context(documents)
print(context)

#big_string = "Rabbit Company revenue in 2025 was 45,000"
system_prompt = f"""
you are a helpful assistant that answers questions about the these documents: {context}
"""

#set up the messages
messages = [
    SystemMessage(content=system_prompt),
]


#invoke the LLM
llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash")


#looping the conversation
while True:
    #get the user query
    user_query = input("Enter your query: ")

    #append the user query to the messages
    messages.append(HumanMessage(content=user_query))
    
    #invoke the LLM
    response = llm.invoke(messages)
    
    #print the response
    print(response.content)
    messages.append(response)

