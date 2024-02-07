build:
	pipreqs --force --mode compat

clean:
	rm -rf __pycache__

# run:
# 	python3 run.py

setup: requirements.txt
	pip install -r requirements.txt
