import sys
from pathlib import Path

# Ensure `score_predictor` and sibling packages resolve when run as a script.
_root = Path(__file__).resolve().parents[1]
_src = _root / "src"
if str(_src) not in sys.path:
    sys.path.insert(0, str(_src))

from score_predictor.bootstrap import ensure_project_import_paths
from score_predictor.config import get_settings

ensure_project_import_paths()

import flask
import predictor

settings = get_settings()
model_path = str(settings.form_model_path)
matches_history_path = str(settings.form_matches_history_csv)
model_artifacts = ""

app = flask.Flask(__name__)


@app.route("/")
def test():
    return "Hello web"


@app.route("/predict", methods=["get"])
def predict():
    print(flask.request.args)

    match_params = {
        "home_team": flask.request.args.get("home_team"),
        "away_team": flask.request.args.get("away_team"),
        "date": flask.request.args.get("date"),
        "psch": flask.request.args.get("psch"),
        "pscd": flask.request.args.get("pscd"),
        "psca": flask.request.args.get("psca"),
    }
    print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!! parametrs parsed")
    print(match_params)
    return predictor.predict(model_path, matches_history_path, match_params)


@app.route("/matches", methods=["get"])
def matches():
    return ""


if __name__ == "__main__":
    model_artifacts = predictor.load_model(model_path)
    app.run()
