from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

db = SQLAlchemy()


class User(UserMixin, db.Model):
    """User model for both admin and student roles."""
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    full_name = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='student')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    exams_created = db.relationship('Exam', backref='creator', lazy=True)
    attempts = db.relationship('ExamAttempt', backref='student', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Exam(db.Model):
    """Exam model containing exam metadata."""
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    subject = db.Column(db.String(100), nullable=False, default='General')
    duration_minutes = db.Column(db.Integer, nullable=False)
    total_marks = db.Column(db.Integer, nullable=False)
    passing_percentage = db.Column(db.Integer, default=40)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    proctoring_enabled = db.Column(db.Boolean, default=True)
    max_violations = db.Column(db.Integer, default=5)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    questions = db.relationship('Question', backref='exam', lazy=True, cascade='all, delete-orphan')
    attempts = db.relationship('ExamAttempt', backref='exam', lazy=True)


class Question(db.Model):
    """Question model for exam questions."""
    id = db.Column(db.Integer, primary_key=True)
    exam_id = db.Column(db.Integer, db.ForeignKey('exam.id'), nullable=False)
    question_text = db.Column(db.Text, nullable=False)
    question_type = db.Column(db.String(20), nullable=False)  # 'mcq' or 'short_answer'
    option_a = db.Column(db.String(500))
    option_b = db.Column(db.String(500))
    option_c = db.Column(db.String(500))
    option_d = db.Column(db.String(500))
    correct_answer = db.Column(db.String(500), nullable=False)
    marks = db.Column(db.Integer, nullable=False, default=1)
    order_num = db.Column(db.Integer, default=0)


class ExamAttempt(db.Model):
    """Tracks each student's exam attempt."""
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    exam_id = db.Column(db.Integer, db.ForeignKey('exam.id'), nullable=False)
    start_time = db.Column(db.DateTime, default=datetime.utcnow)
    end_time = db.Column(db.DateTime)
    score = db.Column(db.Integer, default=0)
    total_marks = db.Column(db.Integer, default=0)
    percentage = db.Column(db.Float, default=0.0)
    is_flagged = db.Column(db.Boolean, default=False)
    violation_count = db.Column(db.Integer, default=0)
    status = db.Column(db.String(20), default='in_progress')

    # Relationships
    answers = db.relationship('Answer', backref='attempt', lazy=True, cascade='all, delete-orphan')
    violations = db.relationship('Violation', backref='attempt', lazy=True, cascade='all, delete-orphan')


class Answer(db.Model):
    """Stores student answers for each question."""
    id = db.Column(db.Integer, primary_key=True)
    attempt_id = db.Column(db.Integer, db.ForeignKey('exam_attempt.id'), nullable=False)
    question_id = db.Column(db.Integer, db.ForeignKey('question.id'), nullable=False)
    student_answer = db.Column(db.String(500))
    is_correct = db.Column(db.Boolean, default=False)


class Violation(db.Model):
    """Logs proctoring violations during exams."""
    id = db.Column(db.Integer, primary_key=True)
    attempt_id = db.Column(db.Integer, db.ForeignKey('exam_attempt.id'), nullable=False)
    violation_type = db.Column(db.String(50), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    details = db.Column(db.Text)
