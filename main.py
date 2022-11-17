import os
import json
from typing import Optional
from dotenv import load_dotenv

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, Response
from starlette.middleware.cors import CORSMiddleware

from worldcat_api import WorldcatAPI

load_dotenv()

worldcat_api = WorldcatAPI(remote_webdriver_address=os.environ["REMOTE_WEBDRIVER_ADDRESS"])

app = FastAPI(title="Worldcat Reconciliation Service API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

metadata = {
    "name": "Worldcat Reconciliation Service",
    "defaultTypes": [
        {"id": "book", "name": "Book"},
        {"id": "artchap", "name": "Article, Chapter"},
    ],
    "identifierSpace": "http://localhost/identifier",
    "schemaSpace": "http://localhost/schema",
    "view": {"url": "https://www.worldcat.org/oclc/{{id}}"},
    "preview": {
        "url": os.environ["RECONCILIATION_SERVICE_DOMAIN"].strip('/') + "/preview?id={{id}}",
        "height": 250,
        "width": 350,
    },
    "extend": {
        "propose_properties": {
            "service_url": os.environ["RECONCILIATION_SERVICE_DOMAIN"],
            "service_path": "/properties",
        },
        "property_settings": [
            {
                "name": "limit",
                "label": "Limit",
                "type": "number",
                "default": 0,
                "help_text": "Maximum number of values to return per row (0 for no limit)",
            },
            {
                "name": "content",
                "label": "Content",
                "type": "select",
                "default": "literal",
                "help_text": "Content type: ID or literal",
                "choices": [
                    {"value": "id", "name": "ID"},
                    {"value": "literal", "name": "Literal"},
                ],
            },
        ],
    },
}


def process_queries(queries):
    query_batch = json.loads(queries)
    results = {}

    for key, query in query_batch.items():

        author, publication_year = None, None

        for property_ in query.get("properties", []):
            if property_["pid"] == "author":
                author = property_["v"]
            elif property_["pid"] == "publication_year":
                publication_year = property_["v"]

        worldcat_results = worldcat_api.search(
            title=query["query"],
            type_=query.get("type"),
            author=author,
            publication_year=publication_year,
        )

        result = []
        for x in worldcat_results:
            record = {
                "id": x["record"]["oclcNumber"],
                "name": x["record"]["title"],
                "score": x["score"],
                "match": True,
            }
            if general_format := x["record"].get("generalFormat"):
                record['type'] = [
                    {
                        "id": general_format.lower(),
                        "name": worldcat_api.types.get(general_format.lower()),
                    }
                ]
            result.append(record)

        results[key] = {"result": result}

    return results


def process_extend(extend):
    extend_batch = json.loads(extend)
    result = {"meta": [], "rows": {}}
    for property_ in extend_batch["properties"]:
        if property_["id"] == "oclc_of_all_editions":
            result["meta"].append({"id": "oclc_of_all_editions", "name": "OCLC"})
            for id in extend_batch.get("ids"):
                all_editions = worldcat_api.get_all_editions(oclc=id)
                result["rows"][id] = {
                    "oclc_of_all_editions": [
                        {"str": str(x["oclcNumber"])} for x in all_editions
                    ]
                }
    return result


@app.post("/")
async def reconcile_post(request: Request):
    form = await request.form()
    if queries := form.get("queries"):
        return process_queries(queries)
    elif extend := form.get("extend"):
        return process_extend(extend)


@app.get("/")
def reconcile_get(callback: Optional[str] = None):
    if callback:
        content = f"{callback}({json.dumps(metadata)})"
        return Response(content=content, media_type="text/javascript")
    return metadata


@app.get("/queries")
def queries(queries: str):
    return process_queries(queries)


@app.get("/properties")
def properties(type: str, limit: Optional[int] = None):
    return {
        "type": type,
        "properties": [
            {"id": "oclc_of_all_editions", "name": "OCLC Numbers of all Editions"},
        ],
    }


@app.get("/preview", response_class=HTMLResponse)
def preview(id: int):
    field_mapping = {
        "contributors": "Author(s)",
        "publisher": "Publisher",
        "publicationDate": "Publication Date",
        "generalFormat": "General Format",
        "specificFormat": "Specific Format",
    }

    metadata = worldcat_api.get_metadata(oclc=id)
    html_metadata = ""
    for key, value in field_mapping.items():
        if x := metadata.get(key):
            if key == "generalFormat" and x.lower() in worldcat_api.types:
                x = worldcat_api.types[x.lower()]
            elif key == "specificFormat" and x.lower() in worldcat_api.subtypes:
                x = worldcat_api.subtypes[x.lower()]
            elif key == "contributors":
                x = "; ".join(
                    [
                        f"{y.get('firstName', {}).get('text', '')} "
                        + f"{y.get('secondName', {}).get('text', '')}"
                        for y in metadata.get("contributors", [])
                    ]
                )
            html_metadata += f"<p>{value}: {x}</p>"

    return f"""
    <html>
        <head><meta charset="utf-8" /></head>
        <body>
        <div style="font-weight:bold">
            {metadata['title']}
        </div>
        <div style="font-size:12px">
            {html_metadata}
        </div>
        </body>
    </html>
    """


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
