"""Teacher app."""

from jinja2 import StrictUndefined
from flask import (Flask, jsonify, render_template, redirect, request, flash,
                   session, url_for)
from flask_debugtoolbar import DebugToolbarExtension
from model import (User, Student, Subject, Classroom, Exam, ExamResult, Exercise,
                   ExerciseResult, Video, VideoResult)
from model import connect_to_db, db
# import ka_oauth
import rauth
import os
import random
import requests


app = Flask(__name__)

app.secret_key = 'alkjsghfwalejfhbsaldfhuewhif'

app.jinja_env.undefined = StrictUndefined

CONSUMER_KEY = os.environ['KHAN_CONSUMER_KEY']
CONSUMER_SECRET = os.environ['KHAN_CONSUMER_SECRET']

CALLBACK_BASE = '0.0.0.0'
SERVER_URL = 'http://www.khanacademy.org'

DEFAULT_API_RESOURCE = '/api/v1/user'
VERIFIER = None


##### LOGIN, REGISTER, AUTHORIZE, LOGOUT #####

@app.route('/')
def index():
    """Display homepage.

    Homepage contains links to Register and Login pages."""

    return render_template('homepage.html')


@app.route('/login')
def show_login_page():
    """Display login form."""

    return render_template('login.html')


@app.route('/login', methods=['POST'])
def log_user_in():
    """Handle login form.

    Put user_email into session and redirect to homepage."""

    email = request.form.get('email')
    password = request.form.get('password')

    user = db.session.query(User).filter(User.user_email == email).first()

    if user:
        if password == user.password:
            session['logged_in_user'] = user.user_email
            if 'oauth_params' in session:
                oauth_params = session['oauth_params']
                if 'access_token' in oauth_params:
                    flash('Logged in.')
                    return redirect('/classroom')
                else:
                    # no tokens, redo oauth
                    pass
            else:
                return redirect('/classroom')
        else:
            flash('Invalid password.')
            return redirect('/login')
    else:
        flash('This email does not have an account.')
        return redirect('/login')


@app.route('/register')
def show_register_page():
    """Display registration form."""

    return render_template('register.html')


@app.route('/register', methods=['POST'])
def register_user():
    """Handle registration form.

    Redirect user to Khan Academy's authorization page, and set callback URL."""

    # Create an OAuth1Service using rauth.
    app.service = rauth.OAuth1Service(
           name='test',
           consumer_key=CONSUMER_KEY,
           consumer_secret=CONSUMER_SECRET,
           request_token_url=SERVER_URL + '/api/auth2/request_token',
           access_token_url=SERVER_URL + '/api/auth2/access_token',
           authorize_url=SERVER_URL + '/api/auth2/authorize',
           base_url=SERVER_URL + '/api/auth2')

    # 1. Get a request token.
    app.request_token, app.secret_request_token = app.service.get_request_token(
        params={'oauth_callback': 'http://localhost:5000/authorize'})

    # 2. Authorize your request token.
    authorize_url = app.service.get_authorize_url(app.request_token)

    return redirect(authorize_url)


@app.route('/authorize')
def show_authorize_form():
    """Handle Khan Academy authorization form.

    Put access tokens in session, add user to database, and display success message."""

    #  Read verifier param value from url
    verifier = request.args.get('oauth_verifier')

    # 3. Get an access token.
    oauth_session = app.service.get_auth_session(app.request_token, app.secret_request_token,
                                                 params={'oauth_verifier': verifier})

    session['oauth_params'] = {'access_token': oauth_session.access_token,
                               'access_token_secret': oauth_session.access_token_secret}

    # 4. Make an authenticated API call
    params = {}
    # import pdb
    # pdb.set_trace()
    response = oauth_session.get("http://www.khanacademy.org/api/v1/user", params=params)
    user_dict = response.json()

    user_email = user_dict['email']
    password = user_dict['username'][:3] + str(random.randint(100, 999))
    nickname = user_dict['nickname'].split(' ')
    f_name, l_name = nickname
    khan_username = user_dict['username']
    num_students = user_dict['students_count']

    user = User(user_email=user_email,
                password=password,
                f_name=f_name,
                l_name=l_name,
                khan_username=khan_username,
                num_students=num_students)

    db.session.add(user)
    db.session.commit()

    # flash('Account created successfully! Please check your email for user information and temporary password.')
    flash('Account created successfully! Please log in.\nTemporary password: ' + password)
    return redirect('/login')
    # return render_template('authorize.html')


