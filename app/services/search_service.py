from elasticsearch import Elasticsearch
from app.core.config import settings
import uuid

def get_es_client() -> Elasticsearch:
    return Elasticsearch(settings.es_host)


def index_submission(submission) -> None:
    es = get_es_client()
    es.index(
        index="submissions",
        id=str(submission.id),
        document={
            "id": str(submission.id),
            "title": submission.title,
            "abstract": submission.abstract or "",
            "section": submission.section or "",
            "status": submission.status,
            "conference_id": str(submission.conference_id),
            "authors": [
                {
                    "full_name": a.full_name,
                    "organization": a.organization or "",
                    "email": a.email or "",
                }
                for a in submission.authors
            ],
        }
    )


def search_submissions(query: str, conference_id: str = None) -> list[str]:
    es = get_es_client()

    must = [
        {
            "multi_match": {
                "query": query,
                "fields": ["title^3", "abstract^2", "authors.full_name", "section"],
                "fuzziness": "AUTO"
            }
        }
    ]

    filter_ = []
    if conference_id:
        filter_.append({"term": {"conference_id": conference_id}})

    response = es.search(
        index="submissions",
        body={
            "query": {
                "bool": {
                    "must": must,
                    "filter": filter_
                }
            }
        }
    )

    return [hit["_source"]["id"] for hit in response["hits"]["hits"]]


def delete_from_index(submission_id: str) -> None:
    es = get_es_client()
    try:
        es.delete(index="submissions", id=submission_id)
    except Exception:
        pass