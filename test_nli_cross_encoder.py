# from sentence_transformers import CrossEncoder

# # load model (downloads once, then cached locally)
# model = CrossEncoder("./nli_crossencoder", backend="onnx")

# # input = list of (premise, hypothesis)
# pairs = [
#     ("The contract requires confidentiality.", 
#      "The agreement forbids sharing information."),
    
#     ("The contract allows termination anytime.", 
#      "Termination is restricted.")
# ]

# # get scores
# scores = model.predict(pairs)

# # map to labels
# label_mapping = ["contradiction", "entailment", "neutral"]

# for i, score in enumerate(scores):
#     label = label_mapping[score.argmax()]
#     print(f"Pair {i}: {label}, scores={score}")


from transformers import AutoTokenizer, AutoModelForSequenceClassification
import torch
model_name = "MoritzLaurer/DeBERTa-v3-base-mnli"
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForSequenceClassification.from_pretrained(model_name)
premise = "I first thought that I liked the movie, but upon second thought it was actually disappointing."
hypothesis = "The movie was good."
input = tokenizer(premise, hypothesis, truncation=True, return_tensors="pt")
output = model(input["input_ids"].to(device))  # device = "cuda:0" or "cpu"
prediction = torch.softmax(output["logits"][0], -1).tolist()
label_names = ["entailment", "neutral", "contradiction"]
prediction = {name: round(float(pred) * 100, 1) for pred, name in zip(prediction, label_names)}
print(prediction)
