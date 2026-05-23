# Fetch raw Wikipedia HTML and return plain text per article
import wikipediaapi

def create_wikipedia_client(asy=False):
    """
    Create and return a wikipedia API client with async optional.
    """
    if not asy:
        return wiki = wikipediaapi.Wikipedia(user_agent=user_agent, language=language)
    else: 
        return wiki = wikipediaapi.AsyncWikipedia(user_agent=user_agent, language=language)

def get_wikipedia_article(topic: str, ):