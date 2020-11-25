test:
	pipenv run pytest

package:
	python setup.py sdist bdist_wheel

upload:
	python -m twine upload dist/*

clean:
	rm dist/*

dev_env:
	pip install -e .

requirements.txt:
	pipenv run pip freeze >> requirements.txt