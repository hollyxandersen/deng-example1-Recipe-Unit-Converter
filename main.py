# Fetching data from the API

import requests

url = "https://exactcup.github.io/api/v1/ingredients.json"

response = requests.get(url)

print(response.status_code) # Checking API request status

#Inspecting what came back

data = response.json()

ingredients = data["ingredients"]

print(type(ingredients))
print(len(ingredients))
print(ingredients[0])

import pandas as pd

df = pd.DataFrame(ingredients)

print(df.head())
print(df.columns)