PYTHON := .venv/Scripts/python.exe

.PHONY: gif screenshots test

test:
	$(PYTHON) -m unittest discover -s tests -v

screenshots:
	$(PYTHON) run_switcher.py --screenshots

gif: screenshots
	$(PYTHON) switcher/build_gif.py
