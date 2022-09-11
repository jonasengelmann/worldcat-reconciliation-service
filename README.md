# Worldcat-reconciliation-service
[![License](https://img.shields.io/github/license/FAIRDataTeam/OpenRefine-metadata-extension)](LICENSE)

[OpenRefine](http://openrefine.org) reconciliation service for [Worldcat](https://www.worldcat.org).

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
```
pre-commit install
```

Start the reconciliation service:
```
uvicorn main:app --reload --port 8000
```

## License

This project is licensed under MIT license - see the [LICENSE](LICENSE) file for more information.
