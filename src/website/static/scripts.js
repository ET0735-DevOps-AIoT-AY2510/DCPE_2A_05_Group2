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
  }

  if (questionCount >= totalQuestions) {
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

