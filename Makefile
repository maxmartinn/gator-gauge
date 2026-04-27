preprocess:
	python scripts/basic_preprocess.py

train:
	python scripts/train_model.py

report:
	python scripts/generate_report.py

dashboard:
	cd dashboard && AWS_PROFILE=gator-gauge streamlit run app.py

all: preprocess train report
