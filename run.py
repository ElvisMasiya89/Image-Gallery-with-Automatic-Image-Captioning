from imagegallery import create_app
from imagegallery import db_init

app = create_app()
db_init(app)

if __name__ == '__main__':
    app.run(debug=True)
