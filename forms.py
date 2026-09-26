from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, TextAreaField, SelectField, SubmitField
from wtforms.validators import DataRequired, Email, Length, EqualTo, Optional


class RegisterForm(FlaskForm):
    username = StringField("Username", validators=[DataRequired(), Length(3, 40)])
    email = StringField("Email", validators=[DataRequired(), Email()])
    password = PasswordField("Password", validators=[DataRequired(), Length(6, 100)])
    confirm = PasswordField("Confirm Password", validators=[DataRequired(), EqualTo("password")])
    submit = SubmitField("Create Account")


class LoginForm(FlaskForm):
    username = StringField("Username", validators=[DataRequired()])
    password = PasswordField("Password", validators=[DataRequired()])
    submit = SubmitField("Login")


class UploadForm(FlaskForm):
    title = StringField("Title", validators=[DataRequired(), Length(3, 200)])
    description = TextAreaField("Description", validators=[Optional()])
    category = SelectField("Category", choices=[], validators=[DataRequired()])
    submit = SubmitField("Upload")


class EditVideoForm(FlaskForm):
    title = StringField("Title", validators=[DataRequired(), Length(3, 200)])
    description = TextAreaField("Description", validators=[Optional()])
    category = SelectField("Category", choices=[], validators=[DataRequired()])
    submit = SubmitField("Save Changes")


class CommentForm(FlaskForm):
    body = TextAreaField("Comment", validators=[DataRequired(), Length(1, 1000)])
    submit = SubmitField("Post")


class SettingsForm(FlaskForm):
    bio = TextAreaField("Bio", validators=[Optional(), Length(0, 500)])
    avatar_url = StringField("Avatar URL", validators=[Optional()])
    banner_url = StringField("Banner URL", validators=[Optional()])
    submit = SubmitField("Update Profile")