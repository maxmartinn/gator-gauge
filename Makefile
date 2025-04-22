preprocess:
	python scripts/basic_preprocess.py

train:
	python scripts/train_model.py

report:
	python scripts/generate_report.py

all: preprocess train report
