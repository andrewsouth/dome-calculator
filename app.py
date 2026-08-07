from flask import Flask, render_template, request

from geometry import spherical_dome

app = Flask(__name__)

DEFAULTS = {"diameter": 105.0, "height": 35.0, "stem_wall": 0.0, "units": "ft"}
UNIT_CHOICES = ["ft", "in", "m", "mm"]


@app.route("/")
def index():
    errors = []
    values = dict(DEFAULTS)
    for key in ("diameter", "height", "stem_wall"):
        raw = request.args.get(key)
        if raw is None:
            continue
        try:
            values[key] = float(raw)
        except ValueError:
            errors.append(f"'{raw}' is not a valid number for {key.replace('_', ' ')}.")

    units = request.args.get("units", DEFAULTS["units"])
    values["units"] = units if units in UNIT_CHOICES else DEFAULTS["units"]

    if values["diameter"] <= 0:
        errors.append("Diameter must be greater than 0.")
    if not errors and not (0 < values["height"] <= values["diameter"]):
        errors.append("Height must be greater than 0 and no more than the diameter.")
    if values["stem_wall"] < 0:
        errors.append("Stem wall height cannot be negative.")

    results = None
    if not errors:
        results = spherical_dome(values["diameter"], values["height"], values["stem_wall"])

    return render_template(
        "index.html",
        values=values,
        unit_choices=UNIT_CHOICES,
        results=results,
        errors=errors,
    )


if __name__ == "__main__":
    app.run(debug=True)
