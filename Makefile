PYTHON ?= uv run --frozen python

.PHONY: build validate refresh release-check clean

build:
	$(PYTHON) scripts/build.py

validate:
	$(PYTHON) scripts/validate.py

refresh:
	$(PYTHON) scripts/refresh_github.py

release-check: build validate
	$(PYTHON) scripts/release_check.py

clean:
	$(PYTHON) scripts/build.py --clean
