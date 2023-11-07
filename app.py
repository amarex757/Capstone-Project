from models import db, connect_db, User, FavoriteRecipe, Allergy, DietaryRestriction, UserAllergy, UserDiet, UserRecipe
from forms import AddUserForm, LoginForm, UserEditForm, SearchIngredientsForm, AddRecipeForm
from flask import Flask, request, render_template, redirect, flash, session, g, jsonify
from flask_debugtoolbar import DebugToolbarExtension
from sqlalchemy.exc import IntegrityError
from bs4 import BeautifulSoup
from secret import API_KEY
from app import app
import requests
# from flask import current_app


API_BASE_URL = "https://api.spoonacular.com/recipes"
API_KEY = API_KEY
CURR_USER_KEY = "curr_user"
html_instructions = '<ol><li>'

diets = ['Gluten Free', 'Ketogenic', 'Vegetarian', 'Lacto-Vegetarian', 'Ovo-Vegetarian', 'Vegan', 'Pescetarian', 'Paleo', 'Primal', 'Low FODMAP', 'Whole 30']
allergies = ['Dairy', 'Egg', 'Gluten', 'Grain', 'Peanut', 'Seafood', 'Sesame', 'Shellfish', 'Soy', 'Sulfite', 'Tree Nut', 'Wheat']

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql:///recipes_db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ECHO'] = False
app.config['SECRET_KEY'] = 'secret'
app.config['DEBUG_TB_INTERCEPT_REDIRECTS'] = True

debug = DebugToolbarExtension(app)
connect_db(app)
app.app_context().push()
db.create_all()

for diet in diets:
    dietary_restriction = DietaryRestriction(type=diet)
    db.session.add(dietary_restriction)

for allergy in allergies:
    user_allergy = Allergy(type=allergy)
    db.session.add(dietary_restriction)
db.session.commit()

"""USER TO FLASK GLOBAL"""
@app.before_request
def add_user_to_g():
    # once logged in: add current user to Flask global.
    if CURR_USER_KEY in session:
        g.user = User.query.get(session[CURR_USER_KEY])
    else:
        g.user = None

"""LOG IN USER"""
def do_login(user):
    # log in users
    session[CURR_USER_KEY] = user.id
"""LOG OUT USER"""
def do_logout():
    if CURR_USER_KEY in session:
        del session[CURR_USER_KEY]

"""FETCH DATA FROM API IF USER LOGGED IN"""
@app.route("/", method=["GET"])
def populate_date():
    # fetch data from API if user logged in

    if not g.user:
        return render_template("home-login.html")
    else:
        user_allergens = g.user.get_allergies()
        user_diet = g.user.get_diet()

        if not user_allergens:
            user_allergens = []
        if not user_diet:
            user_diet = []
        response = requests.get(
            f'{API_BASE_URL}/complexSearch',
            params={
                'intolerance': ','.join(user_allergens),
                'apiKey': API_KEY,
                'number': 10,
                'diet': user_diet,
                'sort': 'random'
            })
        data  = response.json()
        recipe_data = data["results"]
        #recipes = [{"name": recipe["title"], "id": recipe.get("id", "")} for recipe in recipe_data]
        #return render_template('home.html', recipes=recipes)
        recipe_list = [{"name": recipe["title"], "id": recipe.get("id", "")} for recipe in recipe_data]
        return render_template('home.html', recipe_list=recipe_list)


######################################################
##################___USER ROUTES__####################
######################################################

"""SIGNUP."""
@app.route("/register", methods=["GET", "POST"])
def register():
    # handle user signup
    # create user / add to db / redirect to home
    if CURR_USER_KEY in session:
        del session[CURR_USER_KEY]
    form = AddUserForm()

    if form.validate_on_submit():
        try:
            user = User.register(
                username = form.username.data,
                password = form.password.data,
                email = form.email.data
            )
            db.session.commit()

        except IntegrityError as e:
            flash("Username in use, please retry", "danger")
            return render_template("users/register.html", form=form)
        
        do_login(user)

        flash(f"Welcome, {user.username}", 'success')
        return redirect("/")
    
    else:
        return render_template("users/register.html", form=form)

