# PayPal Testing Guide for Maa Express

## 1. PayPal Sandbox Setup

### Step 1: Get Sandbox Credentials

1. Go to [PayPal Developer Dashboard](https://developer.paypal.com/dashboard/)
2. Log in with your PayPal account
3. Navigate to **Apps & Credentials**
4. Under **Sandbox**, click **Create App**
5. Name your app (e.g., "Maa Express Dev")
6. Copy your **Client ID** and **Secret**

### Step 2: Configure `.env` File

Add to your `.env` file:

```env
# PayPal Configuration
PAYPAL_MODE=sandbox
PAYPAL_CLIENT_ID=your_sandbox_client_id_here
PAYPAL_CLIENT_SECRET=your_sandbox_secret_here
```

**Important:** Never commit real credentials to git!

---

## 2. PayPal Sandbox Test Accounts

### Default Sandbox Accounts

PayPal automatically creates test accounts:

1. **Personal Account (Buyer)** - Use this to test purchases
   - Email: `sb-xxxxx@personal.example.com`
   - Password: Shown in dashboard

2. **Business Account (Seller)** - Receives payments
   - Email: `sb-xxxxx@business.example.com`
   - Password: Shown in dashboard

### View Test Accounts

1. Go to [Sandbox Accounts](https://developer.paypal.com/dashboard/accounts)
2. Click on any account to view credentials
3. Click "View/Edit Account" to see email and password

---

## 3. Testing Payment Flow

### Test Purchase Flow

1. **Create a listing** on Maa Express (logged in as seller)

2. **Buy listing** (logged in as buyer)
   - Select weight and fill receiver details
   - Choose PayPal as payment method
   - Click "Pay with PayPal"

3. **PayPal Sandbox Login**
   - You'll be redirected to PayPal sandbox
   - URL will be `sandbox.paypal.com`
   - Login with your **Personal sandbox account**

4. **Complete Payment**
   - Review payment details
   - Click "Pay Now"
   - You'll be redirected back to Maa Express

5. **Verify Success**
   - You should see handover/delivery codes
   - Check console for payment logs

---

## 4. Common Issues & Solutions

### Issue 1: "PayPal SDK not installed"

**Solution:**
```bash
pip install paypalrestsdk
```

### Issue 2: "PayPal credentials not configured"

**Solution:**
- Check `.env` has `PAYPAL_CLIENT_ID` and `PAYPAL_CLIENT_SECRET`
- Restart Flask server after editing `.env`

### Issue 3: "An error occurred" message

**Check:**
1. Open browser console (F12) - look for error messages
2. Check Flask terminal - look for error logs
3. Verify credentials are from **Sandbox** (not Live)
4. Ensure `PAYPAL_MODE=sandbox` in `.env`

### Issue 4: Currency mismatch error

**Solution:**
- PayPal sandbox supports: USD, EUR, GBP, AUD, CAD, etc.
- If testing with BDT, switch listing currency to USD

### Issue 5: "Invalid credentials" error

**Solution:**
1. Go to PayPal Developer Dashboard
2. Verify your app is **active**
3. Regenerate credentials if needed
4. Update `.env` with new credentials

---

## 5. Testing Checklist

### Before Testing
- [ ] PayPal SDK installed (`pip install paypalrestsdk`)
- [ ] `.env` has `PAYPAL_CLIENT_ID` and `PAYPAL_CLIENT_SECRET`
- [ ] `PAYPAL_MODE=sandbox` (not `live`)
- [ ] Flask server restarted after `.env` changes
- [ ] Sandbox test accounts created (buyer + seller)

### During Testing
- [ ] Can create PayPal order (check console logs)
- [ ] Redirected to `sandbox.paypal.com` (not `paypal.com`)
- [ ] Can login with sandbox account
- [ ] Payment amount matches listing price
- [ ] Can complete payment
- [ ] Redirected back to Maa Express
- [ ] Handover/delivery codes generated

### After Testing
- [ ] Payment shows in PayPal sandbox dashboard
- [ ] Order status updated to "pending_handover"
- [ ] Buyer can see purchase in account
- [ ] Seller can verify handover code

---

## 6. Switching to Live Mode (Production)

**⚠️ WARNING: Only do this when ready for real payments!**

### Step 1: Get Live Credentials

1. Go to [PayPal Developer Dashboard](https://developer.paypal.com/dashboard/)
2. Navigate to **Apps & Credentials**
3. Under **Live**, click **Create App**
4. Copy **Live Client ID** and **Live Secret**

### Step 2: Update `.env`

```env
PAYPAL_MODE=live
PAYPAL_CLIENT_ID=your_live_client_id_here
PAYPAL_CLIENT_SECRET=your_live_secret_here
```

### Step 3: Verification

- Test with a **real PayPal account** (use small amount like $0.50)
- URL will be `paypal.com` (not sandbox)
- Real money will be transferred

---

## 7. Debug Commands

### Check PayPal Configuration

```bash
python -c "from config import Config; print(f'Mode: {Config.PAYPAL_MODE}'); print(f'Client ID: {Config.PAYPAL_CLIENT_ID[:20]}...')"
```

### Test PayPal Connection

```bash
python utils/payment_utils.py
```

This will show PayPal connection status in the output.

---

## 8. Support Resources

- [PayPal Developer Documentation](https://developer.paypal.com/docs/)
- [PayPal REST API Reference](https://developer.paypal.com/docs/api/overview/)
- [PayPal Sandbox Guide](https://developer.paypal.com/docs/api-basics/sandbox/)
- [PayPal Error Codes](https://developer.paypal.com/docs/integration/direct/rest/errors/)

---

## Quick Reference

| Environment | Mode | Credentials Location | Test Accounts |
|-------------|------|---------------------|---------------|
| Development | `sandbox` | Developer Dashboard > Sandbox | Auto-generated |
| Production | `live` | Developer Dashboard > Live | Real accounts |

**Remember:** Always test in sandbox first! 🧪
