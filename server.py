from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship
import os
import json
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


@app.route("/claim", methods=["GET", "POST"])
def claim_space():

    day = request.args.get("day")
    id = request.args.get("id")

    if day and id:
        if request.method == 'POST':
            space = ParkingSpace.query.get(id)
            setattr(space, day, request.form["name"])
            db.session.commit()
            flash(f"{request.form['name']} has claimed space {id} on {day.capitalize()}", "success")

    return redirect(url_for("home"))


@app.route("/release")
def release_space():

    day = request.args.get("day")
    id = request.args.get("id")
    
    if day and id:
        space = ParkingSpace.query.get(id)
        setattr(space, day, "")
        db.session.commit()
        flash(
            f"You have made space {id} on {day.capitalize()} avaliable", "success")

    return redirect(url_for("home", day=day))

@app.route("/addowner", methods=["GET", "POST"])
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
    return redirect(url_for("home"))

@app.route("/addspace", methods=["GET", "POST"])
def add_space():

    if request.method == 'POST':
        owner_name = request.form.get("owner_select")
        space_owner = Owner.query.filter_by(name=owner_name).first()
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
    return redirect(url_for("home"))


@app.route("/reset")
def reset():

    spaces = ParkingSpace.query.all()
    for space in spaces:
        for day in days:
            setattr(space, day, space.owner.name)
    db.session.commit()
    flash(
        f"All spaces reset", "success")

    return redirect(url_for("home"))


if __name__ == "__main__":
    app.run(debug=True)
