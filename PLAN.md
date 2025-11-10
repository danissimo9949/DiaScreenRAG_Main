### Plan for integrating TOTP two-factor authentication

1. **Add dependencies**
   - Update `requirements.txt` with `django-two-factor-auth`.
   - Install the package along with its dependencies (`django-otp`, `qrcode`, `django-formtools` come bundled).

2. **Configure settings and middleware**
   - Extend `INSTALLED_APPS` in `DiaScreen/settings.py` with:
     ```
     'django_otp',
     'django_otp.plugins.otp_totp',
     'two_factor',
     ```
   - Insert `django_otp.middleware.OTPMiddleware` into `MIDDLEWARE` after Django’s `AuthenticationMiddleware`.
   - Set auth URLs in `settings.py`:
     ```
     LOGIN_URL = 'two_factor:login'
     LOGIN_REDIRECT_URL = 'home'
     LOGOUT_REDIRECT_URL = 'two_factor:login'
     ```
   - Optionally enable `TWO_FACTOR_PATCH_ADMIN = True` to wrap the admin site.

3. **Wire up URLs**
   - In `DiaScreen/urls.py`, include `two_factor.urls` near the top (before custom auth routes) to expose login, setup and backup-code flows.
   - Keep existing `user_auth` URLs for registration/profile; remove or adapt the old `login_view` if no longer used.

4. **Integrate with existing auth UX**
   - Replace manual login form/template with the packaged flow (it renders multi-step forms).
   - If email-or-username login is required, subclass `two_factor.forms.AuthenticationTokenForm` to normalize input similar to current `LoginForm`, and point `TWO_FACTOR_LOGIN_FORM` to the custom class.
   - Update profile page to show 2FA status and link to setup/removal views (`two_factor:setup`, `two_factor:disable`).

5. **Templates & styling**
   - Add simple template overrides under `templates/two_factor/` as needed for consistent branding (e.g. extend `base.html`).
   - Ensure static assets (e.g. QR code styling) align with theme.

6. **Database & migrations**
   - Run `python manage.py migrate` to apply `two_factor` and `django_otp` migrations.

7. **Testing & docs**
   - Verify login without 2FA, enabling 2FA, logging in with OTP, using backup tokens.
   - Document the 2FA setup flow for users/support, including recovery.

Next steps after confirmation: implement each step, update TODO statuses, and provide testing instructions.


