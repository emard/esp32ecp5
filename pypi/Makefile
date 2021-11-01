dist:
	python setup.py sdist

check: dist
	twine check dist/*

upload: dist
	twine upload dist/*

clean:
	rm -rf dist MANIFEST *~ __pycache__ esp32ecp5.egg-info
