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
