console.log("Hello World")

function incrementQty(button) {
  const input = button.parentNode.querySelector('input');
  let value = parseInt(input.value, 10);
  value = isNaN(value) ? 1 : value + 1;
  input.value = value;
}

function decrementQty(button) {
  const input = button.parentNode.querySelector('input');
  let value = parseInt(input.value, 10);
  value = isNaN(value) ? 1 : Math.max(1, value - 1);
  input.value = value;
}

function updateQuantity(itemId, action) {
  // Example stub: send a POST request to /cart/update
  console.log("Update quantity", itemId, action);
  // You'll implement actual update logic in your Flask backend
}

function removeItem(itemId) {
  // Example stub: send DELETE request or form submission
  console.log("Remove item", itemId);
  // You can also use fetch or a form to send to /cart/remove/<id>
}

function validateForm() {
  const name = document.getElementById('name').value.trim();
  const password = document.getElementById('password').value;
  const confirmPassword = document.getElementById('confirm_password').value;
  const errorMessage = document.getElementById('errorMessage');

  // Reset error
  errorMessage.style.display = 'none';
  errorMessage.innerText = '';

  // Validate name length
  if (name.length < 3) {
    errorMessage.innerText = 'Name must be at least 3 characters long.';
    errorMessage.style.display = 'block';
    return false;
  }

  // Validate password match
  if (password !== confirmPassword) {
    errorMessage.innerText = 'Passwords do not match.';
    errorMessage.style.display = 'block';
    return false;
  }

  return true; // Form is valid
}

// For the Checkout.html

const paynowBtn = document.getElementById('paynowBtn');
if (paynowBtn) {
  paynowBtn.addEventListener('click', function () {
    document.getElementById('qrCodeSection').classList.add('active-section');
    document.getElementById('creditCardSection').classList.remove('active-section');
  });
}

const creditCardBtn = document.getElementById('creditCardBtn');
if (creditCardBtn) {
  creditCardBtn.addEventListener('click', function () {
    document.getElementById('creditCardSection').classList.add('active-section');
    document.getElementById('qrCodeSection').classList.remove('active-section');
  });
}

const flipCard = document.getElementById("flipCard");
if (flipCard) {
  flipCard.addEventListener("click", () => {
    flipCard.classList.toggle("flipped");
  });
}

// Code for the math game 
let score = 0;
let currentAnswer = 0;
let questionCount = 0;
const totalQuestions = 16; // 10 easy + 5 medium + 1 hard

function startGame() {
  score = 0;
  questionCount = 0;
  document.getElementById('start-btn').style.display = 'none';
  updateErrors();
  startTimer();
  generateQuestion();
  updateProgress();
}

function generateQuestion() {
  questionCount++;

  let num1, num2, operator;
  if (questionCount <= 10) {
    // Easy: 1-digit numbers, + - *
    num1 = Math.floor(Math.random() * 9) + 1;
    num2 = Math.floor(Math.random() * 9) + 1;
    const ops = ['+', '-', '*'];
    operator = ops[Math.floor(Math.random() * ops.length)];

    // Ensure that subtraction is always positive 
    if (operator === '-' && num1 < num2) {
      [num1, num2] = [num2, num1] // Swap both values 
    }
  } else if (questionCount <= 15) {
    // Medium: 2-digit x 1-digit
    num1 = Math.floor(Math.random() * 90) + 10;
    num2 = Math.floor(Math.random() * 9) + 1;
    operator = '*';
  } else {
    // Hard: 3-digit x 1-digit
    num1 = Math.floor(Math.random() * 900) + 100;
    num2 = Math.floor(Math.random() * 9) + 1;
    operator = '*';
  }

  currentAnswer = eval(`${num1}${operator}${num2}`);
  document.getElementById('question').textContent = `${num1} ${operator} ${num2} = ?`;
  document.getElementById('answer').value = '';
}

// Logic for the timer function
let timeLeft = 120; // 2 minutes in seconds
let timerInterval;
let errors = 0;
const maxErrors = 3;

// Store reference to timer display for reuse 
let timerDisplay;

function startTimer() {
  timerDisplay = document.getElementById('timer');
  clearInterval(timerInterval);
  timerDisplay.classList.remove('flash-warning');
  timeLeft = 120; // For the time left
  timerDisplay.textContent = `⏱ 2:00 `
  timerDisplay.style.color = '';
  timerInterval = setInterval(() => {
    timeLeft--;
    if (timeLeft <= 0) {
      clearInterval(timerInterval)
      timerDisplay.textContent = `⏱ 2:00 - Game Over`;
      timerDisplay.classList.remove('flash-warning');
      timerDisplay.style.color = 'red';
      endGame();
      return;
    }
    const minutes = Math.floor(timeLeft / 60);
    const seconds = timeLeft % 60;
    timerDisplay.textContent = `⏱ ${minutes}:${seconds.toString().padStart(2,'0')}`;
    if (timeLeft <= 30) { // To add flash warning at the last 30 seconds of the quiz
      timerDisplay.classList.add('flash-warning');
      timerDisplay.style.color = 'red';
    } else {
      timerDisplay.classList.remove('flash-warning');
      timerDisplay.style.color = '';
    }
    if (timeLeft <= 0) {
        endGame();
    }
  }, 1000);
}

function updateErrors() {
  document.getElementById('errors').textContent = `❌ Errors: ${errors} / ${maxErrors}`;
}

