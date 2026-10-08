


from parser import (
    parse_recipe_text,
)



recipe_text ="""
2 cups plain flour
1 tbsp brown sugar
250 ml milk
1 onion
2 cloves garlic
salt to taste"""

table= parse_recipe_text(recipe_text)

print(table)