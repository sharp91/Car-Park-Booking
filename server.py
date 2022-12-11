from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import UserMixin, login_user, LoginManager, login_required, current_user, logout_user
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship
from functools import wraps
from datetime import datetime
import requests
import json

app = Flask(__name__)
app.config['SECRET_KEY'] = '8BYkEfBA6O6donzWlSihBXox7C0sKR6b'

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///parking.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

login_manager = LoginManager()
login_manager.init_app(app)

zapier_webhook = ""

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def admin_only(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if current_user.is_authenticated and current_user.is_admin:
            return func(*args, **kwargs)
        else:
            flash("Admin only.", "warning")
            return redirect(url_for("home"))
    return wrapper

def member_only(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if current_user.is_authenticated:
            return func(*args, **kwargs)
        else:
            flash("You need to login to book.", "warning")
            return redirect(url_for("login"))
    return wrapper


# Configure DB tables
class User(UserMixin, db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(250), nullable=False)
    status = db.Column(db.String(250), nullable=False)
    email = db.Column(db.String(250), unique=True, nullable=False)
    is_admin = db.Column(db.Boolean(), nullable=True)

    parking_spaces = relationship("ParkingSpace", back_populates="user")

class ParkingSpace(db.Model):
    __tablename__ = "parking_spaces"
    id = db.Column(db.Integer, primary_key=True)
    monday = db.Column(db.String(250), nullable=False)
    tuesday = db.Column(db.String(250), nullable=False)
    wednesday = db.Column(db.String(250), nullable=False)
    thursday = db.Column(db.String(250), nullable=False)
    friday = db.Column(db.String(250), nullable=False)

    user_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    user = relationship("User", back_populates="parking_spaces")


# db.create_all()

days = ["monday", "tuesday", "wednesday", "thursday", "friday"]

def send_teams_msg(message):
    data = {
        "message": message
    }
    requests.post(zapier_webhook, data=json.dumps(data), headers={'Content-Type': 'application/json'})

@app.route("/")
@member_only
def home():

    # Set the currently selected day for tabs
    if request.args.get("day"):
        current_day = request.args.get("day")
    elif datetime.today().weekday() < 5:
        current_day = datetime.today().strftime('%A').lower()
    else:
        current_day = days[0]

    # Pull data to populate page
    users = User.query.all()
    spaces = ParkingSpace.query.all()
    num_spaces = len(spaces)

    # Calculate number of free spaces on selected day.
    filter = {current_day:""}
    free_spaces = len(ParkingSpace.query.filter_by(**filter).all())
    if free_spaces > 0:
        flash(f"There's {free_spaces} spaces avaliable on { current_day.capitalize()}", "success")
    else:
        flash(f"There's currently no spaces avaliable on { current_day.capitalize()}", "warning")
    
    # Render page
    return render_template("index.html", spaces=spaces, users=users, days=days, current_day=current_day, num_spaces=num_spaces)

@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == 'POST':
        new_name = request.form["new-user-name"]
        new_email = request.form["new-user-email"]

        existing_user = User.query.filter_by(email=new_email).first()
        if existing_user:
            flash(f"A user with that email already exists.", "danger")
            return redirect(url_for("register"))

        new_user = User(
            name=new_name,
            status="active",
            email=new_email,
        )

        db.session.add(new_user)
        db.session.commit()
        login_user(new_user)
        flash(f"Welcome {new_name}!", "success")
        
    return redirect(url_for("home"))

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == 'POST':
        user_email = request.form["user-email"]
        user = User.query.filter_by(email=user_email).first()
        if user:
            login_user(user)
            flash(f"Welcome back {user.name}!", "success")
            return redirect(url_for("home"))
        else:
            flash(f"User does not exist, please register.", "danger")
            return render_template("register.html")
    
    return render_template("login.html")

@app.route('/logout')
def logout():
    logout_user()
    return render_template("login.html")

@app.route("/admin-panel")
@admin_only
def admin_panel():
    # Pull data to populate page
    users = User.query.all()
    spaces = ParkingSpace.query.all()
    # Render page
    return render_template("admin.html", spaces=spaces, users=users, days=days)


@app.route("/claim", methods=["GET", "POST"])
@member_only
def claim_space():
    # Pull query string params
    day = request.args.get("day")
    id = request.args.get("id")
    name = current_user.name
    # If params exist, set new space owner.
    if day and id and name:
        space = ParkingSpace.query.get(id)
        if space:
            setattr(space, day, name)
            db.session.commit()
            flash(
                f"{name} has claimed space {id} on {day.capitalize()}", "success")
        else:
            flash(f"Space does not exist!", "danger")
    # Render page
    return redirect(url_for("home", day=day))


@app.route("/release")
@member_only
def release_space():
    # Pull query string params
    day = request.args.get("day")
    id = request.args.get("id")

    if day and id:
        space = ParkingSpace.query.get(id)
        if space:
            setattr(space, day, "")
            db.session.commit()
            flash(
                f"You have made space {id} avaliable on {day.capitalize()}", "success")
            send_teams_msg(f"{current_user.name} just made their parking space {id} avaliable on {day.capitalize()}")
        else:
            flash(f"Space does not exist!", "danger")

    return redirect(url_for("home", day=day))

@app.route('/manage', methods=["GET", "POST"])
@member_only
def manage_space():

    id = request.args.get("id")

    if request.method == 'POST':
        
        space = ParkingSpace.query.get(id)
        days_avaliable = []
        for day in days:
            occupier = getattr(space, day)
            try:
                if request.form[day]:
                    if occupier == "":
                        setattr(space, day, space.user.name)
                    elif occupier != space.user.name: 
                        flash(f"You removed {occupier} from your space on {day.capitalize()}", "warning")
                        setattr(space, day, space.user.name)
            except KeyError:
                days_avaliable.append(day.capitalize())
                if occupier == space.user.name: 
                    setattr(space, day, "")

        db.session.commit()
        flash(f"Your space avaliability has been saved.", "success")
        if days_avaliable:
            print(f"{current_user.name} just made their parking space {id} avaliable on {', '.join(days_avaliable)}")
            send_teams_msg(f"{current_user.name} just made their parking space {id} avaliable on {', '.join(days_avaliable)}")
        return redirect(url_for("home"))

    return render_template("manage_space.html", days=days)

@app.route("/add-user", methods=["GET", "POST"])
@admin_only
def add_user():

    if request.method == 'POST':
        new_name = request.form["new-user-name"]
        new_email = request.form["new-user-email"]
        new_user = User(
            name=new_name,
            status="active",
            email=new_email,
        )

        db.session.add(new_user)
        db.session.commit()
        flash(f"{new_name} added as a new user.", "success")

        if request.form.get('createspace'):
            new_space = ParkingSpace(
                    monday=new_name,
                    tuesday=new_name,
                    wednesday=new_name,
                    thursday=new_name,
                    friday=new_name,
                    user=new_user,
                )
            db.session.add(new_space)
            db.session.commit()
            flash(f"Created new space for {new_name}.", "success")
        
    return redirect(url_for("admin_panel"))

@app.route("/edit-user", methods=["GET", "POST"])
@admin_only
def edit_user():

    id = request.args.get("id")
    if request.method == 'POST':
        user = User.query.get(id)
        current_name = user.name
        new_name = request.form["new-user-name"]
        setattr(user, "name", new_name)
        db.session.commit()
        flash(f"Successfully updated user name from {current_name} to {new_name}.", "success")
    return redirect(url_for("admin_panel"))


@app.route("/delete-user", methods=["GET", "POST"])
@admin_only
def del_user():
    id = request.args.get("id")
    if id:
        user = User.query.get(id)
        owned_spaces = ParkingSpace.query.filter_by(user=user).all()
        for space in owned_spaces:
            db.session.delete(space)
        db.session.delete(user)
        db.session.commit()
        flash(f"Removed {user.name} and {len(owned_spaces)} spaces.", "success")
        return redirect(url_for("admin_panel"))

    flash(f"User does not exist.", "danger")
    return redirect(url_for("admin_panel"))


@app.route("/edit-space", methods=["GET", "POST"])
@admin_only
def edit_space():

    id = request.args.get("id")
    if request.method == 'POST':
        space = ParkingSpace.query.get(id)
        old_name = space.user.name
        new_user = User.query.filter_by(name=request.form.get("user_select")).first()
        setattr(space, "user", new_user)
        db.session.commit()
        flash(f"Successfully updated user of space {id} from {old_name} to {new_user.name}.", "success")
    return redirect(url_for("admin_panel"))



@app.route("/delete-space", methods=["GET", "POST"])
@admin_only
def del_space():
    id = request.args.get("id")
    if id:
        space = ParkingSpace.query.get(id)
        flash(
            f"Removed parking space {id}, which was owned by {space.user.name}.", "success")
        db.session.delete(space)
        db.session.commit()
        return redirect(url_for("admin_panel"))

    flash(f"User does not exist.", "danger")
    return redirect(url_for("admin_panel"))


@app.route("/add-space", methods=["GET", "POST"])
@admin_only
def add_space():

    if request.method == 'POST':

        user_name = request.form.get("user_select")
        space_user = User.query.filter_by(name=user_name).first()

        if space_user:
            new_space = ParkingSpace(
                monday=user_name,
                tuesday=user_name,
                wednesday=user_name,
                thursday=user_name,
                friday=user_name,
                user=space_user,
            )
            db.session.add(new_space)
            db.session.commit()


            flash(f"New space added with {user_name} as user.", "success")
            return redirect(url_for("admin_panel"))

        else:

            flash(f"Select an user from the drop down list.", "danger")
            return redirect(url_for("admin_panel"))

    return redirect(url_for("admin_panel"))


@app.route("/reset")
@admin_only
def reset():

    spaces = ParkingSpace.query.all()
    for space in spaces:
        for day in days:
            setattr(space, day, space.user.name)
    db.session.commit()
    flash(
        f"All spaces reset.", "success")

    return redirect(url_for("home"))


if __name__ == "__main__":
    app.run(debug=True)
