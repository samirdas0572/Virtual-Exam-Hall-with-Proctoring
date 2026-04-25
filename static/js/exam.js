/**
 * Exam Engine - Question loading, navigation, timer, answer saving, submission
 */
let currentQuestion = 0;
let questions = [];
let answers = {};
let examTimer = null;
let timeRemaining = 0;
let attemptId = null;
let proctor = null;

function initExam(data) {
    attemptId = data.attempt_id;
    questions = data.questions;
    timeRemaining = data.duration * 60;
    const maxV = data.max_violations || 5;

    renderQuestionNav();
    showQuestion(0);
    startTimer();

    if (data.proctoring_enabled) {
        proctor = new ProctorEngine(attemptId, maxV);
        proctor.start();
    }
}

function renderQuestionNav() {
    const nav = document.getElementById('questionNav');
    if (!nav) return;
    nav.innerHTML = '';
    questions.forEach((q, i) => {
        const btn = document.createElement('button');
        btn.className = 'q-nav-btn' + (i === 0 ? ' active' : '');
        btn.textContent = i + 1;
        btn.id = 'qnav-' + i;
        btn.onclick = () => showQuestion(i);
        nav.appendChild(btn);
    });
}

function showQuestion(index) {
    currentQuestion = index;
    const q = questions[index];
    document.getElementById('questionNumber').textContent = `Question ${index + 1} of ${questions.length}`;
    document.getElementById('questionMarks').textContent = `${q.marks} mark${q.marks > 1 ? 's' : ''}`;
    document.getElementById('questionText').textContent = q.question_text;

    const optionsDiv = document.getElementById('questionOptions');
    optionsDiv.innerHTML = '';

    if (q.question_type === 'mcq') {
        ['A', 'B', 'C', 'D'].forEach(opt => {
            const val = q['option_' + opt.toLowerCase()];
            if (!val) return;
            const label = document.createElement('label');
            label.className = 'option-label' + (answers[q.id] === opt ? ' selected' : '');
            label.innerHTML = `<input type="radio" name="answer" value="${opt}" ${answers[q.id] === opt ? 'checked' : ''}>
                <span class="option-letter">${opt}</span><span class="option-text">${val}</span>`;
            label.querySelector('input').addEventListener('change', () => {
                answers[q.id] = opt;
                saveAnswer(q.id, opt);
                document.querySelectorAll('.option-label').forEach(l => l.classList.remove('selected'));
                label.classList.add('selected');
                markAnswered(index);
            });
            optionsDiv.appendChild(label);
        });
    } else {
        const ta = document.createElement('textarea');
        ta.className = 'answer-textarea';
        ta.placeholder = 'Type your answer here...';
        ta.value = answers[q.id] || '';
        ta.addEventListener('input', debounce(() => {
            answers[q.id] = ta.value;
            saveAnswer(q.id, ta.value);
            if (ta.value.trim()) markAnswered(index);
        }, 500));
        optionsDiv.appendChild(ta);
    }

    // Update nav buttons
    document.querySelectorAll('.q-nav-btn').forEach(b => b.classList.remove('active'));
    const navBtn = document.getElementById('qnav-' + index);
    if (navBtn) navBtn.classList.add('active');

    // Prev/Next buttons
    document.getElementById('prevBtn').disabled = index === 0;
    document.getElementById('nextBtn').disabled = index === questions.length - 1;
}

function markAnswered(index) {
    const btn = document.getElementById('qnav-' + index);
    if (btn) btn.classList.add('answered');
}

function nextQuestion() {
    if (currentQuestion < questions.length - 1) showQuestion(currentQuestion + 1);
}
function prevQuestion() {
    if (currentQuestion > 0) showQuestion(currentQuestion - 1);
}

function startTimer() {
    updateTimerDisplay();
    examTimer = setInterval(() => {
        timeRemaining--;
        updateTimerDisplay();
        if (timeRemaining <= 0) {
            clearInterval(examTimer);
            showToast('Time is up! Auto-submitting...', 'warning');
            submitExam(true);
        }
    }, 1000);
}

function updateTimerDisplay() {
    const h = Math.floor(timeRemaining / 3600);
    const m = Math.floor((timeRemaining % 3600) / 60);
    const s = timeRemaining % 60;
    const display = (h > 0 ? h + ':' : '') + String(m).padStart(2, '0') + ':' + String(s).padStart(2, '0');
    const el = document.getElementById('examTimer');
    if (el) {
        el.textContent = display;
        el.className = 'timer' + (timeRemaining < 60 ? ' danger' : timeRemaining < 300 ? ' warning' : '');
    }
}

async function saveAnswer(questionId, answer) {
    try {
        await fetch('/api/save-answer', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ attempt_id: attemptId, question_id: questionId, answer: answer })
        });
    } catch (e) {
        console.error('Save failed:', e);
    }
}

async function submitExam(auto = false) {
    if (!auto && !confirm('Are you sure you want to submit? You cannot change your answers after submission.')) return;
    clearInterval(examTimer);
    if (proctor) proctor.stop();

    if (document.fullscreenElement) {
        document.exitFullscreen().catch(() => {});
    }

    try {
        const res = await fetch('/api/submit-exam', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ attempt_id: attemptId, answers: answers })
        });
        const data = await res.json();
        if (data.success) {
            window.location.href = '/student/result/' + attemptId;
        } else {
            showToast(data.message || 'Submission failed', 'error');
        }
    } catch (e) {
        showToast('Network error during submission', 'error');
    }
}

function debounce(fn, ms) {
    let t;
    return (...args) => { clearTimeout(t); t = setTimeout(() => fn(...args), ms); };
}