@app.route('/logout')
def log_user_out():
    """Remove user_email from session and redirect to homepage."""

    del session['logged_in_user']

    flash('Logged out')
    return redirect('/')


##### JSON ROUTES #####

@app.route('/student-info.json')
def jsonify_student_info():
    """Return data about students in database as JSON.

    Sample data for create-class.js AJAX request."""

    student_info = open('seed_data/sample_students.json').read()
    return student_info


@app.route('/videoresults.json')
def jsonify_videoresult_info():
    """Return data about video results as JSON.

    Sample data for d3 test."""

    videoresults = open('seed_data/sample_videoresults.json').read()
    return videoresults

    # videoresults = [
    #     {
    #         'video_id': 1,
    #         'student_email': 'studentsally@gmail.com',
    #         'timestamp': '2011-05-04T06:01:47Z',
    #         'points': 16,
    #         'secs_watched': 10,
    #         'last_sec_watched': 90
    #     },
    #     {
    #         'video_id': 1,
    #         'student_email': 'studentsteve@gmail.com',
    #         'timestamp': '2011-05-04T06:01:47Z',
    #         'points': 5,
    #         'secs_watched': 10,
    #         'last_sec_watched': 90
    #     }
    # ]

    # return jsonify(videoresults)


##### CLASSROOMS, EXAMS #####

@app.route('/classroom')
def show_single_class():
    """Display class taught by user.

    Include list of existing exams, link to student roster, visual data, and New Exam button.
    >> MVP: ONLY ONE CLASSROOM PER USER <<"""

    user_email = db.session.query(User.user_email).filter(User.user_email == session['logged_in_user']).first()
    classroom = db.session.query(Classroom).filter(Classroom.user_email == user_email).first()

    if classroom is not None:
        class_id = classroom.class_id
        exams = db.session.query(Exam).filter(Exam.class_id == class_id).all()

        return render_template('classroom.html',
                               classroom=classroom,
                               exams=exams)

    else:
        return redirect('/create-class')


@app.route('/student-roster')
def show_student_roster():
    """Display student roster for class taught by user."""

    user_email = db.session.query(User.user_email).filter(User.user_email == session['logged_in_user']).first()

    classroom = db.session.query(Classroom).filter(Classroom.user_email == user_email).first()
    class_id = classroom.class_id

    students = db.session.query(Student).filter(Student.class_id == class_id).all()

    return render_template('student-roster.html',
                           classroom=classroom,
                           students=students)


@app.route('/create-class')
def show_create_class_form():
    """Display form to create class.

    >> MVP: ONLY ONE CLASSROOM PER USER <<"""

    user_email = session['logged_in_user']
    classroom = db.session.query(Classroom).filter(Classroom.user_email == user_email).first()

    if classroom is not None:
        flash('A class currently exists for this user.')
        return redirect('/classroom')

    else:
        subjects_tup = db.session.query(Subject.name).all()
        subjects = []

        for subject in subjects_tup:
            subject = subject[0]
            subjects.append(subject)

        return render_template('create-class.html',
                               subjects=subjects)


@app.route('/create-class', methods=['POST'])
def create_class():
    """Handle form to create class and redirect to classroom page."""

    user_email = session['logged_in_user']
    # oauth_params = session['oauth_params']

    name = request.form.get('class-name')
    subject = request.form.get('subject')

    subject_code = db.session.query(Subject.subject_code).filter(Subject.name == subject).first()

    new_class = Classroom(name=name,
                          user_email=user_email,
                          subject_code=subject_code)

    db.session.add(new_class)
    db.session.commit()

    return 'Created class.'


@app.route('/add-student', methods=['POST'])
def add_student_to_roster():
    """Handle form to add student to class roster."""

    user_email = session['logged_in_user']
    # class_id = int(db.session.query(Classroom.class_id).filter(Classroom.user_email == user_email).first())
    classroom = Classroom.query.filter(Classroom.user_email == user_email).first()
    class_id = classroom.class_id

    f_name = request.form.get('f-name')
    l_name = request.form.get('l-name')
    student_email = request.form.get('student-email')
    khan_username = request.form.get('khan-username')

    new_student = Student(student_email=student_email,
                          f_name=f_name,
                          l_name=l_name,
                          khan_username=khan_username,
                          class_id=class_id)

    db.session.add(new_student)
    db.session.commit()

    return 'Added student to roster.'