function appendNumber(num) {
  document.getElementById('answer').value += num;
}

function clearAnswer() {
  document.getElementById('answer').value = '';
}

function submitAnswer() {
  const userAnswer = parseInt(document.getElementById('answer').value);
  if (!isNaN(userAnswer) && userAnswer === currentAnswer) {
    score++;
    updateProgress();
  } else {
    errors++;
    updateErrors();
    if (errors >= maxErrors) {
      endGame();
      errors = 0
      return;
    }
  }

  if (questionCount >= totalQuestions) {
    errors = 0
    endGame();
  } else {
    generateQuestion();
  }
}

function updateProgress() {
  const progressPercent = (score / totalQuestions) * 100;
  const progressBar = document.getElementById('progress-bar');
  progressBar.style.width = `${progressPercent}%`;
  progressBar.textContent = `${score} / ${totalQuestions}`;
}

function endGame() {
  clearInterval(timerInterval);
  const gameContainer = document.querySelector('.game-container');

  won = (errors < maxErrors && timeLeft > 0)

  if (won) {
    gameContainer.innerHTML = `
      <h2 class="mb-4 text-success">🎉 Congratulations! 🎉</h2>
      <p class="mb-4">You successfully completed the challenge with a score of <strong>${score}/${totalQuestions}</strong>!</p>
      <a href="/math-game/collect-prize" class="btn btn-lg btn-warning">🎁 Collect Your Prize</a>
    `;
  } else {
    gameContainer.innerHTML = `
    <h2 class="mb-4 text-danger">Thank you for trying!</h2>
    <p class="mb-4">Your score: <strong>${score}/${totalQuestions}</strong></p>
    <a href="/math-game">
      <button class="btn btn-primary btn-lg" onclick="startGame()">Play Again</button>
    </a>
    `;
  }
  document.getElementById('question').textContent = `🎉 Game Over! Score: ${score} / ${totalQuestions}`;
  document.getElementById('start-btn').style.display = 'block';
  document.getElementById('start-btn').textContent = 'Play Again';
}

// ✅ Enable keyboard input
document.addEventListener('keydown', (e) => {
  if (!isNaN(e.key) && e.key !== ' ') {
    appendNumber(e.key);
  }
  if (e.key === 'Backspace') {
    clearAnswer();
  }
  if (e.key === 'Enter') {
    submitAnswer();
  }
});

// Collect Prize

// Scratch Card Logic
const canvas = document.getElementById('scratch-card');
const ctx = canvas.getContext('2d');
const container = document.querySelector('.scratch-card-container');

function resizeCanvas() {
  canvas.width = container.offsetWidth;
  canvas.height = container.offsetHeight;
  ctx.fillStyle = "#aaa";
  ctx.fillRect(0, 0, canvas.width, canvas.height);
}
resizeCanvas();
window.addEventListener('resize', resizeCanvas);

let isDrawing = false;

function scratch(e) {
  if (!isDrawing) return;
  const rect = canvas.getBoundingClientRect();
  const x = (e.clientX || e.touches[0].clientX) - rect.left;
  const y = (e.clientY || e.touches[0].clientY) - rect.top;

  ctx.globalCompositeOperation = 'destination-out';
  ctx.beginPath();
  ctx.arc(x, y, 20, 0, 2 * Math.PI);
  ctx.fill();
}

canvas.addEventListener('mousedown', () => isDrawing = true);
canvas.addEventListener('mouseup', () => isDrawing = false);
canvas.addEventListener('mousemove', scratch);

canvas.addEventListener('touchstart', () => isDrawing = true);
canvas.addEventListener('touchend', () => isDrawing = false);
canvas.addEventListener('touchmove', scratch);

// 🎊 Confetti Animation with fade-out
const confettiCanvas = document.getElementById('confetti-canvas');
const confettiCtx = confettiCanvas.getContext('2d');
confettiCanvas.width = window.innerWidth;
confettiCanvas.height = window.innerHeight;

const confetti = Array.from({length: 150}, () => ({
  x: Math.random() * confettiCanvas.width,
  y: Math.random() * confettiCanvas.height,
  r: Math.random() * 6 + 2,
  d: Math.random() * 0.5 + 0.5,
  color: `hsl(${Math.random()*360}, 70%, 60%)`,
  opacity: 1
}));

let fadeOut = false;
let confettiAnimation;

function drawConfetti() {
  confettiCtx.clearRect(0, 0, confettiCanvas.width, confettiCanvas.height);
  confetti.forEach(c => {
    confettiCtx.beginPath();
    confettiCtx.arc(c.x, c.y, c.r, 0, 2 * Math.PI);
    confettiCtx.fillStyle = c.color.replace('hsl', 'hsla').replace(')', `,${c.opacity})`);
    confettiCtx.fill();
    c.y += c.d;
    if (c.y > confettiCanvas.height) { c.y = 0; c.x = Math.random() * confettiCanvas.width; }
    if (fadeOut && c.opacity > 0) c.opacity -= 0.02;
  });

  if (fadeOut && confetti.every(c => c.opacity <= 0)) {
    cancelAnimationFrame(confettiAnimation);
    confettiCtx.clearRect(0, 0, confettiCanvas.width, confettiCanvas.height);
    return;
  }
  confettiAnimation = requestAnimationFrame(drawConfetti);
}

drawConfetti();
setTimeout(() => fadeOut = true, 3000);
