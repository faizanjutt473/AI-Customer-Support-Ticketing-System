"""Trains the 3 ticket models (category, priority, sentiment) and saves them to ml_models/.

NOTE: The training data below is generated from templates, so it is good enough to demo
the full pipeline. For production, replace it with real labelled tickets (same columns).
"""
import random
from pathlib import Path

import joblib
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import make_pipeline

random.seed(42)
OUT = Path(__file__).parent / "ml_models"
OUT.mkdir(exist_ok=True)

PHRASES = {
    "Billing": [
        "I was charged twice for this month's invoice",
        "My invoice amount is wrong",
        "The payment failed but money left my account",
        "I need to update my card details",
        "Please change the billing address on my account",
        "I was overcharged on my latest bill",
        "I need a copy of last month's invoice",
        "My subscription price went up without notice",
        "The tax on my invoice looks incorrect",
        "My payment is not showing in my account",
    ],
    "Technical": [
        "I cannot log in to my account",
        "The app crashes every time I open it",
        "I get error code 500 on the dashboard",
        "The password reset link is not working",
        "The website is very slow to load",
        "The page keeps freezing and not loading",
        "My account is locked and I cannot access it",
        "There is a bug in the reports section",
        "I cannot upload files, the upload fails",
        "Notifications are not working on my phone",
    ],
    "Refund": [
        "I want a refund for my annual plan",
        "Please give me my money back",
        "I cancelled my order and need a refund",
        "I want to return the product and get a refund",
        "My refund has not arrived yet",
        "What is the status of my refund request",
        "I want to cancel my subscription and get refunded",
        "Please refund the amount, I do not need the service",
        "I was promised a refund but nothing came",
        "I want to cancel my order",
    ],
}
PREFIX = ["", "Hello, ", "Hi team, ", "Please help: ", "Hi, ", "Good morning, "]
TONES = {
    "Angry": [
        " This is unacceptable and I am furious!",
        " Worst service ever, I am fed up.",
        " Terrible support, this is a scam.",
        " This is ridiculous, nobody replies to me.",
    ],
    "Negative": [
        " I am disappointed with this.",
        " This is frustrating.",
        " I am not happy about this.",
        " This has been a poor experience.",
    ],
    "Neutral": ["", ".", " Please check.", " Can you help?", " Waiting for your reply."],
    "Positive": [
        " Thank you, great product!",
        " Thanks a lot, really happy with the team.",
        " Love the service, thanks!",
        " Appreciate your help, thank you.",
    ],
}
URGENT = [" This is urgent.", " I need this fixed immediately.", " Please respond ASAP."]
PRIORITY_BY_SENTIMENT = {"Angry": "Urgent", "Negative": "High", "Neutral": "Normal", "Positive": "Low"}

rows = []
for category, phrases in PHRASES.items():
    for phrase in phrases:
        for sentiment, tails in TONES.items():
            for _ in range(8):
                text = random.choice(PREFIX) + phrase + random.choice(tails)
                priority = PRIORITY_BY_SENTIMENT[sentiment]
                if sentiment in ("Neutral", "Negative") and random.random() < 0.25:
                    text += random.choice(URGENT)
                    priority = "Urgent"
                rows.append((text, category, priority, sentiment))

df = pd.DataFrame(rows, columns=["text", "category", "priority", "sentiment"]).drop_duplicates()
df.to_csv(OUT / "training_data.csv", index=False)
print(f"Training rows: {len(df)}")

for target in ("category", "priority", "sentiment"):
    X_train, X_test, y_train, y_test = train_test_split(
        df["text"], df[target], test_size=0.2, random_state=42, stratify=df[target]
    )
    model = make_pipeline(
        TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True),
        LogisticRegression(max_iter=1000, C=5),
    )
    model.fit(X_train, y_train)
    print(f"{target:10s} test accuracy: {accuracy_score(y_test, model.predict(X_test)):.2%}")
    model.fit(df["text"], df[target])
    joblib.dump(model, OUT / f"{target}.pkl")

print("Models saved in ml_models/")