@app.route('/classroom/add-exam')
def show_new_exam_form():
    """Display form to add new exam under specified class."""

    user_email = session['logged_in_user']
    classroom = db.session.query(Classroom).filter(Classroom.user_email == user_email).first()

    if classroom is not None:
        return render_template('add-exam.html',
                               classroom=classroom)

    else:
        return redirect('/create-class')


@app.route('/classroom/add-exam', methods=['POST'])
def add_new_exam():
    """Handle form to add new exam under specified class."""

    user_email = session['logged_in_user']
    classroom = Classroom.query.filter(Classroom.user_email == user_email).first()
    class_id = classroom.class_id

    name = request.form.get('exam-name')
    total_points = request.form.get('total-points')

    exam = Exam(name=name,
                class_id=class_id,
                total_points=total_points)
    db.session.add(exam)
    db.session.commit()

    exam_id = exam.exam_id

    return redirect(url_for('show_exam', exam_id=exam_id))


@app.route('/classroom/add-score', methods=['POST'])
def add_new_score():
    """Handle form to add new score for specified exam."""

    # ONLY HALFWAY DONE ISH

    user_email = session['logged_in_user']
    classroom = Classroom.query.filter(Classroom.user_email == user_email).first()
    class_id = classroom.class_id

    name = request.form.get('exam-name')
    total_points = request.form.get('total-points')

    examresult = ExamResult(name=name,
                            class_id=class_id,
                            total_points=total_points)
    db.session.add(examresult)
    db.session.commit()

    return 'Added score to exam.'


@app.route('/classroom/<exam_id>')
def show_exam(exam_id):
    """Display individual exam data.

    Includes list of exam scores, visual analytic, and Add Score button."""

    # IN PROCESS

    exam = db.session.query(Exam).filter(Exam.exam_id == exam_id).first()
    examresults = db.session.query(ExamResult).filter(ExamResult.exam_id == exam_id).all()

    return render_template('exam-individual.html',
                           class_id=class_id,
                           exam=exam,
                           examresults=examresults)


@app.route('/classroom/<exam_id>/add-score')
def show_new_score_form(exam_id):
    """Display form to add new exam score under specified class."""

    # IN PROCESS

    students = db.session.query(Student).filter(Student.class_id == class_id).all()
    exam = db.session.query(Exam).filter(Exam.exam_id == exam_id).first()

    return render_template('add-score.html',
                           class_id=class_id,
                           students=students,
                           exam=exam)


@app.route('/classroom/<exam_id>/add-score', methods=['POST'])
def add_new_score(class_id, exam_id):
    """Handle form to add new exam score under specified class."""

    # IN PROCESS

    student_name = request.form.get('student-name')
    score = request.form.get('score')

    student_name = student_name.split(" ")
    f_name, l_name = student_name
    student = db.session.query(Student).filter((Student.f_name == f_name) &
                                               (Student.l_name == l_name)).first()
    student_id = student.student_id

    examresult = ExamResult(exam_id=exam_id,
                            student_id=student_id,
                            score=score)
    db.session.add(examresult)
    db.session.commit()

    return redirect(url_for('show_exam', class_id=class_id, exam_id=exam_id))


# @app.route('/classes')
# def show_classes_list():
#     """Display list of classes taught by user.

#     >> POST-MVP <<"""

#     # email = request.form.get('email')
#     if session.get('logged_in_user') and session.get('oauth_params'):
#         user_email = session['logged_in_user']
#         oauth_params = session['oauth_params']

#         user = db.session.query(User).filter(User.user_email == user_email).first()

#         # response = requests.get('https://www.khanacademy.org/api/v1/classes', params=session['oauth_params'])
#         # response = response.json()

#         classrooms = db.session.query(Classroom).join(User)\
#                                                 .filter(User.user_email == user_email).all()

#         return render_template('class-list.html',
#                                user=user,
#                                classrooms=classrooms)
#     else:
#         return render_template('unauthorized-attempt.html')


# @app.route('/classes/add-class')
# def show_new_class_form():
#     """Display form to add new class.

#     >> POST-MVP <<"""

#     subjects_tup = db.session.query(Subject.name).all()
#     subjects = []

