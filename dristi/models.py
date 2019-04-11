from dristi import db, login_manager, app
from flask_login import UserMixin
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer 

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key = True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    email = db.Column(db.String(20), unique=True, nullable=False)
    image_file = db.Column(db.String(20),  nullable=False, default='default.jpg')
    password = db.Column(db.String(60), nullable=False)
    rating = db.Column(db.String(10), nullable=False)
    posts = db.relationship('Post', backref='rate', lazy=True)

    def get_reset_token(self, expires_sec=1800):
        s = Serializer(app.config['SECRET_KEY'], expires_sec)
        return s.dumps({'user_id': self.id}).decode('utf-8')

    @staticmethod
    def verify_reset_token(token):
        s = Serializer(app.config['SECRET_KEY'])
        try:
            user_id = s.loads(token)['user_id']
        except:
            return None
        return User.query.get(user_id)

    def __repr__(self):
        return f"User('{self.username}', '{self.email}', '{self.image_file}', '{self.rating}')"

class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    Title = db.Column(db.String(100), nullable=False)
    Runtime = db.Column(db.String(15), nullable=False)
    Showtimes = db.Column(db.Text, nullable=False)
    Rating = db.Column(db.String(10), db.ForeignKey('user.rating'), nullable=False)

    def __repr__(self):
        return f"Post('{self.Title}', '{self.Runtime}', '{self.Rating}')"