from flask_bcrypt import Bcrypt
from flask_sqlalchemy import SQLAlchemy
from app import app

bcrypt = Bcrypt()
db = SQLAlchemy()

def connect_app(db):
    db.app = app 
    db.init_app(app)
    app.app_context().push()

class User(db.Model):
    """User Model"""
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String, nullable=False, unique=True)
    email = db.Column(db.String, nullable=False)
    password = db.Column(db.String, nullable=False)
    favorites = db.relationship("FavoriteRecipe", cascade="all, delete-orphan")
    user_recipes = db.relationship("UserRecipe", backref="user", cascade="all, delete-orphan")
    allergies = db.relationship("UserAllergy", back_populates="user", overlaps="users", cascade="all, delete-orphan")
    diet_restrictions = db.relationship("UserDiet", back_populates="user", overlaps="users", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User #{self.id}: {self.username}, {self.email}>"

    def get_allergies(self):
        # Retrieve the allergies for this user
        allergies = [allergen.allergy.type for allergen in self.allergies]
        return allergies
    
    def has_allergy(self, allergy_id):
        for user_allergy in self.allergies:
            if user_allergy.allergy_id == allergy_id:
                return True
        return False
    
    def get_diet(self):
        # Retrieve the dietary restrictions for this user."""
        diets = [ud.diet_restrictions.type for ud in self.diet_prefs]
        return diets

    def has_diet(self, diet_id):
        for user_diet_restriction in self.diet_restrictions:
            if user_diet_restriction.diet_restriction_id == diet_id:
                return True
        return False

    @classmethod
    def signup(cls, username, email, password):
        # sign up user and hash password
        hashed_pwd = bcrypt.generate_password_hash(password).decode('UTF-8')
        user = User(username=username, email=email, password=hashed_pwd,)
        db.session.add(user)
        return user

    @classmethod
    def authenticate(cls, username, password):
        # Find user with `username` and `password`.
        user = cls.query.filter_by(username=username).first()
        if user:
            is_auth = bcrypt.check_password_hash(user.password, password)
            if is_auth:
                return user
        return False

class DietaryRestriction(db.Model):
    # Dietary Restriction Model"""
    __tablename__ = "diet_restrictions"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    type = db.Column(db.Text)

class Allergy(db.Model):
    # Allergy Model
    __tablename__ = "allergies"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    type = db.Column(db.Text)

class FavoriteRecipe(db.Model):
    # Favorite Recipes Model for User
    __tablename__ = "favorites"
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), primary_key=True)
    recipe_id = db.Column(db.Integer, primary_key=True)

class UserAllergy(db.Model):
    # User-Allergy Association Table
    __tablename__ = "user_allergies"
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), primary_key=True)
    allergy_id = db.Column(db.Integer, db.ForeignKey( "allergies.id"), primary_key=True)
    user = db.relationship("User", back_populates="allergies", overlaps="user_allergies")
    allergy = db.relationship("Allergy", backref="user_allergies")

class UserDiet(db.Model):
    # User-Allergy Association Table
    __tablename__ = "user_diet_restrictions"
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), primary_key=True)
    diet_restrictions_id = db.Column(db.Integer, db.ForeignKey("diet_restrictions.id"), primary_key=True)
    user = db.relationship("User", back_populates="diet_restrictions",  overlaps="user_diet_restrictions")  # Back-reference to User.diet_restrictions
    diet_restriction = db.relationship("DietaryRestriction", backref="user_diet_restriction")

class UserRecipe(db.Model):
    #User-added Recipe Table
    __tablename__ = "user_recipes"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    title = db.Column(db.Text, nullable=False)
    photo_url = db.Column(db.Text, nullable=True)
    ingredients = db.Column(db.Text, nullable=False)
    instructions = db.Column(db.Text, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"))
