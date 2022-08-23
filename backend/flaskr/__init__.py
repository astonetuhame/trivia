import os
import re
from traceback import format_tb
from flask import Flask, request, abort, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from sqlalchemy.sql.expression import func
import random

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

    """
    @TODO: Set up CORS. Allow '*' for origins. Delete the sample route after completing the TODOs
    """
    CORS(app, resources={r"/api/*": {"origins": "*"}})

    """
    @TODO: Use the after_request decorator to set Access-Control-Allow
    """
    @app.after_request
    def after_request(response):
        response.headers.add('Access-Control-Allow-Headers',
                             'Content-Type, Authorization')
        response.headers.add('Access-Control-Allow-Methods',
                             'GET, POST, PATCH, DELETE, OPTIONS')
        return response

    """
    @TODO:
    Create an endpoint to handle GET requests
    for all available categories.
    """
    @app.route('/categories', methods=['GET'])
    def get_categories():
        categories = Category.query.all()
        formatted_categories = [category.format() for category in categories]
        return jsonify({
            "success": True,
            "categories": formatted_categories
        })

    """
    @TODO:
    Create an endpoint to handle GET requests for questions,
    including pagination (every 10 questions).
    This endpoint should return a list of questions,
    number of total questions, current category, categories.

    TEST: At this point, when you start the application
    you should see questions and categories generated,
    ten questions per page and pagination at the bottom of the screen for three pages.
    Clicking on the page numbers should update the questions.
    """
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

    """
    @TODO:
    Create an endpoint to DELETE question using a question ID.

    TEST: When you click the trash icon next to a question, the question will be removed.
    This removal will persist in the database and when you refresh the page.
    """
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
                    "total_books": len(Question.query.all()),
                }
            )

        except:
            abort(422)

    """
    @TODO:
    Create an endpoint to POST a new question,
    which will require the question and answer text,
    category, and difficulty score.

    TEST: When you submit a question on the "Add" tab,
    the form will clear and the question will appear at the end of the last page
    of the questions list in the "List" tab.
    """
    @app.route('/questions', methods=['POST'])
    def add_question():
        # body = request.get_json()

        new_question = request.json.get("question")
        new_answer = request.json.get("answer")
        new_category = request.json.get("category")
        new_difficulty = request.json.get("difficulty")
        if not (new_question and new_answer and new_category and new_difficulty):
            return abort(400,
                         'Required question object keys missing from request '
                         'body')

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

    """
    @TODO:
    Create a POST endpoint to get questions based on a search term.
    It should return any questions for whom the search term
    is a substring of the question.

    TEST: Search by any phrase. The questions list will update to include
    only question that include that string within their question.
    Try using the word "title" to start.
    """
    @app.route('/questions/search', methods=['POST'])
    def search_question():
        search_term = request.json.get('searchTerm', '')
        questions = [question.format() for question in Question.query.all() if
                     re.search(search_term, question.question, re.IGNORECASE)]
        return jsonify({
            'questions': questions,
            'total_questions': len(questions)
        })

    """
    @TODO:
    Create a GET endpoint to get questions based on category.

    TEST: In the "List" tab / main screen, clicking on one of the
    categories in the left column will cause only questions of that
    category to be shown.
    """

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

    """
    @TODO:
    Create a POST endpoint to get questions to play the quiz.
    This endpoint should take category and previous question parameters
    and return a random questions within the given category,
    if provided, and that is not one of the previous questions.

    TEST: In the "Play" tab, after a user selects "All" or a category,
    one question at a time is displayed, the user is allowed to answer
    and shown whether they were correct or not.
    """

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

    """
    @TODO:
    Create error handlers for all expected errors
    including 404 and 422.
    """

    return app
