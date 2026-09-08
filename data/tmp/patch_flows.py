import json
path = "data/app/flows.json"
with open(path, encoding="utf-8") as f:
    data = json.load(f)
print(len(data["series"]), data["series"][-1]["date"])
