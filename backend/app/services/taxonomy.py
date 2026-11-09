"""Small, hand-curated vocabularies used by the rule-based profile extractor.

Extend these freely; every new entry immediately improves resume parsing.
"""

import re

# canonical topic -> aliases (all matched case-insensitively on word boundaries)
TOPICS: dict[str, list[str]] = {
    "Natural Language Processing": [
        "natural language processing", "nlp", "computational linguistics",
        "text mining", "language understanding", "named entity recognition",
        "sentiment analysis", "text classification", "question answering",
        "text summarization",
    ],
    "Large Language Models": [
        "large language model", "large language models", "llm", "llms", "gpt",
        "prompt engineering", "in-context learning", "instruction tuning", "rlhf",
        "retrieval-augmented generation", "retrieval augmented generation", "rag",
        "fine-tuning language models",
    ],
    "Machine Translation": ["machine translation", "neural machine translation", "nmt"],
    "Deep Learning": [
        "deep learning", "neural network", "neural networks", "cnn", "rnn", "lstm",
        "transformer", "transformers", "attention mechanism",
    ],
    "Machine Learning": [
        "machine learning", "supervised learning", "unsupervised learning",
        "statistical learning", "random forest", "gradient boosting", "xgboost",
        "support vector machine", "svm",
    ],
    "Computer Vision": [
        "computer vision", "image classification", "object detection",
        "image segmentation", "visual recognition",
    ],
    "Multimodal Learning": ["multimodal", "vision-language", "vision language", "image captioning"],
    "Reinforcement Learning": ["reinforcement learning", "q-learning", "policy gradient"],
    "Generative Models": [
        "generative model", "generative models", "diffusion model", "diffusion models",
        "generative adversarial", "gan", "gans", "variational autoencoder", "vae",
    ],
    "Graph Neural Networks": ["graph neural network", "graph neural networks", "gnn", "gnns"],
    "Information Retrieval": [
        "information retrieval", "recommender system", "recommender systems",
        "recommendation system", "semantic search", "search engine",
    ],
    "Speech Processing": [
        "speech recognition", "speech processing", "text-to-speech", "speech synthesis", "asr",
    ],
    "Knowledge Graphs": ["knowledge graph", "knowledge graphs", "ontology", "semantic web"],
    "Robustness & Safety": [
        "adversarial robustness", "adversarial examples", "robustness", "ai safety",
        "alignment", "interpretability", "explainable ai", "xai", "fairness",
    ],
    "Federated & Privacy-preserving Learning": [
        "federated learning", "differential privacy", "privacy-preserving",
    ],
    "Data Mining": ["data mining", "anomaly detection", "clustering", "time series"],
    "Optimization": ["optimization", "convex optimization", "bayesian optimization"],
    "Bioinformatics & Health AI": [
        "bioinformatics", "medical imaging", "clinical nlp", "drug discovery",
    ],
}

SKILLS: list[str] = [
    "Python", "PyTorch", "TensorFlow", "Keras", "scikit-learn", "Pandas", "NumPy",
    "Hugging Face", "JAX", "CUDA", "OpenCV", "NLTK", "spaCy", "LangChain",
    "Java", "C++", "JavaScript", "TypeScript", "Rust", "Go", "MATLAB", "Julia",
    "SQL", "PostgreSQL", "MongoDB", "Spark", "Hadoop",
    "Docker", "Git", "Linux", "Kubernetes", "FastAPI", "Flask", "Django", "React",
    "LaTeX", "R",
]


def term_pattern(term: str) -> re.Pattern:
    """Word-boundary-ish pattern that also works for terms like 'C++'."""
    return re.compile(r"(?<![A-Za-z0-9+#])" + re.escape(term) + r"(?![A-Za-z0-9+#])", re.IGNORECASE)


def count_term(text: str, term: str) -> int:
    return len(term_pattern(term).findall(text))
