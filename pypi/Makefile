dist:
	python setup.py sdist

check: dist
	twine check dist/*

clean:
	rm -rf dist MANIFEST *~ __pycache__ esp32ecp5.egg-info
