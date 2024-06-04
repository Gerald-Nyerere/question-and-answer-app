from flask import Flask, render_template, request, g, session, redirect, url_for
from database import get_db, connect_db
from werkzeug.security import generate_password_hash, check_password_hash
import os


app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24)



@app.teardown_appcontext
def close_db(error):
    if hasattr(g, 'sqlite_db'):
        g.sqlite_db.close()

def get_current_user():
    user_result = None

    if 'user' in session:
        user = session['user']
    
        db = get_db()
        user_cur = db.execute('select id, name, password, expert, admin from users where name = ? ', [user])
        user_result = user_cur.fetchone()       

    return user_result

@app.route("/")
def index():
    user = get_current_user()
    db = get_db()

    question_cur = db.execute('SELECT question.id as question_id, question.question_text, askers.name AS asker_name, experts.name AS expert_name FROM question JOIN users AS askers ON askers.id = question.asked_by_id JOIN users AS experts ON experts.id = question.expert_id WHERE question.answer_text IS NOT NULL')
    question_all = question_cur.fetchall()


    return render_template("home.html", user = user, questions=question_all)

@app.route("/register", methods=['POST', 'GET'])
def register():
    user = get_current_user()


    if request.method == 'POST':
        db = get_db()
        existing_user_cur = db.execute('select id from users where name =?', [request.form['name']])
        existing_user = existing_user_cur.fetchone()

        if existing_user:
            return render_template('register.html', user=user, error='User already exists!')
        hashed_password = generate_password_hash(request.form['password'], method='pbkdf2:sha256')
        db.execute('insert into users(name, password, expert, admin) values (?, ?, ?, ?)', [request.form['name'], hashed_password, '0', '0'])
        db.commit()

        session['user'] = request.form['name']

        return redirect(url_for('index'))
    
    return render_template("register.html", user=user)

@app.route("/login", methods=['POST', 'GET'])
def login():
    user = get_current_user()
    error = None
    
    if request.method == 'POST':    
        db = get_db()
       
        name = request.form['name']
        password =  request.form['password']
        
        user_cur = db.execute('select id, name, password from users where name = ? ', [name])
        user_result = user_cur.fetchone()
        
    
        if user_result:
    
            if check_password_hash(user_result['password'], password):
                session['user'] = user_result['name']
                return redirect(url_for('index'))
            else:        
                error = ' the password is incorrect'
        else:
           error = 'username is incorrect!'
    
    return render_template("login.html", user=user, error=error)

@app.route("/question/<question_id>")
def question(question_id):
    user = get_current_user()
    db = get_db()

    question_cur = db.execute('SELECT question.question_text, question.answer_text, askers.name AS asker_name, experts.name AS expert_name FROM question JOIN users AS askers ON askers.id = question.asked_by_id JOIN users AS experts ON experts.id = question.expert_id WHERE question.id = ?', [question_id])
    question = question_cur.fetchone()


    return render_template("question.html", user=user, question=question)

@app.route("/answer/<question_id>", methods=['POST', 'GET'])
def answer(question_id):
    user = get_current_user()

    if not user:
        return redirect(url_for('login'))
   
    if user['expert'] == 0:
        return redirect(url_for('index'))
    
    db = get_db()    
    if request.method == 'POST':
        db.execute('update question set answer_text = ? where id = ?', [request.form['answer'], question_id])
        db.commit()
        return redirect(url_for('unanswered'))

    question_cur = db.execute('select id, question_text from question where id = ?', [question_id])
    question = question_cur.fetchone() 

    return render_template("answer.html", user=user, question=question)

@app.route("/ask", methods=['POST', 'GET'])
def ask():
    user = get_current_user()

    if not user:
        return redirect(url_for('login'))


    db = get_db()
    if request.method == 'POST':
        db.execute("insert into question (question_text, asked_by_id, expert_id) values (?, ?, ?)", [request.form['question'], user['id'], request.form['expert']])
        db.commit()
        return redirect(url_for('index'))
    

    expert_cur = db.execute('select id, name from users where expert = 1' )
    expert_results = expert_cur.fetchall()


    return render_template("ask.html", experts=expert_results, user=user)

@app.route("/unanswered")
def unanswered():
    user = get_current_user()

    if not user:
        return redirect(url_for('login'))
    
    if user['expert'] == 0:
        return redirect(url_for('index'))
    
    db = get_db()
    question_cur = db.execute('select question.id, question.question_text, users.name from question join users on users.id = question.asked_by_id where question.answer_text is null and question.expert_id = ?', [user['id']])
    questions =question_cur.fetchall()

    return render_template('unanswered.html', user=user, questions=questions)

@app.route("/users")
def users():
    user = get_current_user()

    if not user:
        return redirect(url_for('login'))

    if user['admin'] == 0:
        return redirect(url_for('index'))
    

    db = get_db()
    users_cur = db.execute('select id , name, expert, admin from users')
    users_results = users_cur.fetchall()


    return render_template("users.html", user=user, users=users_results)

@app.route("/promote/<user_id>")
def promote(user_id):
    user = get_current_user()

    if not user:
        return redirect(url_for('login'))
   
    if user['admin'] == 0:
        return redirect(url_for('index'))
    

    db = get_db()
    db.execute('update users set expert = 1 where id = ?', [user_id])
    db.commit()
    return redirect(url_for('index'))



@app.route("/logout")
def logout():
    session.pop('user', None)
    return redirect(url_for('index'))


if __name__ == '__main__':
    app.run(debug=True)