"""LOGIN."""
@app.route("/login", methods=["GET", "POST"])
def login():
    form = LoginForm()
    if form.validate_on_submit(): 
        user = User.authenaticate(form.username.data, form.password.data)
        
        if user:
            do_login(user)
            flash(f"Welcome back, {user.username}!", "success")
            return redirect("/")
        
        flash("Invalid username/password. Please try again", "danger")
        
    return render_template("users/login.html", form=form)

"""LOGOUT."""
@app.route("/logout")
def logout():
    do_logout()
    flash("You are successfully logged out", "success")
    return redirect("/login")

"""VIEW PROFILE."""
@app.route("/profile/<int:user_id>", methods=["GET"])
def view_profile(user_id):
    user = User.query.get_or_404(user_id)
    allergies = user.allergies
    diet_restrictions = user.diet_restrictions
    
    if not g.user:
        flash("User profile unavailable", "danger")
        return redirect("/")
    return render_template("users/detail.html", user=user, allergies=allergies, diet_restrictions=diet_restrictions)

"""EDIT PROFILE."""
@app.route("/profile/<int:user_id>/edit", methods=["GET", "POST"])
def edit_profile(user_id):

    user = User.query.get_or_404(user_id)
    allergies = Allergy.query.all()
    diet_restrictions = DietaryRestriction.query.all()

    form = UserEditForm(request.form, obj=user)

    if not g.user:
        flash("Unable to view other users' profiles", "danger")
        return redirect("/")

    if request.method == 'POST' and form.validate_on_submit():
        user.username = form.username.data
        user.email = form.email.data

        allergy_id = int(request.form.get("allergies")) if request.form.get(
            'allergies') != 'None' else None        
        diet_restrictions_id = int(request.form.get("diet_restrictions")) if request.form.get(
            'diet_restrictions') != 'None' else None
        
        if user.has_allergy(allergy_id):
            flash("Allergy in use.", "warning")
            return redirect(f"/profile/{g.user.id}/edit")
        elif user.has_diet(diet_restrictions_id):
            flash("Dietary Restrictions in use.", "warning")
            return redirect(f"/profile/{g.user.id}/edit")
        else:
            user.allergies_id = allergy_id
            user.diet_restrictions_id = diet_restrictions_id
        
        new_allergies = request.form.getlist('allergies')
        if 'None' not in new_allergies:
            for allergy_id in new_allergies:
                if not user.has_allergy(int(allergy_id)):
                    user_allergy = UserAllergy(
                        user_id=user.id, allergy_id=int(allergy_id))
                    db.session.add(user_allergy)     

        new_diet_restrictions = request.form.getlist('diet_restrictions')
        if 'None' not in new_diet_restrictions:
            for allergy_id in new_diet_restrictions:
                if not user.has_diet(int(diet_restrictions_id)):
                    user_diet_restriction = UserDiet(
                        user_id=user.id, diet_restrictions_id=int(diet_restrictions_id))
                    db.session.add(user_diet_restriction)

        db.session.commit()
        flash("Profile updated successfully.", "success")
        return redirect(f"/profile/{g.user.id}")
    
    return render_template("users/edit.html", form=form, user=user, allergies=allergies, diet_restrictions=diet_restrictions)


"""DELETE USER."""
@app.route("/profile/delete", methods=["POST"])
def delete_profile():

    if g.user:
        do_logout()
        db.session.delete(g.user)
        db.session.commit()
        flash(f"{g.user.username} updated successfully.", "success")
        return redirect("/")
    
#################################################
#####################__RECIPE ROUTES__###########
#################################################

