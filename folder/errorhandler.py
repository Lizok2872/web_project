from flask import make_response, jsonify

def errorhandler(app):
    @app.errorhandler(404)
    def not_found(error):
        return make_response(jsonify({'error': 'Not found'}), 404)

    @app.errorhandler(400)
    def bad_request(error):
        return make_response(jsonify({'error': 'Bad Request'}), 400)
