# Fetching data from the API

import requests
import os
import json

CACHE_FILE = "ingredients.json"
url = "https://exactcup.github.io/api/v1/ingredients.json"

if os.path.exists(CACHE_FILE):
    # Load existing cached data if it exists
    print('Loading from cache')
    with open(CACHE_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

else:
    # Fetch data from API and check it came through successfully
    print('Fetching from API')
    response = requests.get(url)
    response.raise_for_status()

    data = response.json()

    # Save it for future runs
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

#Inspecting what came back

ingredients = data["ingredients"]

print(type(ingredients))
print(len(ingredients))
print(ingredients[0])

import pandas as pd

df = pd.DataFrame(ingredients)

print(df.head())
print(df.columns)