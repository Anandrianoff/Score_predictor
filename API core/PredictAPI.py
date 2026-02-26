import flask
import predictor


model_path = rf"D:\Programming\Score_predictor\Trained models\random_forest_20260226_134721.pkl"
matches_history_path = rf"D:\Programming\Score_predictor\Datasets\RUS_default.csv"
model_artifacts = ""


app = flask.Flask(__name__)

# Создайте конечную точку API
@app.route('/')
def test(): 
   return 'Hello web'

@app.route('/predict', methods=['get'])
def predict():
    print(flask.request.args)
    
    # Считываем все необходимые параметры запроса
    match_params = {
        'home_team': flask.request.args.get('home_team'),
        'away_team': flask.request.args.get('away_team'),
        'date': flask.request.args.get('date'),
        'psch': flask.request.args.get('psch'),
        'pscd': flask.request.args.get('pscd'),
        'psca': flask.request.args.get('psca'),
    }
    print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!! parametrs parsed")
    print(match_params)
    return predictor.predict(model_path, matches_history_path, match_params)

if __name__ == '__main__':
   model_artifacts = predictor.load_model(model_path)
   app.run()