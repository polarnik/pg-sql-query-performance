PYTHON ?= python3.13
VENV   := .venv

.PHONY: dashboards venv clean

dashboards: $(VENV)/bin/python
	$(VENV)/bin/python generate.py

venv: $(VENV)/bin/python

$(VENV)/bin/python: requirements.txt
	$(PYTHON) -m venv $(VENV)
	$(VENV)/bin/pip install -q --disable-pip-version-check -r requirements.txt
	touch $(VENV)/bin/python

clean:
	rm -rf $(VENV)
