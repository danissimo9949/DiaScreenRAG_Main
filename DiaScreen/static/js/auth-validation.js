document.addEventListener('DOMContentLoaded', () => {
  const EMAIL_REGEX =
    /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/;
  const USERNAME_REGEX =
    /^[\w.@+-]{3,150}$/;

  function removeFieldError(field) {
    if (!field) {
      return;
    }
    field.classList.remove('is-invalid');
    const container =
      field.closest('.mb-3') || field.closest('.form-check') || field.parentElement;
    if (!container) {
      return;
    }
    container
      .querySelectorAll('[data-js-error]')
      .forEach((el) => el.remove());
  }

  function showFieldError(field, message) {
    if (!field) {
      return;
    }
    const container =
      field.closest('.mb-3') || field.closest('.form-check') || field.parentElement;
    if (!container) {
      return;
    }

    removeFieldError(field);

    field.classList.add('is-invalid');

    const errorEl = document.createElement('div');
    errorEl.className = 'invalid-feedback d-block';
    errorEl.dataset.jsError = 'true';
    errorEl.textContent = message;
    container.appendChild(errorEl);
  }

  function validateLoginForm(form) {
    let isValid = true;
    const usernameField = form.querySelector('input[name="username"]');
    const passwordField = form.querySelector('input[name="password"]');

    [usernameField, passwordField].forEach(removeFieldError);

    const usernameValue = usernameField?.value.trim() || '';
    const passwordValue = passwordField?.value || '';

    if (!usernameValue) {
      showFieldError(
        usernameField,
        'Введіть ім’я користувача або адресу електронної пошти.'
      );
      isValid = false;
    } else if (usernameValue.includes('@') && !EMAIL_REGEX.test(usernameValue)) {
      showFieldError(usernameField, 'Введіть коректну адресу електронної пошти.');
      isValid = false;
    }

    if (!passwordValue) {
      showFieldError(passwordField, 'Введіть пароль.');
      isValid = false;
    } else if (passwordValue.length < 8) {
      showFieldError(passwordField, 'Пароль має містити щонайменше 8 символів.');
      isValid = false;
    }

    return isValid;
  }

  function validateRegisterForm(form) {
    let isValid = true;

    const usernameField = form.querySelector('input[name="username"]');
    const emailField = form.querySelector('input[name="email"]');
    const password1Field = form.querySelector('input[name="password1"]');
    const password2Field = form.querySelector('input[name="password2"]');
    const policyField = form.querySelector('input[name="policy_agreement"]');

    [usernameField, emailField, password1Field, password2Field, policyField].forEach(
      removeFieldError
    );

    const usernameValue = usernameField?.value.trim() || '';
    const emailValue = emailField?.value.trim() || '';
    const password1Value = password1Field?.value || '';
    const password2Value = password2Field?.value || '';

    if (!usernameValue) {
      showFieldError(usernameField, 'Введіть ім’я користувача.');
      isValid = false;
    } else if (!USERNAME_REGEX.test(usernameValue)) {
      showFieldError(
        usernameField,
        'Дозволені літери, цифри та символи @/./+/-/_. Мінімум 3 символи.'
      );
      isValid = false;
    }

    if (!emailValue) {
      showFieldError(emailField, 'Введіть адресу електронної пошти.');
      isValid = false;
    } else if (!EMAIL_REGEX.test(emailValue)) {
      showFieldError(emailField, 'Введіть коректну адресу електронної пошти.');
      isValid = false;
    }

    if (!password1Value) {
      showFieldError(password1Field, 'Введіть пароль.');
      isValid = false;
    } else if (password1Value.length < 8) {
      showFieldError(password1Field, 'Пароль має містити щонайменше 8 символів.');
      isValid = false;
    }

    if (!password2Value) {
      showFieldError(password2Field, 'Повторіть пароль.');
      isValid = false;
    } else if (password1Value && password1Value !== password2Value) {
      showFieldError(password2Field, 'Паролі не збігаються.');
      isValid = false;
    }

    if (policyField && !policyField.checked) {
      showFieldError(policyField, 'Потрібно погодитися з політикою конфіденційності.');
      isValid = false;
    }

    return isValid;
  }

  const loginForm = document.getElementById('loginForm');
  if (loginForm) {
    loginForm.addEventListener('submit', (event) => {
      if (!validateLoginForm(loginForm)) {
        event.preventDefault();
      }
    });

    loginForm
      .querySelectorAll('input')
      .forEach((input) =>
        input.addEventListener('input', () => removeFieldError(input))
      );
  }

  const registerForm = document.getElementById('registerForm');
  if (registerForm) {
    registerForm.addEventListener('submit', (event) => {
      if (!validateRegisterForm(registerForm)) {
        event.preventDefault();
      }
    });

    registerForm
      .querySelectorAll('input')
      .forEach((input) =>
        input.addEventListener('input', () => removeFieldError(input))
      );
  }
});

