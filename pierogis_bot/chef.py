import io

from pierogis import Pierogi, Recipe, Dish


class Chef:
    def cook_json_pierogi(self, file, ingredients_dict, recipe, files):
        ingredients = {}

        for name, dict_ingredient in ingredients_dict.items():
            if dict_ingredient.get('kwargs', {}).get('path') is not None:
                path = dict_ingredient['kwargs'].pop('path')
                dict_ingredient['kwargs']['file'] = files[path]

            ingredient = Pierogi(*dict_ingredient.get('args'), **dict_ingredient.get('kwargs'))
            ingredients[name] = ingredient

        recipe = Recipe(ingredients=[ingredients[ingredient_name] for ingredient_name in recipe])
        dish = Dish(recipe=recipe)
        dish.serve()

        dish.save(file)
