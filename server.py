from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = '8BYkEfBA6O6donzWlSihBXox7C0sKR6b'

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///parking.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)


class Owner(db.Model):
    __tablename__ = "owners"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(250), nullable=False)
    status = db.Column(db.String(250), nullable=False)

    parking_spaces = relationship("ParkingSpace", back_populates="owner")


class ParkingSpace(db.Model):
    __tablename__ = "parking_spaces"
    id = db.Column(db.Integer, primary_key=True)
    monday = db.Column(db.String(250), nullable=False)
    tuesday = db.Column(db.String(250), nullable=False)
    wednesday = db.Column(db.String(250), nullable=False)
    thursday = db.Column(db.String(250), nullable=False)
    friday = db.Column(db.String(250), nullable=False)

    owner_id = db.Column(db.Integer, db.ForeignKey("owners.id"))
    owner = relationship("Owner", back_populates="parking_spaces")


db.create_all()

days = ["monday", "tuesday", "wednesday", "thursday", "friday"]


@app.route("/")
def home():
    if request.args.get("day"):
        current_day = request.args.get("day")
    else:
        current_day = datetime.today().strftime('%A').lower()
    owners = Owner.query.all()
    spaces = ParkingSpace.query.all()
    return render_template("index.html", spaces=spaces, owners=owners, days=days, current_day=current_day)


@app.route("/admin-panel")
def admin_panel():
    owners = Owner.query.all()
    spaces = ParkingSpace.query.all()
    return render_template("admin.html", spaces=spaces, owners=owners, days=days)


@app.route("/claim", methods=["GET", "POST"])
def claim_space():

    day = request.args.get("day")
    id = request.args.get("id")

    if day and id:
        if request.method == 'POST':
            space = ParkingSpace.query.get(id)
            setattr(space, day, request.form["name"])
            db.session.commit()
            flash(
                f"{request.form['name']} has claimed space {id} on {day.capitalize()}", "success")

    return redirect(url_for("home", day=day))


@app.route("/release")
def release_space():

    day = request.args.get("day")
    id = request.args.get("id")

    if day and id:
        space = ParkingSpace.query.get(id)
        setattr(space, day, "")
        db.session.commit()
        flash(
            f"You have made space {id} avaliable on {day.capitalize()}", "success")

    return redirect(url_for("home", day=day))


@app.route("/add-owner", methods=["GET", "POST"])
def add_owner():

    if request.method == 'POST':
        new_name = request.form["new-owner-name"]
        new_owner = Owner(
            name=new_name,
            status="active",
        )

        db.session.add(new_owner)
        db.session.commit()
        flash(f"{new_name} added as a new owner.", "success")

        if request.form.get('createspace'):
            new_space = ParkingSpace(
                    monday=new_name,
                    tuesday=new_name,
                    wednesday=new_name,
                    thursday=new_name,
                    friday=new_name,
                    owner=new_owner,
                )
            db.session.add(new_space)
            db.session.commit()
            flash(f"Created new space for {new_name}.", "success")
        
    return redirect(url_for("admin_panel"))

@app.route("/edit-owner", methods=["GET", "POST"])
def edit_owner():

    id = request.args.get("id")
    if request.method == 'POST':
        owner = Owner.query.get(id)
        current_name = owner.name
        new_name = request.form["new-owner-name"]
        setattr(owner, "name", new_name)
        db.session.commit()
        flash(f"Successfully updated owner name from {current_name} to {new_name}.", "success")
    return redirect(url_for("admin_panel"))


@app.route("/delete-owner", methods=["GET", "POST"])
def del_owner():
    id = request.args.get("id")
    if id:
        owner = Owner.query.get(id)
        owned_spaces = ParkingSpace.query.filter_by(owner=owner).all()
        for space in owned_spaces:
            db.session.delete(space)
        db.session.delete(owner)
        db.session.commit()
        flash(f"Removed {owner.name} and {len(owned_spaces)} spaces.", "success")
        return redirect(url_for("admin_panel"))

        

    flash(f"Owner does not exist.", "danger")
    return redirect(url_for("admin_panel"))


@app.route("/edit-space", methods=["GET", "POST"])
def edit_space():

    id = request.args.get("id")
    if request.method == 'POST':
        space = ParkingSpace.query.get(id)
        old_name = space.owner.name
        new_owner = Owner.query.filter_by(name=request.form.get("owner_select")).first()
        setattr(space, "owner", new_owner)
        db.session.commit()
        flash(f"Successfully updated owner of space {id} from {old_name} to {new_owner.name}.", "success")
    return redirect(url_for("admin_panel"))



@app.route("/delete-space", methods=["GET", "POST"])
def del_space():
    id = request.args.get("id")
    if id:
        space = ParkingSpace.query.get(id)
        flash(
            f"Removed parking space {id}, which was owned by {space.owner.name}.", "success")
        db.session.delete(space)
        db.session.commit()
        return redirect(url_for("admin_panel"))

    flash(f"Owner does not exist.", "danger")
    return redirect(url_for("admin_panel"))


@app.route("/add-space", methods=["GET", "POST"])
def add_space():

    if request.method == 'POST':

        owner_name = request.form.get("owner_select")
        space_owner = Owner.query.filter_by(name=owner_name).first()

        if space_owner:
            new_space = ParkingSpace(
                monday=owner_name,
                tuesday=owner_name,
                wednesday=owner_name,
                thursday=owner_name,
                friday=owner_name,
                owner=space_owner,
            )
            db.session.add(new_space)
            db.session.commit()


            flash(f"New space added with {owner_name} as owner.", "success")
            return redirect(url_for("admin_panel"))

        else:

            flash(f"Select an owner from the drop down list.", "danger")
            return redirect(url_for("admin_panel"))

    return redirect(url_for("admin_panel"))


@app.route("/reset")
def reset():

    spaces = ParkingSpace.query.all()
    for space in spaces:
        for day in days:
            setattr(space, day, space.owner.name)
    db.session.commit()
    flash(
        f"All spaces reset.", "success")

    return redirect(url_for("home"))


if __name__ == "__main__":
    app.run(debug=True)