"""SHOW RECIPE DETAILS"""
@app.route("/recipes/<int:recipe_id>", methods=["GET", "POST"])
def show_recipe(recipe_id):
    if not g.user:
        flash("Please login to a profile to view and favorite recipes", "danger")
        return redirect("/login")
    
    response  = requests.get(f'{API_BASE_URL}/{recipe_id}/information?includeNutrition=false&apiKey={API_KEY}')
    if response.status_code == 200:
        data  = response.json()
        if 'title' in data:
            title = data['title']
            if 'image' in data:
                photo_url =  data['image']
            else:
                photo_url = '' 
            ingredients = [ingredient['original'] for ingredient in data['extendedIngredients']]
            instructions_html = data['instructions']
            soup = BeautifulSoup(instructions_html, 'html.parser')
            instructions = soup.get_text()
            return render_template("recipes/detail.html", title=title, photo_url=photo_url)        
        else:
            return "Title not found in JSON response" 
    else:
        return f"Error: {response.status_code}, {response}"

"""FAVORITED RECIPES"""
@app.route("/favorited", methods=["GET"])
def list_favorited():
    # Page of Logged In User Favorited Recipes.
    if not g.user:
        flash("Login to your profile to save favorited recipes", "danger")
        return redirect("/login")
    
    user = User.query.filter_by(id=g.user.id).first()
    favorited = []

    for favorite in user.favorites:
        recipe_id = favorite.recipe_id
        response = requests.get(f'{API_BASE_URL}/{recipe_id}/information?includeNutrition=false&apiKey={API_KEY}')
        recipe_data = response.json()
        recipe_name = recipe_data.get('title', 'N/A')
        recipe_info = {'recipe_id': recipe_id, 'recipe_name': recipe_name}
        favorited.append(recipe_id)
    return render_template("recipes/favorited.html", favorited=favorited)

"""ADD FAVORITE RECIPE"""
@app.route('favorited/<int:recipe_id>', methods=["POST"])
def add_favorite(recipe_id):
    if not g.user:
        flash("Login to add to favorites", "danger")
        return redirect('/login')

    response = requests.get(f'{API_BASE_URL}/{recipe_id}/information?includeNutrition=false&apiKey={API_KEY}')
    if response.status_code == 200:
        data = response.json()
        recipe_name = data.get('title')
        recipe_id = data.get('id')
        new_favorite = FavoriteRecipe(user_id=g.user.id, recipe_id=recipe_id)
        db.session.add(new_favorite)
        db.session.commit()

        flash(f"{recipe_name} saved to favorites!", "success")
        return redirect(f'/recipes/{recipe_id}')
    else:
        flash("Error saving recipe to favorites", "danger")

"""SEARCH INGREDIENT"""
@app.route("/search", methods=["GET", "POST"])
def search_ingredient():
    if not g.user:
        flash("Sign up or Register to search recipes", "danger")
        return redirect('/')
    
    form = SearchIngredientsForm()
    if request.method == "POST":
        ingredients = request.form.get("ingredients")
        user_allergens = g.user.get_allergies()
        user_diet = g.user.get_diet()

        if not user_allergens:
            user_allergens = []
        if not user_diet:
            user_diet = []

        response = requests.get(
            f'{API_BASE_URL}/complexSearch',
            params={
                'intolerances': ','.join(user_allergens),
                'diet': ','.join(user_diet),
                'number': 10,
                'apiKey': API_KEY,
                'query': ingredients,
                'sort': 'random'
            })
        
        if response.status_code == 200:
            data = response.json()
            recipe_data = data["results"]
            recipes = [{"name": recipe["title"], "id": recipe.get("id", "")} for recipe in recipe_data]
            if not recipes:  # <-- check if recipes list is empty
                flash("No recipes were found with your selected allergies and dietary restrictions.", "warning")
            else:
                return render_template("recipes/search.html", recipes=recipes, form=form)
    return render_template("recipes/search.html", form=form)


