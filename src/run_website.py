# Purpose of this file: 
# Entry point for python main.py to run

from website import create_app, create_database
from flask import Flask

app = create_app()
create_database(app)

if __name__ == '__main__':
    # app.run(debug=True)

    # run the below to make website accessible through the internet
    app.run(debug=True, host='0.0.0.0')