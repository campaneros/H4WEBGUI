# from flask import Flask, jsonify, send_from_directory
# from flask_socketio import SocketIO
# from src.rc_router import rc_router
#
# app = Flask(__name__, static_folder='../Client/dist')
# socketio = SocketIO(app)
# app.register_blueprint(rc_router,url_prefix="/api")
#
# @app.route('/')
# def index():
#     return app.send_static_file("index.html")
#
# # @app.route('/dist/<path:path>')
# # def static_dist(path):
#     # return send_from_directory("../Client/dist", path)
#
# @app.route('/static/<path:path>')
# def dist_static(path):
#     return send_from_directory("../Client/dist/static", path)
#
#
# if __name__ == '__main__':
#     #app.run()
#     socketio.run(app)

from src import create_app, socketio
import logging

logger = logging.getLogger('webgui_logger')
logger.setLevel(logging.DEBUG)

app = create_app(debug=True)

if __name__ == '__main__':
    socketio.run(app)
