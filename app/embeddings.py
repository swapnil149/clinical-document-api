import os
import voyageai
from dotenv import load_dotenv
# load_dotenv() loads variables from the local .env file into the environment so they can be accessed with os.getenv(). 
# We call it in embeddings.py before creating the Voyage client to ensure VOYAGE_API_KEY is available when that module is imported.
load_dotenv()

voyage_client = voyageai.Client(
    api_key=os.getenv("VOYAGE_API_KEY")
)


def generate_document_embedding(text: str):
    result = voyage_client.embed(
        [text],
        model="voyage-4",
        input_type="document"
    )

    return result.embeddings[0]


def generate_query_embedding(text: str):
    result = voyage_client.embed(
        [text],
        model="voyage-4",
        input_type="query"
    )

    return result.embeddings[0]