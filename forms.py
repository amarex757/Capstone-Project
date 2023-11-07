from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, TextAreaField, SelectField
from wtforms.validators import DataRequired, Email, Length, Optional, URL
from models import Allergies, Dietary_Restrictions

class AddUserForm(FlaskForm):
    """Form to add users."""
    username = StringField("Username", validators=[DataRequired()])
    email = StringField("Email", validators=[DataRequired(), Email()])
    password = PasswordField("Password", validators=[Length(min=8)])

class EditUserForm(FlaskForm):
    """Form to add users."""
    username = StringField("Username", validators=[DataRequired()])
    email = StringField("Email", validators=[DataRequired(), Email()])
    allergies = SelectField("Allergies", default=None, validators=[Optional()])
    diet_restrictions = SelectField("Allergies", default=None, validators=[Optional()])

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.allergies.choices = [(None, 'Add Allergy')] + [(allergy.id, allergy.type) for allergy in Allergies.query.all()]
        self.diet_restrictions.choices = [(None, 'Add Dietary Restriction')] + [(diet.id, diet.type) for diet in Dietary_Restrictions.query.all()]

class LoginForm(FlaskForm):
    """Login Form"""
    username = StringField("Username", validators=[DataRequired()])
    password = PasswordField("Password", validators=[Length(min=8)])

class SearchIngredientsForm(FlaskForm):
    ingredients =  StringField("Ingredients", validators=[DataRequired()])

class AddRecipeForm(FlaskForm):
    """Form for adding recipes."""
    title = StringField("", validators=[DataRequired()])   
    photo_url = StringField("Recipe Image", default=None, validators=[Optional(), URL()]) 
    ingredients = TextAreaField("Ingredients", validators=[DataRequired()])    
    instructions = TextAreaField("Instructions", validators=[DataRequired()])