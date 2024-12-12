tests: tests/*_tests.py FORCE
	python3 -m unittest -v tests/*_tests.py

coverage: tests/*_tests.py FORCE
	coverage run -m unittest -v tests/*_tests.py
	coverage xml --include=.,src/bibtex_validator/* --omit=tests/*,*__init__.py
	coverage report -im --include=.,src/bibtex_validator/* --omit=tests/*,*__init__.py

pylint: FORCE
	pylint --exit-zero --output-format=text src/bibtex_validator

FORCE: ;