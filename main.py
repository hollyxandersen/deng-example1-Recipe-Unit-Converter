


from parser import (
    parse_recipe_text,
)



recipe_text = """
125g caster sugar
125g unsalted butter
softened
2 eggs
1 tsp vanilla extract
125g self-raising flour
ICING
200g icing sugar
1-2 tbsp milk
food colouring, sprinkles, marshmallows
to decorate (optional)
"""

table= parse_recipe_text(recipe_text)

print(table)