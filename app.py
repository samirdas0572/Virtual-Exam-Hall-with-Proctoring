import os
import json
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from models import db, User, Exam, Question, ExamAttempt, Answer, Violation

# ── App Setup ─────────────────────────────────────────
app = Flask(__name__)
app.config['SECRET_KEY'] = 'virtual-exam-hall-secret-key-2026'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///exam_hall.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message_category = 'warning'


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# ── Auth Routes ───────────────────────────────────────
@app.route('/')
def index():
    if current_user.is_authenticated:
        if current_user.role == 'admin':
            return redirect(url_for('admin_dashboard'))
        return redirect(url_for('student_dashboard'))
    return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            flash('Welcome back, ' + user.full_name + '!', 'success')
            return redirect(url_for('index'))
        flash('Invalid username or password.', 'error')
    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        role = request.form.get('role', 'student')

        if User.query.filter_by(username=username).first():
            flash('Username already taken.', 'error')
            return redirect(url_for('register'))
        if User.query.filter_by(email=email).first():
            flash('Email already registered.', 'error')
            return redirect(url_for('register'))

        user = User(full_name=full_name, username=username, email=email, role=role)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        flash('Account created! Please sign in.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'success')
    return redirect(url_for('login'))


# ── Admin Routes ──────────────────────────────────────
@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    if current_user.role != 'admin':
        flash('Access denied.', 'error')
        return redirect(url_for('index'))
    exams = Exam.query.filter_by(created_by=current_user.id).order_by(Exam.created_at.desc()).all()
    stats = {
        'total_exams': len(exams),
        'total_students': User.query.filter_by(role='student').count(),
        'total_attempts': ExamAttempt.query.join(Exam).filter(Exam.created_by == current_user.id).count(),
        'flagged_attempts': ExamAttempt.query.join(Exam).filter(
            Exam.created_by == current_user.id, ExamAttempt.is_flagged == True
        ).count()
    }
    return render_template('admin/dashboard.html', exams=exams, stats=stats)


@app.route('/admin/create-exam', methods=['GET', 'POST'])
@login_required
def create_exam():
    if current_user.role != 'admin':
        flash('Access denied.', 'error')
        return redirect(url_for('index'))
    if request.method == 'POST':
        exam = Exam(
            title=request.form['title'],
            subject=request.form['subject'],
            description=request.form.get('description', ''),
            duration_minutes=int(request.form['duration']),
            total_marks=int(request.form['total_marks']),
            passing_percentage=int(request.form.get('passing_percentage', 40)),
            max_violations=int(request.form.get('max_violations', 5)),
            proctoring_enabled='proctoring_enabled' in request.form,
            created_by=current_user.id
        )
        db.session.add(exam)
        db.session.commit()
        flash('Exam created successfully!', 'success')
        return redirect(url_for('manage_questions', exam_id=exam.id))
    return render_template('admin/create_exam.html', exam=None)


@app.route('/admin/edit-exam/<int:exam_id>', methods=['GET', 'POST'])
@login_required
def edit_exam(exam_id):
    exam = Exam.query.get_or_404(exam_id)
    if exam.created_by != current_user.id:
        flash('Access denied.', 'error')
        return redirect(url_for('admin_dashboard'))
    if request.method == 'POST':
        exam.title = request.form['title']
        exam.subject = request.form['subject']
        exam.description = request.form.get('description', '')
        exam.duration_minutes = int(request.form['duration'])
        exam.total_marks = int(request.form['total_marks'])
        exam.passing_percentage = int(request.form.get('passing_percentage', 40))
        exam.max_violations = int(request.form.get('max_violations', 5))
        exam.proctoring_enabled = 'proctoring_enabled' in request.form
        db.session.commit()
        flash('Exam updated!', 'success')
        return redirect(url_for('admin_dashboard'))
    return render_template('admin/create_exam.html', exam=exam)


@app.route('/admin/delete-exam/<int:exam_id>', methods=['POST'])
@login_required
def delete_exam(exam_id):
    exam = Exam.query.get_or_404(exam_id)
    if exam.created_by != current_user.id:
        flash('Access denied.', 'error')
        return redirect(url_for('admin_dashboard'))
    # Delete related attempts first
    for attempt in exam.attempts:
        db.session.delete(attempt)
    db.session.delete(exam)
    db.session.commit()
    flash('Exam deleted.', 'success')
    return redirect(url_for('admin_dashboard'))


@app.route('/admin/toggle-exam/<int:exam_id>', methods=['POST'])
@login_required
def toggle_exam(exam_id):
    exam = Exam.query.get_or_404(exam_id)
    if exam.created_by != current_user.id:
        flash('Access denied.', 'error')
        return redirect(url_for('admin_dashboard'))
    exam.is_active = not exam.is_active
    db.session.commit()
    flash(f'Exam {"activated" if exam.is_active else "deactivated"}.', 'success')
    return redirect(url_for('admin_dashboard'))


@app.route('/admin/exam/<int:exam_id>/questions')
@login_required
def manage_questions(exam_id):
    exam = Exam.query.get_or_404(exam_id)
    if exam.created_by != current_user.id:
        flash('Access denied.', 'error')
        return redirect(url_for('admin_dashboard'))
    return render_template('admin/manage_questions.html', exam=exam)


@app.route('/admin/exam/<int:exam_id>/add-question', methods=['POST'])
@login_required
def add_question(exam_id):
    exam = Exam.query.get_or_404(exam_id)
    if exam.created_by != current_user.id:
        flash('Access denied.', 'error')
        return redirect(url_for('admin_dashboard'))
    q = Question(
        exam_id=exam.id,
        question_text=request.form['question_text'],
        question_type=request.form['question_type'],
        option_a=request.form.get('option_a', ''),
        option_b=request.form.get('option_b', ''),
        option_c=request.form.get('option_c', ''),
        option_d=request.form.get('option_d', ''),
        correct_answer=request.form['correct_answer'].strip().upper() if request.form['question_type'] == 'mcq' else request.form['correct_answer'].strip(),
        marks=int(request.form.get('marks', 1)),
        order_num=len(exam.questions) + 1
    )
    db.session.add(q)
    db.session.commit()
    flash('Question added!', 'success')
    return redirect(url_for('manage_questions', exam_id=exam.id))


@app.route('/admin/delete-question/<int:question_id>', methods=['POST'])
@login_required
def delete_question(question_id):
    q = Question.query.get_or_404(question_id)
    exam_id = q.exam_id
    if q.exam.created_by != current_user.id:
        flash('Access denied.', 'error')
        return redirect(url_for('admin_dashboard'))
    db.session.delete(q)
    db.session.commit()
    flash('Question deleted.', 'success')
    return redirect(url_for('manage_questions', exam_id=exam_id))


@app.route('/admin/exam/<int:exam_id>/results')
@login_required
def exam_results(exam_id):
    exam = Exam.query.get_or_404(exam_id)
    if exam.created_by != current_user.id:
        flash('Access denied.', 'error')
        return redirect(url_for('admin_dashboard'))
    attempts = ExamAttempt.query.filter_by(exam_id=exam.id).order_by(ExamAttempt.end_time.desc()).all()
    return render_template('admin/results.html', exam=exam, attempts=attempts)


# ── Student Routes ────────────────────────────────────
@app.route('/student/dashboard')
@login_required
def student_dashboard():
    if current_user.role != 'student':
        flash('Access denied.', 'error')
        return redirect(url_for('index'))
    available_exams = Exam.query.filter_by(is_active=True).all()
    my_attempts = ExamAttempt.query.filter_by(student_id=current_user.id, status='completed').all()
    attempted_exam_ids = {a.exam_id for a in my_attempts}
    completed = len(my_attempts)
    avg_score = sum(a.percentage for a in my_attempts) / len(my_attempts) if my_attempts else 0
    return render_template('student/dashboard.html',
                           available_exams=available_exams,
                           attempted_exam_ids=attempted_exam_ids,
                           completed=completed,
                           avg_score=avg_score)


@app.route('/student/exam/<int:exam_id>')
@login_required
def start_exam(exam_id):
    if current_user.role != 'student':
        flash('Access denied.', 'error')
        return redirect(url_for('index'))
    exam = Exam.query.get_or_404(exam_id)
    if not exam.is_active:
        flash('This exam is not active.', 'error')
        return redirect(url_for('student_dashboard'))

    # Check if already attempted
    existing = ExamAttempt.query.filter_by(
        student_id=current_user.id, exam_id=exam.id, status='completed'
    ).first()
    if existing:
        flash('You have already taken this exam.', 'warning')
        return redirect(url_for('student_dashboard'))

    # Check for in-progress attempt
    attempt = ExamAttempt.query.filter_by(
        student_id=current_user.id, exam_id=exam.id, status='in_progress'
    ).first()
    if not attempt:
        attempt = ExamAttempt(
            student_id=current_user.id,
            exam_id=exam.id,
            total_marks=exam.total_marks
        )
        db.session.add(attempt)
        db.session.commit()

    questions = Question.query.filter_by(exam_id=exam.id).order_by(Question.order_num).all()
    questions_json = json.dumps([{
        'id': q.id,
        'question_text': q.question_text,
        'question_type': q.question_type,
        'option_a': q.option_a,
        'option_b': q.option_b,
        'option_c': q.option_c,
        'option_d': q.option_d,
        'marks': q.marks
    } for q in questions])

    return render_template('student/exam.html',
                           exam=exam, attempt=attempt,
                           questions=questions,
                           questions_json=questions_json)


@app.route('/student/results')
@login_required
def student_results():
    if current_user.role != 'student':
        flash('Access denied.', 'error')
        return redirect(url_for('index'))
    attempts = ExamAttempt.query.filter_by(
        student_id=current_user.id
    ).order_by(ExamAttempt.end_time.desc()).all()
    return render_template('student/results.html', attempts=attempts)


@app.route('/student/result/<int:attempt_id>')
@login_required
def student_result_detail(attempt_id):
    attempt = ExamAttempt.query.get_or_404(attempt_id)
    if attempt.student_id != current_user.id and current_user.role != 'admin':
        flash('Access denied.', 'error')
        return redirect(url_for('index'))

    # Attach question objects to answers for template access
    for answer in attempt.answers:
        answer.question = Question.query.get(answer.question_id)

    return render_template('student/result_detail.html', attempt=attempt)


# ── API Routes ────────────────────────────────────────
@app.route('/api/save-answer', methods=['POST'])
@login_required
def api_save_answer():
    data = request.get_json()
    attempt_id = data.get('attempt_id')
    question_id = data.get('question_id')
    student_answer = data.get('answer', '')

    attempt = ExamAttempt.query.get(attempt_id)
    if not attempt or attempt.student_id != current_user.id:
        return jsonify({'success': False, 'message': 'Invalid attempt'}), 403

    answer = Answer.query.filter_by(attempt_id=attempt_id, question_id=question_id).first()
    if answer:
        answer.student_answer = student_answer
    else:
        answer = Answer(attempt_id=attempt_id, question_id=question_id, student_answer=student_answer)
        db.session.add(answer)
    db.session.commit()
    return jsonify({'success': True})


@app.route('/api/log-violation', methods=['POST'])
@login_required
def api_log_violation():
    data = request.get_json()
    attempt_id = data.get('attempt_id')
    attempt = ExamAttempt.query.get(attempt_id)
    if not attempt or attempt.student_id != current_user.id:
        return jsonify({'success': False}), 403

    violation = Violation(
        attempt_id=attempt_id,
        violation_type=data.get('violation_type', 'unknown'),
        details=data.get('details', '')
    )
    db.session.add(violation)
    attempt.violation_count += 1
    if attempt.violation_count >= attempt.exam.max_violations:
        attempt.is_flagged = True
    db.session.commit()
    return jsonify({'success': True, 'count': attempt.violation_count})


@app.route('/api/submit-exam', methods=['POST'])
@login_required
def api_submit_exam():
    data = request.get_json()
    attempt_id = data.get('attempt_id')
    answers_data = data.get('answers', {})

    attempt = ExamAttempt.query.get(attempt_id)
    if not attempt or attempt.student_id != current_user.id:
        return jsonify({'success': False, 'message': 'Invalid attempt'}), 403
    if attempt.status == 'completed':
        return jsonify({'success': False, 'message': 'Already submitted'}), 400

    # Save any remaining answers
    for q_id_str, ans in answers_data.items():
        q_id = int(q_id_str)
        answer = Answer.query.filter_by(attempt_id=attempt_id, question_id=q_id).first()
        if answer:
            answer.student_answer = ans
        else:
            answer = Answer(attempt_id=attempt_id, question_id=q_id, student_answer=ans)
            db.session.add(answer)

    # Grade the exam
    score = 0
    questions = Question.query.filter_by(exam_id=attempt.exam_id).all()
    for q in questions:
        answer = Answer.query.filter_by(attempt_id=attempt_id, question_id=q.id).first()
        if answer:
            if q.question_type == 'mcq':
                is_correct = answer.student_answer and answer.student_answer.strip().upper() == q.correct_answer.strip().upper()
            else:
                is_correct = answer.student_answer and answer.student_answer.strip().lower() == q.correct_answer.strip().lower()
            answer.is_correct = is_correct
            if is_correct:
                score += q.marks

    attempt.score = score
    attempt.total_marks = attempt.exam.total_marks
    attempt.percentage = (score / attempt.total_marks * 100) if attempt.total_marks > 0 else 0
    attempt.status = 'completed'
    attempt.end_time = datetime.utcnow()
    db.session.commit()

    return jsonify({'success': True, 'score': score, 'total': attempt.total_marks})


# ── Init DB & Run ─────────────────────────────────────
with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True, port=5000)
