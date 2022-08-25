from http.client import HTTPException
import re
from traceback import format_tb
from flask import Flask, request, abort, jsonify
from flask_cors import CORS
from sqlalchemy.sql.expression import func

from models import setup_db, Question, Category

QUESTIONS_PER_PAGE = 10

# utility for paginating questions


def paginate_questions(request, selection):
    page = request.args.get('page', 1, type=int)
    start = (page - 1) * QUESTIONS_PER_PAGE
    end = start + QUESTIONS_PER_PAGE

    questions = [question.format() for question in selection]
    current_questions = questions[start:end]

    return current_questions


def create_app(test_config=None):
    # create and configure the app
    app = Flask(__name__)
    setup_db(app)

    # Set up CORS. Allow '*' for origins

    CORS(app, resources={r"/api/*": {"origins": "*"}})

    # Set up headers

    @app.after_request
    def after_request(response):
        response.headers.add('Access-Control-Allow-Headers',
                             'Content-Type, Authorization')
        response.headers.add('Access-Control-Allow-Methods',
                             'GET, POST, PATCH, DELETE, OPTIONS')
        return response

    # Get categories

    @app.route('/categories', methods=['GET'])
    def get_categories():
        categories = Category.query.all()
        formatted_categories = [category.format() for category in categories]
        return jsonify({
            "success": True,
            "categories": formatted_categories
        })

    # Get questions

    @app.route('/questions', methods=['GET'])
    def get_questions():
        # get all questions and paginate
        selection = Question.query.all()
        total_questions = len(selection)
        current_questions = paginate_questions(request, selection)

        # get all categories and add to dict
        all_categories = Category.query.all()
        categories = {}
        for category in all_categories:
            categories[category.id] = category.type

        # abort 404 if no questions
        if (len(current_questions) == 0):
            abort(404)

        # return data to view
        return jsonify({
            'success': True,
            'questions': current_questions,
            'total_questions': total_questions,
            'categories': categories
        })

    # Delete question

    @app.route('/questions/<int:question_id>', methods=['DELETE'])
    def delete_question(question_id):
        try:
            question = Question.query.filter(
                Question.id == question_id).one_or_none()

            if question is None:
                abort(404)

            question.delete()

            return jsonify(
                {
                    "success": True,
                    "deleted": question_id,
                    "total_questions": len(Question.query.all()),
                }
            )

        except HTTPException:
            abort(422)

    # Add a question

    @app.route('/questions', methods=['POST'])
    def add_question():

        new_question = request.json.get("question")
        new_answer = request.json.get("answer")
        new_category = request.json.get("category")
        new_difficulty = request.json.get("difficulty")
        if not (new_question and new_answer and new_category
           and new_difficulty):
            return abort(400,
                         'Required question object keys missing from request '
                         'body')

        try:
            question = Question(new_question, new_answer,
                                new_category, new_difficulty)
            question.insert()

            return jsonify(
                {
                    "success": True,
                    "question": question.format(),
                    "total_questions": len(Question.query.all()),
                }
            )

        except HTTPException:
            abort(422)

    # Search questions

    @app.route('/questions/search', methods=['POST'])
    def search_question():
        search_term = request.json.get('searchTerm')
        selection = Question.query.filter(
            Question.question.ilike(f'%{search_term}%')).all()

        if (len(selection) == 0):
            abort(404)

        paginated = paginate_questions(request, selection)

        return jsonify({
            'success': True,
            'questions': paginated,
            'total_questions': len(Question.query.all())
        })

    # Get questions by category

    @app.route('/categories/<int:id>/questions', methods=['GET'])
    def get_questions_by_category(id):
        # get the category by id
        category = Category.query.filter_by(id=id).one_or_none()

        # abort 400 for bad request if category isn't found
        if (category is None):
            abort(400)

        # get the matching questions
        selection = Question.query.filter_by(category=str(category.id)).all()

        # paginate the selection
        paginated = paginate_questions(request, selection)

        # return the results
        return jsonify({
            'success': True,
            'questions': paginated,
            'total_questions': len(Question.query.all()),
            'current_category': category.type
        })

    # Play quiz

    @app.route('/quizzes', methods=['POST'])
    def get_quiz_questions():
        """
        Gets question for quiz
        :return: Uniques quiz question or None
        """
        previous_questions = request.json.get('previous_questions')
        quiz_category = request.json.get('quiz_category')
        if not quiz_category:
            return abort(400, 'Required keys missing from request body')
        category_id = int(quiz_category.get('id'))
        questions = Question.query.filter(
            Question.category == category_id,
            ~Question.id.in_(previous_questions)) if category_id else \
            Question.query.filter(~Question.id.in_(previous_questions))
        question = questions.order_by(func.random()).first()
        if not question:
            return jsonify({})
        return jsonify({
            'question': question.format()
        })

    # Error handlers
    # ------------------------------------------

    @app.errorhandler(404)
    def not_found(error):
        return (
            jsonify({"success": False, "error": 404,
                    "message": "resource not found"}),
            404,
        )

    @app.errorhandler(422)
    def unprocessable(error):
        return (
            jsonify({"success": False, "error": 422,
                    "message": "unprocessable"}),
            422,
        )

    @app.errorhandler(400)
    def bad_request(error):
        return jsonify({"success": False,
                        "error": 400,
                        "message": "bad request"}), 400

    @app.errorhandler(405)
    def method_not_allowed(error):
        return jsonify({"success": False, "error": 405,
                        "message": "method not allowed"}),  405

    return app
