#Fetch data from API or cache

from api import load_ingredient_data
data = load_ingredient_data()
ingredients = data["ingredients"]
