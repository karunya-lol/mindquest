import os
import joblib
import pandas as pd

from sklearn.model_selection import train_test_split
from sklearn.pipeline import FeatureUnion, Pipeline
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(BASE_DIR, "data", "training_data.csv")
MODEL_PATH = os.path.join(BASE_DIR, "mindquest_model.pkl")


# ---------------------------------------------------------
# Load dataset
# ---------------------------------------------------------

df = pd.read_csv(DATA_PATH)

required_columns = {"text", "category"}

if not required_columns.issubset(df.columns):
    raise ValueError(
        f"Dataset must contain these columns: {required_columns}"
    )

df = df[["text", "category"]].dropna()

df["text"] = df["text"].astype(str).str.strip()
df["category"] = df["category"].astype(str).str.strip()

df = df[df["text"] != ""]
df = df.drop_duplicates()

print(f"Training examples: {len(df)}")
print("\nCategories:")
print(df["category"].value_counts())


# ---------------------------------------------------------
# Train / validation split
# ---------------------------------------------------------

X = df["text"]
y = df["category"]

try:
    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.20,
        random_state=42,
        stratify=y
    )
except ValueError:
    # Fallback if a category has too few examples
    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.20,
        random_state=42
    )


# ---------------------------------------------------------
# Word + character TF-IDF
# ---------------------------------------------------------

features = FeatureUnion([
    (
        "word_features",
        TfidfVectorizer(
            lowercase=True,
            strip_accents="unicode",
            ngram_range=(1, 2),
            min_df=1,
            sublinear_tf=True,
            max_features=12000
        )
    ),
    (
        "character_features",
        TfidfVectorizer(
            analyzer="char_wb",
            lowercase=True,
            ngram_range=(3, 5),
            min_df=1,
            sublinear_tf=True,
            max_features=12000
        )
    )
])


# ---------------------------------------------------------
# Classifier
# ---------------------------------------------------------

model = Pipeline([
    ("features", features),
    (
        "classifier",
        LogisticRegression(
            max_iter=3000,
            class_weight="balanced",
            random_state=42
        )
    )
])


# ---------------------------------------------------------
# Validation
# ---------------------------------------------------------

print("\nTraining model...")

model.fit(X_train, y_train)

predictions = model.predict(X_test)

accuracy = accuracy_score(y_test, predictions)

print(f"\nValidation accuracy: {accuracy:.2%}")

print("\nClassification report:")
print(
    classification_report(
        y_test,
        predictions,
        zero_division=0
    )
)


# ---------------------------------------------------------
# Final training on all available data
# ---------------------------------------------------------

print("\nTraining final model on complete dataset...")

model.fit(X, y)


# ---------------------------------------------------------
# Save
# ---------------------------------------------------------

joblib.dump(model, MODEL_PATH)

print("\nModel saved successfully:")
print(MODEL_PATH)

print("\nFinal categories:")
print(sorted(model.classes_))

print("\nMindQuest ML model is ready.")