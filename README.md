# Worldcat-reconciliation-service
[![License](https://img.shields.io/github/license/jonasengelmann/worldcat-reconciliation-service)](LICENSE)

[OpenRefine](http://openrefine.org) reconciliation service for [Worldcat](https://www.worldcat.org).

Implemented query properties are `author` and `publication_year`. 

If there is only need to disambiguate conceptual works, i.e. specific realizations and editions are treated as the same entry, an extension service is provided that allows to extract all OCLC numbers of all editions. Thereby a set of OCLC numbers can be used to unambiguously identify a conceptual work, requiring an entry only to be matched to an arbitrary edition of the work. The extension service can be used as follows:

Edit column -> Add columns from reconciled values... -> OCLC Numbers of all Editions


## Run via Docker-Compose (Recommended)

```console
cp .env.docker-compose .env
docker-compose up --build
```

The reconciliation service should now be accessible at [http://localhost](http://localhost). 

## Development

The reconciliation service requires Selenium and Redis. The easiest way is to run these services via Docker:
```console
docker run --rm -it -p 4444:4444 --shm-size 2g seleniarm/standalone-chromium:latest
docker run --rm -it -p 6379:6379 redis:latest
```

Setup pre-commit hooks:
```console
pre-commit install
```

```console
pip3 install -r requirement.txt
```

Start the reconciliation service:
```console
uvicorn main:app --reload --port 8000 --env-file .env.dev
```

The reconciliation service should now be accessible at [http://localhost:8000](http://localhost:8000). 

## License

This project is licensed under MIT license - see the [LICENSE](LICENSE) file for more information.
