# Fetch raw Wikipedia HTML and return plain text per article
import wikipediaapi
from wikipediaapi import (SearchSort, SearchWhat)  # noqa: F401

USER_AGENT = "WikiRAGAgent/0.1 (https://github.com/milwil-2/curio-rag)"
LANGUAGE = 'en'

def create_wikipedia_client():
    """
    Create and return a wikipedia API client with async optional.
    """
    return wikipediaapi.Wikipedia(user_agent=USER_AGENT, language=LANGUAGE, max_retries=5, retry_wait=2.0)
    

def page_to_article_dict(page) -> dict:
    return {
        "title": page.title,
        "url": page.fullurl,
        "summary": page.summary,
        "text": page.text,
    }

def get_page(wiki, title: str):
    return wiki.page(title)


def search_wikipedia_topic(topic: str, limit: int=20) -> list[dict]:
    """
    Seach a Wikipedia for a given topic.
    Return SearchResults object with dict of ~20 pages, int totalhits (matches reported by api) and str suggestion (spelling suggestion from search backend).
    """
    wiki = create_wikipedia_client()

    try:
        # optimize search with api functions
        results = wiki.search(
                topic,
                # what=SearchWhat.NEAR_MATCH,
                sort=SearchSort.RELEVANCE,
                limit=limit
            )

        matches = []

        for title in results.pages:
            matches.append(page_to_article_dict(get_page(wiki, title)))
            
        return matches

    except wikipediaapi.WikipediaException as e:
        print(f"Error: {e}")
        return None


def main():
    topic = input("Enter a topic: ")
    result = search_wikipedia_topic(topic, limit=20)

    print([article["title"] for article in result])

if __name__ == "__main__":
    main()