#     for subject in subjects_tup:
#         subject = subject[0]
#         subjects.append(subject)

#     return render_template('add-class.html',
#                            subjects=subjects)


# @app.route('/classes/add-class', methods=['POST'])
# def add_new_class():
#     """Handle form to add new class and redirect to classes page.

#     >> POST-MVP <<"""

#     user_email = session['logged_in_user']
#     # oauth_params = session['oauth_params']

#     name = request.form.get('class-name')
#     subject = request.form.get('subject')

#     subject_code = db.session.query(Subject.subject_code).filter(Subject.name == subject).first()

#     new_class = Classroom(name=name,
#                           user_email=user_email,
#                           subject_code=subject_code)

#     db.session.add(new_class)
#     db.session.commit()

#     # class_id = db.session.get(Classroom.class_id).filter(Classroom.name == name).first()

#     # for student in students:
#     #     student_email = student['email']
#     #     nickname = student['nickname']
#     #     f_name, l_name = nickname
#     #     khan_username = student['username']
#     #     new_student = Student(student_email=student_email,
#     #                           f_name=f_name,
#     #                           l_name=l_name,
#     #                           khan_username=khan_username,
#     #                           class_id=class_id)

#     #     db.session.add(new_student)

#     # db.session.commit()

#     return redirect('/classes')


# @app.route('/classes/<class_id>')   # note: returns string of a number
# def show_class(class_id):
#     """Display individual class data.

#     Includes list of existing exams, visual analytic, and New Exam button.

#     >> POST-MVP <<"""

#     classroom = db.session.query(Classroom).filter(Classroom.class_id == class_id).first()
#     exams = db.session.query(Exam).filter(Exam.class_id == class_id).all()

#     return render_template('class-individual.html',
#                            classroom=classroom,
#                            exams=exams)


# @app.route('/classes/<class_id>/add-exam')
# def show_new_exam_form(class_id):
#     """Display form to add new exam under specified class."""

#     return render_template('add-exam.html',
#                            class_id=class_id)


# @app.route('/classes/<class_id>/add-exam', methods=['POST'])
# def add_new_exam(class_id):
#     """Handle form to add new exam under specified class."""

#     name = request.form.get('exam-name')
#     total_points = request.form.get('total-points')

#     exam = Exam(name=name,
#                 class_id=class_id,
#                 total_points=total_points)
#     db.session.add(exam)
#     db.session.commit()

#     return redirect(url_for('show_class', class_id=class_id))


# @app.route('/classes/<class_id>/<exam_id>')
# def show_exam(class_id, exam_id):
#     """Display individual exam data.

#     Includes list of exam scores, visual analytic, and Add Score button."""

#     exam = db.session.query(Exam).filter(Exam.exam_id == exam_id).first()
#     examresults = db.session.query(ExamResult).filter(ExamResult.exam_id == exam_id).all()

#     return render_template('exam-individual.html',
#                            class_id=class_id,
#                            exam=exam,
#                            examresults=examresults)


# @app.route('/classes/<class_id>/<exam_id>/add-score')
# def show_new_score_form(class_id, exam_id):
#     """Display form to add new exam score under specified class."""

#     students = db.session.query(Student).filter(Student.class_id == class_id).all()
#     exam = db.session.query(Exam).filter(Exam.exam_id == exam_id).first()

#     return render_template('add-score.html',
#                            class_id=class_id,
#                            students=students,
#                            exam=exam)


# @app.route('/classes/<class_id>/<exam_id>/add-score', methods=['POST'])
# def add_new_score(class_id, exam_id):
#     """Handle form to add new exam score under specified class."""

#     student_name = request.form.get('student-name')
#     score = request.form.get('score')

#     student_name = student_name.split(" ")
#     f_name, l_name = student_name
#     student = db.session.query(Student).filter((Student.f_name == f_name) &
#                                                (Student.l_name == l_name)).first()
#     student_id = student.student_id

#     examresult = ExamResult(exam_id=exam_id,
#                             student_id=student_id,
#                             score=score)
#     db.session.add(examresult)
#     db.session.commit()

#     return redirect(url_for('show_exam', class_id=class_id, exam_id=exam_id))


#####

if __name__ == "__main__":
    app.debug = True
    app.jinja_env.auto_reload = app.debug

    connect_to_db(app)

    DebugToolbarExtension(app)

    app.run(port=5000, host='0.0.0.0')
