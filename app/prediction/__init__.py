from flask import Blueprint

prediction_bp = Blueprint('prediction', __name__, url_prefix='/prediction')

from app.prediction import routes
