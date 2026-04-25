/**
 * Proctoring Engine - Webcam, fullscreen, tab detection, violation logging
 */
class ProctorEngine {
    constructor(attemptId, maxViolations = 5) {
        this.attemptId = attemptId;
        this.maxViolations = maxViolations;
        this.violationCount = 0;
        this.webcamStream = null;
        this.isFullscreen = false;
        this.isActive = false;
    }

    async start() {
        this.isActive = true;
        await this.startWebcam();
        this.enforceFullscreen();
        this.detectTabSwitch();
        this.preventCopyPaste();
        this.preventRightClick();
        this.updateStatus('Proctoring Active', 'active');
    }

    stop() {
        this.isActive = false;
        if (this.webcamStream) {
            this.webcamStream.getTracks().forEach(t => t.stop());
        }
        document.removeEventListener('visibilitychange', this._visHandler);
        window.removeEventListener('blur', this._blurHandler);
        document.removeEventListener('fullscreenchange', this._fsHandler);
    }

    async startWebcam() {
        const video = document.getElementById('webcamPreview');
        if (!video) return;
        try {
            this.webcamStream = await navigator.mediaDevices.getUserMedia({
                video: { width: 320, height: 240 }, audio: false
            });
            video.srcObject = this.webcamStream;
            video.play();
            document.getElementById('webcamStatus').textContent = 'Camera Active';
            document.getElementById('webcamStatus').className = 'status-badge status-active';
        } catch (e) {
            this.logViolation('webcam_denied', 'Webcam access was denied');
            document.getElementById('webcamStatus').textContent = 'Camera Denied';
            document.getElementById('webcamStatus').className = 'status-badge status-danger';
        }
    }

    enforceFullscreen() {
        const el = document.documentElement;
        if (el.requestFullscreen) el.requestFullscreen();
        else if (el.webkitRequestFullscreen) el.webkitRequestFullscreen();
        else if (el.msRequestFullscreen) el.msRequestFullscreen();

        this._fsHandler = () => {
            if (!document.fullscreenElement && this.isActive) {
                this.logViolation('fullscreen_exit', 'Exited fullscreen mode');
                setTimeout(() => {
                    if (this.isActive && !document.fullscreenElement) {
                        document.documentElement.requestFullscreen().catch(() => {});
                    }
                }, 1000);
            }
        };
        document.addEventListener('fullscreenchange', this._fsHandler);
    }

    detectTabSwitch() {
        this._visHandler = () => {
            if (document.hidden && this.isActive) {
                this.logViolation('tab_switch', 'Switched to another tab');
            }
        };
        this._blurHandler = () => {
            if (this.isActive) {
                this.logViolation('window_blur', 'Window lost focus');
            }
        };
        document.addEventListener('visibilitychange', this._visHandler);
        window.addEventListener('blur', this._blurHandler);
    }

    preventCopyPaste() {
        document.addEventListener('copy', e => { if (this.isActive) { e.preventDefault(); this.logViolation('copy_attempt', 'Attempted to copy'); }});
        document.addEventListener('paste', e => { if (this.isActive) { e.preventDefault(); this.logViolation('paste_attempt', 'Attempted to paste'); }});
        document.addEventListener('cut', e => { if (this.isActive) { e.preventDefault(); this.logViolation('cut_attempt', 'Attempted to cut'); }});
    }

    preventRightClick() {
        document.addEventListener('contextmenu', e => {
            if (this.isActive) { e.preventDefault(); this.logViolation('right_click', 'Right-click attempted'); }
        });
    }

    async logViolation(type, details) {
        this.violationCount++;
        this.updateViolationUI();

        try {
            await fetch('/api/log-violation', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    attempt_id: this.attemptId,
                    violation_type: type,
                    details: details
                })
            });
        } catch (e) {
            console.error('Failed to log violation:', e);
        }

        if (this.violationCount >= this.maxViolations) {
            this.updateStatus('Max Violations Reached!', 'danger');
            showToast('Maximum violations reached! Your exam will be auto-submitted.', 'error');
            setTimeout(() => {
                if (typeof submitExam === 'function') submitExam(true);
            }, 2000);
        }
    }

    updateViolationUI() {
        const counter = document.getElementById('violationCount');
        if (counter) counter.textContent = this.violationCount;
        const bar = document.getElementById('violationBar');
        if (bar) {
            const pct = (this.violationCount / this.maxViolations) * 100;
            bar.style.width = pct + '%';
            bar.className = 'violation-bar-fill' + (pct > 60 ? ' danger' : pct > 30 ? ' warning' : '');
        }
    }

    updateStatus(text, type) {
        const el = document.getElementById('proctorStatus');
        if (el) {
            el.textContent = text;
            el.className = 'status-badge status-' + type;
        }
    }
}
