from app.extensions import db
from app.models.user import User
from app.models.employee import Employee
from app.models.prediction import Prediction

__all__ = ['db', 'User', 'Employee', 'Prediction']
