import os
from dotenv import load_dotenv
from langchain.chat_models import init_chat_model
from langchain_core.tools import tool
from langchain.agents import create_agent
load_dotenv()

from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown

console = Console()

llm = init_chat_model(
    "gemini-3.8-flash",
    model_provider="google_genai",
    temperature=0.5
)

@tool
def list_directory(path: str=".") -> str:
    """List all files and folders in given directory path and the default path is current directory"""
    try:
        result = "Contents of current directory\n: "
        items = os.listdir()

        files = []
        folders =[]

        for item in items:
            if os.path.isdir(item):
                folders.append(item)
            else:
                files.append(item)

        if folders:
            folders = "Folders:\n" + result + "\n".join(folders) + "\n"
        if files:
            files = "Files:\n" + result + "\n".join(files) + "\n"   
        
        return folders + files
    except Exception as e:
        return f"Error listing directories: {str(e)}"

def write_file(filepath: str, content: str) -> str:
    """ write content to a file . create new file or overwrite existing file"""
    try:
        with open(filepath, 'w') as file:
            file.write(content)

        return f"file {filepath} created successfully"
    except Exception as e:
        return f"Error writing file: {str(e)}"

def read_file(filepath: str) -> str:
    """ read the content of a given file """
    try:
        with open(filepath, 'r') as file:
            content = file.read()
        return content
    except Exception as e:
        return f"Error reading file: {str(e)}"

def create_directory(path: str) -> str:
    """ create a new directory at the given path. Can create nested directories."""
    try: 
        os.makedirs(path, exist_ok=True)
        return f"Succesfully created directory {path}"
    except Exception as e:
        return f"Error creating directory: {str(e)}"
    


system_prompt = """
you are a helpful coding assistant that can help users navigate, read and edit files.

you have access to four tools:
- list_directory: show files and folders in the current directory
- read_file: Read the content of a file
- write_file: Create or edit files
- create_directory: Create a new directory (including nested directories)

be helpful and clear in you rresponses. when editing files or creating directories, always confirm what changes you made.
"""
agent =  create_agent(
    model=llm,
    tools=[list_directory, write_file, read_file, create_directory]
)

user_input = console.input("[bold cyan]You:[/bold cyan] ").strip()

messages = [{"role": "user", "content": user_input}]

chunks = agent.stream({"messages": messages}, stream_mode='updates')

for chunk in chunks:
    for step, data in chunk.items():
        if step  == 'model':
            msg = data['messages'][-1]
            print("msg tool call", msg.tool_calls)
            if msg.tool_calls:
                tool = msg.tool_calls[0]['name']
                message = f"[bold yellow]🔧 Using tool: [/bold yellow][cyan]{tool}[/cyan]"
                console.print(message)
            else:
                ai_message = msg.content
                text_output = ai_message
        elif step == 'tools':
            result = data['messages'][-1].content
            result = result if len(result) <50 else result[:50] + "..."
            console.print(f"[bold green]🗒️ Tool result: [/bold green]\n [dim]{result}[/dim]")

markdown_output = Markdown(text_output)
Panel_output = Panel(markdown_output,
                    title='[bold cyan] 🤖 AI Response [/bold cyan]',
                    border_style='blue',
                    padding=(1,2))
                 
console.print(Panel_output)


