.PHONY: preprocess train report dashboard all

preprocess:
	python scripts/basic_preprocess.py

train:
	python scripts/train_model.py

report:
	python scripts/generate_report.py

dashboard:
	cd dashboard && AWS_PROFILE=gator-gauge python3 -m streamlit run app.py

all: preprocess train report
