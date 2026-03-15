from sentence_transformers import SentenceTransformer, util

model = SentenceTransformer(
    "onnx_model",
    backend="onnx",
    model_kwargs={"file_name": "model_O4.onnx"}
)

sentences = ["Paris is the capital of France", "Berlin is the capital of Germany"]
embeddings = model.encode(sentences, convert_to_tensor=True)
similarity_matrix = util.cos_sim(embeddings, embeddings)

print(similarity_matrix)    