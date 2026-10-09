.PHONY: install test notebooks
install:
	python -m pip install -e ".[notebooks,dev]"
test:
	python -m pytest -q
	python scripts/validate_notebooks.py
notebooks:
	python -m jupyter lab notebooks/
