import joblib
import pandas as pd

# Load model
model = joblib.load("models/gym_model.pkl")

# Build sample input
sample = pd.DataFrame([{
    "hour": 17,
    "day_of_week": 5,
    "is_weekend": True,
    "location_name_Maguire Field": 1
}])

# Align with training feature order
sample = sample.reindex(columns=model.feature_names_in_, fill_value=0)

# Predict
prediction = model.predict(sample)[0]
print(f"Predicted crowd count: {int(prediction)}")
