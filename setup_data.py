"""Download Pima Indians Diabetes dataset without pandas dependency."""
import csv
import urllib.request

URL = "https://raw.githubusercontent.com/jbrownlee/Datasets/master/pima-indians-diabetes.data.csv"
COLUMNS = [
    "Pregnancies", "Glucose", "BloodPressure", "SkinThickness", "Insulin",
    "BMI", "DiabetesPedigreeFunction", "Age", "Outcome",
]

print("Downloading dataset...")
with urllib.request.urlopen(URL, timeout=60) as response:
    lines = response.read().decode("utf-8").strip().split("\n")

rows = [line.split(",") for line in lines if line.strip()]
with open("data/diabetes.csv", "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(COLUMNS)
    writer.writerows(rows)

print(f"Saved data/diabetes.csv with {len(rows)} rows")
