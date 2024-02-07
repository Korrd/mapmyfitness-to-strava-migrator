build:
	pipreqs --force --mode compat

clean:
	rm -rf __pycache__

setup: requirements.txt
	pip install -r requirements.txt

lint:
	pylint *.py