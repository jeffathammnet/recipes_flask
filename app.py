from flask import Flask, render_template, request, flash, redirect, url_for, session
from flask_redis import FlaskRedis
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import or_
import uuid
from cfg import config

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = config.SQLALCHEMY_DATABASE_URI
app.config['SECRET_KEY'] = config.SECRET_KEY
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = config.SQLALCHEMY_TRACK_MODIFICATIONS
REDIS_URL = config.REDIS_URL

db = SQLAlchemy(app)
r = FlaskRedis(app)

class Recipes(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)
    healthy = db.Column(db.Boolean(), nullable=False)
    prepTime = db.Column(db.Integer, nullable=False)
    cookTime = db.Column(db.Integer, nullable=False)
    servings = db.Column(db.Integer, nullable=False)
    ingredients = db.Column(db.String(10000), nullable=False)
    directions = db.Column(db.String(10000), nullable=False)

    def __repr__(self):
        return '<Recipe %r>' % self.name

@app.before_request 
def before_request_callback():
    #Create a session ID for the user
    if not "uid" in session:
        session['uid'] = uuid.uuid1().int

@app.route("/")
def index():
    return redirect(url_for("view_get"))

@app.route("/new")
def new_get():
    '''Create a new recipe entry
    '''
    return render_template("new.html")

@app.route("/new", methods=["POST"])
def new_post():
    '''Add new recipe entry to DB
    '''
    new_recipe = Recipes(
        name = request.form.get('title'),
        healthy = True if request.form.get('healthy-bool') else False,
        prepTime = int(request.form['prep-time']) if request.form.get('prep-time').isnumeric() else 0,
        cookTime = int(request.form['cook-time']) if request.form.get('cook-time').isnumeric() else 0,
        servings = int(request.form['servings']) if request.form.get('servings').isnumeric() else 0,
        ingredients = request.form.get('ingredients'),
        directions = request.form.get('directions')
    )
    db.session.add(new_recipe)
    db.session.commit()
    flash("Recipe addedd successfully")

    return redirect(url_for("new_get"))

@app.route("/view")
def view_get():
    '''View all recipes
    '''
    j2_data = {'recipes': Recipes.query.all() }

    return render_template("view.html", j2_data=j2_data)

@app.route("/view/<int:recipeID>")
def view_id_get(recipeID):
    '''View specific recipe
    '''
    recipe = Recipes.query.filter(Recipes.id == recipeID).first()
    j2_data = {'single_recipe': 
        {
            "recipe": recipe,
        }
    }
    return render_template("view.html", j2_data=j2_data)

@app.route("/view", methods=["POST"])
def view_post():
    '''Add new recipe entry to DB
    '''
    print(request.form)
    recipe = Recipes.query.filter(Recipes.id==request.form.get("recipeID")).first()
    
    recipe.name = request.form.get('title')
    recipe.healthy = True if request.form.get('healthy-bool') else False
    recipe.prepTime = int(request.form['prep-time']) if request.form.get('prep-time').isnumeric() else 0
    recipe.cookTime = int(request.form['cook-time']) if request.form.get('cook-time').isnumeric() else 0
    recipe.servings = int(request.form['servings']) if request.form.get('servings').isnumeric() else 0
    recipe.ingredients = request.form.get('ingredients')
    recipe.directions = request.form.get('directions')
    
    db.session.commit()
    flash("Recipe updated successfully")

    return redirect(url_for("view_get")+"/"+request.form["recipeID"])

@app.route("/menu", methods=["GET"])
def menu_get():
    '''View menu for current user session
    '''
    j2_data = {}

    #Validate user has items in menu
    if r.llen(session['uid']) > 0:
        j2_data['recipes'] = []

        #Query for menu item details
        for menuID in r.lrange(session['uid'],0,-1):
            j2_data['recipes'].append(Recipes.query.filter(Recipes.id==int(menuID)).first())

    return render_template("menu.html", j2_data=j2_data)

@app.route("/menu", methods=["POST"])
def menu_post():
    '''Update menu for current user session
    '''
    #Delete all items from menu
    if request.form.get('reset_menu'):
        r.delete(session['uid'])
        flash("Menu has been cleared")
    #Remove 1 occurence of menu item form list
    elif request.form.get('remove_menu_item'):
        r.lrem(session['uid'],1, request.form['remove_menu_item'])
    #Add random items to menu
    elif request.form.get('add_random_count'):
        add_random_count = int(request.form.get('add_random_count', 0))
        found_count = 0
        loop_count = 0
        #Search up to 10 times to find unique number of menu items requested.
        while found_count < add_random_count and loop_count <= 10:
            random_recipes = Recipes.query.order_by(db.func.random()).limit(int(request.form['add_random_count'])).all()
            for recipe in random_recipes:
                if not bytes(str(recipe.id), encoding="utf8") in r.lrange(session['uid'],0,-1):
                    r.lpush(session['uid'], recipe.id)
                    found_count += 1
            loop_count += 1
        if loop_count > 10:
            flash("Not able to find enough recipes")
        flash("Random recipes added")
    #Add single item to menu
    else:
        if not bytes(str(request.form['recipeID']), encoding="utf8") in r.lrange(session['uid'],0,-1):
          r.lpush(session['uid'], int(request.form.get('recipeID')))
        else:
            flash("Recipe already added to menu.")

    return redirect(url_for("menu_get"))

@app.route("/search")
def search_get():
    '''Search recipe title and ingrediants to find a match
    '''
    j2_data = {}
    query = request.args.get('q')

    search_result = j2_data['recipes'] = Recipes.query.filter(or_(Recipes.name.like(f"%{query}%"),Recipes.ingredients.like(f"%{query}%"))).all()
        
    if not search_result:
        flash("No items found")

    return render_template("view.html", j2_data=j2_data)

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True, port=8443, ssl_context=(config.SSL_CERTIFICATE, config.SSL_KEY))
