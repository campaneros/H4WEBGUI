
from flask import Flask, send_from_directory
from flask_socketio import SocketIO
import os

socketio = SocketIO()


def create_app(debug=False):
    """Create an application."""
    app = Flask(__name__,static_folder='../../Client/dist')
    app.debug = debug
    # secret key for sessions
    app.config['SECRET_KEY'] = 'pippo!'
    if os.environ.get("H4SETUP") == 'False' :
        app.config['H4SETUP'] = False
        print('####### Deactivating detailed GUI for H4 #######')
    else: # Enter in else also if env var H4SETUP is not set
        app.config['H4SETUP'] = True

    from .rc_router import rc_router
    app.register_blueprint(rc_router,url_prefix="/api")

    socketio.init_app(app,async_mode='threading')

    @app.route('/')
    def index():
        return app.send_static_file("index.html")

    @app.route('/static/<path:path>')
    def dist_static(path):
        return send_from_directory("../../Client/dist/static", path)

    return app
