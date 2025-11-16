# Two-Factor Authentication & Fallback Options

## Current Implementation

The maa_express application uses a hybrid authentication approach:

### Primary Authentication
- **Email/Password**: Standard email and password combination using bcrypt hashing (werkzeug.security)
- **Phone-Based Login**: Optional phone number login with E.164 normalization for international support

### Phone Verification (Registration)
- Client-side Firebase phone authentication via SMS OTP
- User receives SMS code from Firebase and enters it in the registration form
- Firebase returns an ID token to the client
- Client submits email, password, phone, and Firebase ID token to backend
- Backend verifies the Firebase ID token before creating the user account
- Phone number is normalized to E.164 format (+[country code][number]) and stored in the database

## Security Features

1. **E.164 Phone Normalization**: All phone numbers are normalized to international E.164 format using the `phonenumbers` library
   - Supports automatic region detection (default: Australia, +61)
   - Validates phone number format before storage
   - Enables consistent phone number matching across different input formats

2. **Duplicate Prevention**:
   - Database constraints prevent duplicate email registrations
   - Duplicate phone number validation on registration and login
   - Normalized phone format ensures duplicates are caught regardless of input format

3. **Password Security**:
   - Passwords hashed using werkzeug `generate_password_hash()` (bcrypt)
   - No plaintext passwords stored
   - Verification uses `check_password_hash()`

4. **Session Management**:
   - Flask sessions store only `user_id` after successful authentication
   - Sessions are server-managed and cannot be tampered with by clients
   - Session timeout controlled by Flask configuration

## Fallback & Recovery Options

### If Firebase Phone OTP Fails (During Registration)

**Scenario**: User cannot receive SMS or Firebase service is unavailable

**Fallback Option 1: Email Verification**
- Skip phone verification step
- User can register with email/password only
- Phone number field becomes optional
- User can add phone later from profile settings
- Implementation: Modify register form to allow skipping phone verification

**Fallback Option 2: Manual Admin Verification**
- User provides phone number but cannot verify via SMS
- Phone is marked as "unverified"
- Admin reviews and manually verifies the phone (mark verified=true in database)
- User can proceed with phone-based login once verified

### If Phone Login Fails

**Scenario**: User cannot access phone or forgot phone number

**Fallback Option 1: Email Login**
- User can always fall back to email/password login
- Login form includes toggle: "Switch to phone" ↔ "Switch to email"
- Both methods use the same password

**Fallback Option 2: Phone Recovery via Email**
- User logs in with email/password
- User navigates to Settings → Add/Update Phone
- Verification code sent to registered email
- User enters code and new phone number
- New phone is verified and saved

### Account Recovery

**If User Forgets Password**
- User clicks "Forgot Password" link (not yet implemented)
- Email recovery code sent to registered email address
- User clicks link in email with time-limited token
- User sets new password
- Next login requires new password

**If User Cannot Access Registered Email**
- Contact admin support
- Admin verifies identity through other means (phone call, ID verification)
- Admin resets password or updates email address
- User receives temporary credentials
- User logs in and changes password

## Future 2FA Enhancements

### TOTP (Time-Based One-Time Password)
- Users can enable TOTP via authenticator apps (Google Authenticator, Authy, etc.)
- After enabling, login requires both password and TOTP code
- Implementation: Add QR code generation and TOTP validation using `pyotp` library

### Email OTP as Additional Factor
- Optional second factor for high-risk accounts
- 6-digit code sent to email during login
- User enters code to complete authentication
- Implementation: Add email sending via SendGrid/AWS SES

### Backup Codes
- Users can generate backup codes during 2FA setup
- Each code can be used once as fallback authentication
- Printed or saved by user for emergency access
- Implementation: Add backup code generation and validation

### Account Lockout & Suspicious Activity
- Track failed login attempts per user
- Temporary account lock after 5 failed attempts (15 min)
- Email alert to user about suspicious login attempts
- IP-based risk scoring and adaptive authentication

## Implementation Checklist for Admins

- [ ] Enable Firebase phone authentication in Firebase Console
- [ ] Set up email templates for password recovery (future feature)
- [ ] Configure SMS rate limits in Firebase Console (prevent abuse)
- [ ] Monitor failed login attempts via UserLoginLog table
- [ ] Create admin dashboard for manual phone verification
- [ ] Document user support procedures for account recovery
- [ ] Set up email service for OTP delivery (future feature)
- [ ] Configure CORS and security headers for production

## Environment Variables Required

```
FIREBASE_PROJECT_ID=<your-firebase-project-id>
FIREBASE_STORAGE_BUCKET=<your-storage-bucket>
FIREBASE_CREDENTIALS=<path-to-serviceAccountKey.json>
DB_HOST=<mysql-host>
DB_USER=<mysql-user>
DB_PASSWORD=<mysql-password>
DB_NAME=<database-name>
SECRET_KEY=<flask-secret-key>
```

## Database Schema for Phone Verification

The `users` table includes:
- `phone` (VARCHAR): E.164 formatted phone number (+[country][number])
- `phone_verified` (BOOLEAN, optional): Future addition to track verification status

## Testing Phone Authentication

### Testing E.164 Normalization
```python
from blueprints.auth import normalize_phone_e164

# Test cases
normalize_phone_e164("0412345678")           # → "+61412345678" (AU default)
normalize_phone_e164("+61412345678")         # → "+61412345678" (already E.164)
normalize_phone_e164("+1-555-123-4567")      # → "+15551234567" (US)
normalize_phone_e164("invalid")              # → None (invalid format)
```

### Testing Phone Login
```bash
# Register user with phone +61412345678
curl -X POST http://localhost:5000/api/register \
  -H "Content-Type: application/json" \
  -d '{
    "full_name": "Test User",
    "email": "test@example.com",
    "phone": "+61412345678",
    "password": "securepassword123"
  }'

# Login with phone
curl -X POST http://localhost:5000/api/login \
  -H "Content-Type: application/json" \
  -d '{
    "identifier": "+61412345678",
    "password": "securepassword123"
  }'

# Login with email
curl -X POST http://localhost:5000/api/login \
  -H "Content-Type: application/json" \
  -d '{
    "identifier": "test@example.com",
    "password": "securepassword123"
  }'
```

## Support & Resources

- Firebase Phone Authentication: https://firebase.google.com/docs/auth/phone
- Phonenumbers Library: https://github.com/daviddrysdale/python-phonenumbers
- OWASP Authentication Cheat Sheet: https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html
- Flask Security Best Practices: https://flask.palletsprojects.com/en/2.3.x/security/
