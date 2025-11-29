# %%
# importing necessary libraries
import pandas as pd
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, confusion_matrix, classification_report
import matplotlib.pyplot as plt
from sklearn.preprocessing import LabelEncoder, StandardScaler


# %%
df = pd.read_csv("output_file.csv")

df.head()

# %%
# defined some stopwords manually to remove them
urdu_stopwords = [
    "کی","اس","کے", "ہے", "اور", "میں", "سے", "کو", "کا", "کر", "یہ", "نے", "تو", "پر", "بھی",
]

def remove_stopwords(text, stopwords_list):
    if not isinstance(text, str):
        return text
    words = text.split()  
    filtered_words = [word for word in words if word not in stopwords_list] 
    return " ".join(filtered_words)

# %%
#preprocessing
df['cleaned_content'] = df['content'].fillna("").apply(lambda x: " ".join([word for word in x.split() if word not in urdu_stopwords]))

# %%
#manual implementation of logistic regression
class LogisticRegression:
    def __init__(self, learning_rate=0.01, num_iter=1000, regularization=0.01):
        self.learning_rate = learning_rate
        self.num_iter = num_iter
        self.regularization = regularization
        self.weights = None
        self.bias = 0

    def sigmoid(self, x):
        return 1 / (1 + np.exp(-x))

    def cross_entropy_loss(self, y_true, y_pred):
        m = y_true.shape[0]
        y_pred = np.clip(y_pred, 1e-15, 1 - 1e-15) #wanted to avoid log(0) errors
        loss = -(1 / m) * (np.dot(y_true, np.log(y_pred)) + np.dot(1 - y_true, np.log(1 - y_pred)))
        reg = (self.regularization / (2 * m)) * np.sum(np.square(self.weights))
        return loss + reg

    def fit(self, x_train, y_train):
        m, n = x_train.shape
        self.weights = np.zeros(n)
        self.bias = 0
        costs = []

        for _ in range(self.num_iter):
            linear_model = np.dot(x_train, self.weights) + self.bias
            y_pred = self.sigmoid(linear_model)

            gradient_weight = (1 / m) * np.dot(x_train.T, (y_pred - y_train)) + (self.regularization / m) * self.weights
            gradient_bias = (1 / m) * np.sum(y_pred - y_train)

            self.weights -= self.learning_rate * gradient_weight
            self.bias -= self.learning_rate * gradient_bias

            loss = self.cross_entropy_loss(y_train, y_pred)
            costs.append(loss)

        return costs

    def predict(self, x_test):
        linear_model = np.dot(x_test, self.weights) + self.bias
        y_pred_prob = self.sigmoid(linear_model)
        y_pred_class = [1 if i > 0.5 else 0 for i in y_pred_prob]
        return np.array(y_pred_prob), np.array(y_pred_class)

    def evaluate(self, y_true, y_pred):
        accuracy = accuracy_score(y_true, y_pred)
        f1 = f1_score(y_true, y_pred)
        conf_matrix = confusion_matrix(y_true, y_pred)
        return {
            "accuracy": accuracy,
            "f1_score": f1,
            "confusion_matrix": conf_matrix
        }


# %%
label_encoder = LabelEncoder()
df['encoded_label'] = label_encoder.fit_transform(df['gold_label'])

vectorizer = TfidfVectorizer(max_features=1000)
features = vectorizer.fit_transform(df['cleaned_content']).toarray()
labels = df['encoded_label'].values

features_train, features_test, label_train, label_test = train_test_split(features, labels, test_size=0.2, random_state=42)

scaler = StandardScaler()
features_train_norm = scaler.fit_transform(features_train)
features_test_norm = scaler.transform(features_test)

classifiers = {}
losses = {}

for i in range(len(label_encoder.classes_)):
    y_binary = (label_train == i).astype(int)
    model = LogisticRegression(learning_rate=0.01, num_iter=10000, regularization=0.01)
    classifiers[i] = model
    cost = model.fit(features_train_norm, y_binary)
    losses[i] = cost

plt.figure(figsize=(12, 8))
for i in range(len(label_encoder.classes_)):
    plt.plot(losses[i], label=f'Class {label_encoder.classes_[i]}')
plt.xlabel('Iterations')
plt.ylabel('Loss')
plt.legend()
plt.title('Training Loss for One-vs-Rest Logistic Regression')
plt.show()

# %%
results = {
    'Class': [],
    'Probs': [],
    'Accuracy': [],
    'Precision': [],
    'Recall': [],
    'F1 Score': [],
    'Confusion Matrix': []
}

for i in range(len(label_encoder.classes_)):
    y_test_binary = (label_test == i).astype(int)
    probability, predicted_class = classifiers[i].predict(features_test_norm)
    evaluation_metrics = classifiers[i].evaluate(y_test_binary, predicted_class)
    results['Class'].append(label_encoder.classes_[i])
    results['Probs'].append(probability)
    results['Accuracy'].append(evaluation_metrics["accuracy"])
    results['Precision'].append(precision_score(y_test_binary, predicted_class))
    results['Recall'].append(recall_score(y_test_binary, predicted_class))
    results['F1 Score'].append(evaluation_metrics["f1_score"])
    results['Confusion Matrix'].append(evaluation_metrics["confusion_matrix"])

results_df = pd.DataFrame(results)

final_probs = np.array([results['Probs'][i] for i in range(len(label_encoder.classes_))]).T
final_predictions = np.argmax(final_probs, axis=1)

results_df.drop('Probs',axis=1)
results_df

# %%
multi_class_accuracy = accuracy_score(label_test, final_predictions)
multi_class_precision = precision_score(label_test, final_predictions, average='weighted')
multi_class_recall = recall_score(label_test, final_predictions, average='weighted')
multi_class_f1 = f1_score(label_test, final_predictions, average='weighted')
multi_class_confusion_matrix = confusion_matrix(label_test, final_predictions)

print(f"Accuracy: {multi_class_accuracy * 100:.2f}%")
print(f"Precision: {multi_class_precision:.2f}")
print(f"Recall: {multi_class_recall:.2f}")
print(f"F1 Score: {multi_class_f1:.2f}")
print("\nConfusion Matrix:\n", multi_class_confusion_matrix)

class_report = classification_report(label_test, final_predictions, target_names=label_encoder.classes_)
print("\nClassification Report:\n", class_report)