"""UNFAVORITE RECIPE"""
@app.route('/favorited/<int:recipe_id>/delete', methods=["POST"])
def unfavorite_recipe(recipe_id):
    if not g.user:
        flash("You must be logged into a profile.", "danger")
        return redirect("/login")
    favorite_recipe = FavoriteRecipe.query.filter_by(user_id=g.user.id, recipe_id=recipe_id).first()
    db.session.delete(favorite_recipe)
    db.session.commit()
    flash("Recipe has been unfavorited.", "success")
    return redirect("/favorited")

##############################################
#####################__REMOVE TAGS__##########
##############################################

"""REMOVE ALLERGY"""
@app.route('/remove-allergy/int:user_allergy_id>', methods=["POST"])
def remove_allergy(user_allergy_id):
    if not g.user:
        flash("You must be logged into a profile.", "danger")
        return redirect("/login")
    
    user_allergy = UserAllergy.query.get_or_404((g.user.id, user_allergy_id))
    db.session.delete(user_allergy)
    db.session.commit()
    flash(f"Allergy discarded from {g.user.username} profile.", "success")
    # flash(f"Allergy discarded from {g.user.username}'s profile", "success")
    return redirect(f"/profile/{g.user.id}")

"""REMOVE DIET RESTRICTION"""
@app.route('/remove-diet/<int:user_restriction_id>', methods=["POST"])
def remove_restriction(user_restriction_id):
    if not g.user:
        flash("You must be logged into a profile.", "danger")
        return redirect("/login")
    
    user_diet = UserDiet.query.get_or_404((g.user.id, user_restriction_id))
    db.session.delete(user_diet)
    db.session.commit()
    flash(f"Dietary Restriction discarded from {g.user.username} profile.", "success")
    return redirect(f"/profile/{g.user.id}")

##############################################
#####################__ADD RECIPE__###########
##############################################

"""LOGGED IN USER RECIPES"""
@app.route('/user-recipes', methods=['GET'])
def g_user_added_recipes():
    """Page of Logged In User's Added Recipes."""
    if not g.user:
        flash("Login to add personalized recipes", "danger")
        return redirect("/login")
    user_recipes = UserRecipe.query.filter_by(user_id=g.user.id).all()
    return render_template('add-recipes/user-recipes.html', user_recipes=user_recipes)

"""ADD RECIPES"""
@app.route('/add-recipe', methods=["GET", "POST"])
def added_recipes():
    if not g.user:
        flash("You must be logged into a profile.", "danger")
        return redirect("/login")
    form = AddRecipeForm()
    if form.validate_on_submit():
        recipe = UserRecipe(
            title = form.title.data,
            photo_url = form.photo_url.data, 
            ingredients = form.ingredients.data, 
            instructions = form.instructions.data, 
            user_id = g.user.id)
        db.session.add(recipe)
        db.session.commit()
        flash(f"{recipe.title} recipe added.", "success")
        return redirect(f"/user-recipes/{recipe.id}")
    return render_template("add-recipe/add.html", form=form)

"""SHOW USER RECIPES"""
@app.route('/user-recipes/<int:recipe_id>', methods=["GET"])
def show_user_recipe_info(recipe_id):
    if not g.user:
        flash("You must be logged in to view and add recipes.", "danger")
        return redirect("/login")
    user_recipe = UserRecipe.query.get_or_404(recipe_id)
    return render_template("add-recipes/show.html", user_recipe=user_recipe)

"""DELETE USER RECIPES"""
@app.route('/delete/<int:recipe_id>', methods=["POST"])
def delete_recipe(recipe_id):
    # Delete user recipe.

    if not g.user:
        flash("You must log in to contiue", "danger")
        return redirect("/login")
    
    recipe = UserRecipe.query.get_or_404(recipe_id)
    db.session.delete(recipe)
    db.session.commit()
    flash(
        f"{recipe.title} has been deleted.", "success")
    return redirect("/user-recipes")

##############################################
#####################__END OF ROUTES__########
##############################################
