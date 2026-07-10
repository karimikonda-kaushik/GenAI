from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv
import os 
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.vectorstores import InMemoryVectorStore
from langchain_community.document_loaders import PyPDFDirectoryLoader, DirectoryLoader, TextLoader

load_dotenv()
DOCUMENTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "My Documents")

#Load API key 
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))

#invoke the LLM
llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash")

#load the documents
pdf_loader = PyPDFDirectoryLoader(DOCUMENTS_DIR)
pdf_docs = pdf_loader.load()

text_loader = DirectoryLoader(DOCUMENTS_DIR, glob="**/*.txt", loader_cls=TextLoader)
text_docs = text_loader.load()

docs = pdf_docs + text_docs

#creating embeddings and vector store
embeddings = HuggingFaceEmbeddings(model_name='sentence-transformers/all-MiniLM-L6-v2')
vector_store = InMemoryVectorStore(embeddings)
vector_store.add_documents(docs)

#get the user query
user_query = input("Enter your query: ")

# we retrieve the most similar documents to the user query
vector_store.similarity_search(user_query)

retrieved_docs = vector_store.similarity_search(user_query, k=2)

#we extract page content from the retrieved documents and apply join to create a single string and inject context in the system prompt
context = "\n".join([doc.page_content for doc in retrieved_docs])

system_prompt = f"""
you are a helpful assistant that answers questions about the these documents: {context}
"""

#set up the messages
messages = [
    SystemMessage(content=system_prompt),
]


#append the user query to the messages
messages.append(HumanMessage(content=user_query))

#invoke the LLM
response = llm.invoke(messages)

#print the response
print(response.content)