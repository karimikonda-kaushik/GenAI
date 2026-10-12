from langchain_tavily import TavilySearch
from langchain.chat_models import init_chat_model
from dotenv import load_dotenv
import os

from pprint import pprint

load_dotenv()

queries = ["AI news this week", "AI companies latest models news", "Ai impact on businesses and jobs"]

def search_for_articles(queries):
    tavily_search = TavilySearch(
        max_results=5,
        topic="news",
        search_depth="basic",
        time_range="week",
        include_raw_content=False,
        include_answer=False,
    )

    all_results = []

    for query in queries:
        results = tavily_search.invoke(query)
        all_results.append(results)
    pprint(all_results)
    return all_results

def generate_newsletter(search_results):
    prompt = f"""
    you are a professional newsletter writer for an AI news business.
    below are the search results for this week's AI news. Each results includes content and the source url.

    SEARCH RESULTS:
    {search_results}

    write the article in markdown format.

    Rules:
    - Focus on the positive news about AI and recent improvements in AI technology and companies. 
    - Provide references using the URL's from the SEARCH RESULTS
    - Use Bold and italic text to highlight the most important information
    """
    model = init_chat_model("gemini-3-flash-preview" , model_provider="google_genai", temperature=0.5)
    response = model.invoke(prompt)
    if isinstance(response.content, list):
        return response.content[0]['text']
    return response.content

output =search_for_articles(queries=queries)
article =generate_newsletter(output)
#pprint(output)
print(article)

with open('article.md', 'w') as file:
    file.write(article)