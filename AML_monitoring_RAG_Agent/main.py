import os
import random
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

from src.preprocessing import (
    load_dataset,
    create_sample,
    create_stratified_subset,
    save_sample,
    dataset_summary,
)

from src.text_converter import dataframe_to_documents

random.seed(42)
np.random.seed(42)

os.makedirs("data", exist_ok=True)
os.makedirs("outputs", exist_ok=True)

# Load dataset
df = load_dataset("data/HI-Small_Trans.csv")

dataset_summary(df)

print("\nFirst 5 Rows:\n")
print(df.head())

print("\nMissing Values:\n")
print(df.isnull().sum())

print("\nTransaction Statistics:\n")
print(df[["Amount Paid", "Amount Received"]].describe())

print("\nPayment Format Distribution:\n")
print(df["Payment Format"].value_counts())

print("\nReceiving Currency Distribution:\n")
print(df["Receiving Currency"].value_counts())

print("\nPayment Currency Distribution:\n")
print(df["Payment Currency"].value_counts())

print("\nUnique Sender Banks:", df["From Bank"].nunique())
print("Unique Receiver Banks:", df["To Bank"].nunique())

print("\nUnique Sender Accounts:", df["Account"].nunique())
print("Unique Receiver Accounts:", df["Account.1"].nunique())

# Random research sample
sample_df = create_sample(df, sample_size=50000)
save_sample(sample_df, "data/research_sample.csv")

print("\nResearch Sample Created Successfully!")
print(sample_df.shape)
print("\nSample Class Distribution")
print(sample_df["Is Laundering"].value_counts())

# Stratified subset for RAG development
dev_df = create_stratified_subset(df, normal_size=20000)
save_sample(dev_df, "data/dev_subset.csv")

print("\nDevelopment Subset Created Successfully!")
print(dev_df.shape)
print("\nDevelopment Subset Class Distribution")
print(dev_df["Is Laundering"].value_counts())

# Convert development subset into documents
documents = dataframe_to_documents(dev_df)

print("\nFirst AML Document\n")
print(documents[0])

with open("outputs/sample_document.txt", "w", encoding="utf-8") as f:
    f.write(documents[0])

print("\nSample document saved to outputs/sample_document.txt")

plt.figure(figsize=(6,4))
sns.countplot(data=dev_df, x="Is Laundering")
plt.title("Class Distribution (Development Subset)")
plt.savefig("outputs/class_distribution.png")
plt.show()

print("\nMilestone 3 Ready: Development subset + document conversion")