.PHONY: install test lint eval report up docker-build data fixtures clean

install:
	pip install -e ".[dev]"

data:  ## regenerate the corpus (deterministic, seeded)
	python training/gen_corpus.py --out data/corpus

fixtures:  ## rebuild handwritten + public fixture sets
	python eval/fixtures/build_handwritten.py
	python eval/fixtures/build_public.py

test:
	python -m pytest -q

lint:
	ruff check src tests training eval

eval:  ## rules system over all sets (no model needed)
	spanguard eval --detectors spanguard-rules

report:  ## regenerate README blocks + SVG charts from committed run records
	spanguard report

up:  ## gateway + demo UI on :8819
	spanguard up

docker-build:
	docker build -t spanguard:latest .

gate:  ## eval regression gate (used by CI)
	python -m spanguard.eval.gate

clean:
	rm -rf .pytest_cache .ruff_cache src/*.egg-info
