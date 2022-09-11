# Worldcat-reconciliation-service
[![CI](https://github.com/jonasengelmann/worldcat-reconciliation-service/actions/workflows/docker-publish.yml/badge.svg?branch=main)](https://github.com/jonasengelmann/worldcat-reconciliation-service/actions)
[![License](https://img.shields.io/github/license/jonasengelmann/worldcat-reconciliation-service)](LICENSE)

[OpenRefine](http://openrefine.org) reconciliation service for [Worldcat](https://www.worldcat.org).


## Run via Docker (Recommended)

```console
docker run -p 8000:80 jonasengelmann/worldcat-reconciliation-service:main
```

## Installation and Deployment

```console
pip3 install -r requirement.txt
```

Start the reconciliation service:
```console
python3 main.py
```

The reconciliation service should now be accessible at [http://localhost:8000](http://localhost:8000). 

## Development

Setup pre-commit hooks:
```console
pre-commit install
```

Start the reconciliation service:
```console
uvicorn main:app --reload --port 8000
```

## Build with Docker

The service can also be built and run using Docker:

```console
docker build -t worldcat-reconciliation-service .
docker run -p 8000:80 worldcat-reconciliation-service
```

## License

This project is licensed under MIT license - see the [LICENSE](LICENSE) file for more information.
