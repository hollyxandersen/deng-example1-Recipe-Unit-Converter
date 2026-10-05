#Fetch data from API or cache

from api import load_ingredient_data
data = load_ingredient_data()

from transform import make_ingredient_dataframe, make_alias_dataframe
ingredients_df = make_ingredient_dataframe(data)
alias_df = make_alias_dataframe(ingredients_df)

print(alias_df.head())



