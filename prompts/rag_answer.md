model_prompt = """You are answering a question using ONLY the provided context passages.
If the answer isn't in the context, say so honestly. Cite passages by their [source].

Context:
[1] (source: Wikipedia/Thermodynamics) ...chunk text...
[2] (source: Wikipedia/Entropy) ...chunk text...
...

Question: {user_question}

Answer (with citations like [source: Wikipedia/Thermodynamics]):"""
