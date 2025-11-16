/**
 * ============================================================================
 * CATEGORY 1 LISTING WIZARD - FRONTEND LOGIC (REORDERED STEPS)
 * ============================================================================
 * NEW FLOW:
 * Step 1: Travel Date, Service Type, Pricing & Documents
 * Step 2: Origin & Destination Details
 * Step 3: Phone Verification & Submission
 */

// ============================================================================
// GLOBAL STATE
// ============================================================================

let currentStep = 1;
let wizardData = {
  // Step 1: Travel Date, Service Type, Pricing & Documents
  travel_date: '',
  service_type: 'Included pick up at Origin and delivery at Destination.',
  description: '',
  currency: 'AUD',
  price_per_kg: '',
  total_weight: '',
  discount_percent: '0',
  passport_photo_url: '',
  ticket_copy_url: '',
  
  // Step 2: Origin & Destination
  origin: '',
  origin_airport: '',
  origin_delivery_location: '',
  origin_delivery_postcode: '',
  origin_phone_country_code: '+61',
  origin_phone_local: '',
  
  destination: '',
  destination_airport: '',
  destination_delivery_location: '',
  destination_delivery_postcode: '',
  destination_phone_country_code: '',
  destination_phone_local: '',
  
  // Step 3: Verification
  phone_verified: false
};

let recaptchaVerifier = null;
let confirmationResult = null;

// ============================================================================
// FIREBASE INITIALIZATION
// ============================================================================

const { initializeApp, getApps } = window.firebaseApp;
const { getAuth, RecaptchaVerifier, signInWithPhoneNumber } = window.firebaseAuth;
const { getStorage, ref, uploadBytesResumable, getDownloadURL } = window.firebaseStorage;

const firebaseConfig = {
  apiKey: window.FIREBASE_CONFIG?.apiKey || '',
  authDomain: window.FIREBASE_CONFIG?.authDomain || '',
  projectId: window.FIREBASE_CONFIG?.projectId || '',
  storageBucket: window.FIREBASE_CONFIG?.storageBucket || '',
  messagingSenderId: window.FIREBASE_CONFIG?.messagingSenderId || '',
  appId: window.FIREBASE_CONFIG?.appId || ''
};

const app = getApps().length ? getApps()[0] : initializeApp(firebaseConfig);
const auth = getAuth(app);
const storage = getStorage(app);

// ============================================================================
// WIZARD NAVIGATION
// ============================================================================

window.nextStep = function(fromStep) {
  if (!validateStep(fromStep)) {
    return;
  }
  
  collectStepData(fromStep);
  
  document.querySelector(`.wizard-step[data-step="${fromStep}"]`).classList.remove('active');
  
  const nextStepNum = fromStep + 1;
  document.querySelector(`.wizard-step[data-step="${nextStepNum}"]`).classList.add('active');
  
  updateProgressIndicator(nextStepNum);
  
  if (nextStepNum === 3) {
    initializePhoneVerification();
  }
  
  window.scrollTo({ top: 0, behavior: 'smooth' });
  
  currentStep = nextStepNum;
};

window.prevStep = function(fromStep) {
  document.querySelector(`.wizard-step[data-step="${fromStep}"]`).classList.remove('active');
  
  const prevStepNum = fromStep - 1;
  document.querySelector(`.wizard-step[data-step="${prevStepNum}"]`).classList.add('active');
  
  updateProgressIndicator(prevStepNum);
  
  window.scrollTo({ top: 0, behavior: 'smooth' });
  
  currentStep = prevStepNum;
};

function updateProgressIndicator(stepNum) {
  const steps = document.querySelectorAll('.progress-step');
  
  steps.forEach((step, index) => {
    const stepNumber = index + 1;
    
    if (stepNumber < stepNum) {
      step.classList.add('completed');
      step.classList.remove('active');
    } else if (stepNumber === stepNum) {
      step.classList.add('active');
      step.classList.remove('completed');
    } else {
      step.classList.remove('active', 'completed');
    }
  });
}

// ============================================================================
// STEP VALIDATION
// ============================================================================

function validateStep(stepNum) {
  const messageEl = document.getElementById(`step${stepNum}-message`);
  
  if (stepNum === 1) {
    // Validate travel date
    const travelDateInput = document.querySelector('[name="travel_date"]');
    if (!travelDateInput || !travelDateInput.value) {
      showMessage(messageEl, 'Please select a travel date', 'error');
      travelDateInput?.focus();
      return false;
    }
    
    const travelDate = new Date(travelDateInput.value);
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    
    if (travelDate <= today) {
      showMessage(messageEl, 'Travel date must be in the future', 'error');
      travelDateInput.focus();
      return false;
    }
    
    // Validate service type
    const serviceType = document.querySelector('[name="service_type"]:checked');
    if (!serviceType) {
      showMessage(messageEl, 'Please select a service type', 'error');
      return false;
    }
    
    // Validate pricing
    const pricePerKg = parseFloat(document.querySelector('[name="price_per_kg"]').value);
    const totalWeight = parseFloat(document.querySelector('[name="total_weight"]').value);
    const discount = parseFloat(document.querySelector('[name="discount_percent"]').value || 0);
    
    if (!pricePerKg || pricePerKg <= 0 || pricePerKg > 10000) {
      showMessage(messageEl, 'Price per kg must be between 0 and 10,000', 'error');
      document.querySelector('[name="price_per_kg"]').focus();
      return false;
    }
    
    if (!totalWeight || totalWeight <= 0 || totalWeight > 100) {
      showMessage(messageEl, 'Total weight must be between 0 and 100 kg', 'error');
      document.querySelector('[name="total_weight"]').focus();
      return false;
    }
    
    if (discount < 0 || discount > 100) {
      showMessage(messageEl, 'Discount must be between 0 and 100%', 'error');
      return false;
    }
    
    return true;
  }
  
  if (stepNum === 2) {
    // Validate required location fields
    const requiredFields = [
      'origin', 'origin_airport', 'destination', 'destination_airport',
      'origin_phone_country_code', 'origin_phone_local'
    ];
    
    for (const field of requiredFields) {
      const input = document.querySelector(`[name="${field}"]`);
      if (!input || !input.value.trim()) {
        showMessage(messageEl, `Please fill in: ${field.replace(/_/g, ' ')}`, 'error');
        input?.focus();
        return false;
      }
    }
    
    // Validate phone number format
    const phoneLocal = document.querySelector('[name="origin_phone_local"]').value;
    if (phoneLocal.length < 6 || !/^\d+$/.test(phoneLocal)) {
      showMessage(messageEl, 'Please enter a valid phone number', 'error');
      return false;
    }
    
    return true;
  }
  
  return true;
}

function collectStepData(stepNum) {
  if (stepNum === 1) {
    wizardData.travel_date = document.querySelector('[name="travel_date"]').value;
    wizardData.service_type = document.querySelector('[name="service_type"]:checked').value;
    wizardData.description = document.querySelector('[name="description"]')?.value.trim() || '';
    wizardData.currency = document.querySelector('[name="currency"]').value;
    wizardData.price_per_kg = document.querySelector('[name="price_per_kg"]').value;
    wizardData.total_weight = document.querySelector('[name="total_weight"]').value;
    wizardData.discount_percent = document.querySelector('[name="discount_percent"]').value || '0';
    wizardData.passport_photo_url = document.getElementById('passport-photo-url')?.value || '';
    wizardData.ticket_copy_url = document.getElementById('ticket-copy-url')?.value || '';
  }
  
  if (stepNum === 2) {
    wizardData.origin = document.querySelector('[name="origin"]').value.trim();
    wizardData.origin_airport = document.querySelector('[name="origin_airport"]').value.trim();
    wizardData.origin_delivery_location = document.querySelector('[name="origin_delivery_location"]')?.value.trim() || '';
    wizardData.origin_delivery_postcode = document.querySelector('[name="origin_delivery_postcode"]')?.value.trim() || '';
    wizardData.origin_phone_country_code = document.querySelector('[name="origin_phone_country_code"]').value;
    wizardData.origin_phone_local = document.querySelector('[name="origin_phone_local"]').value.trim();
    
    wizardData.destination = document.querySelector('[name="destination"]').value.trim();
    wizardData.destination_airport = document.querySelector('[name="destination_airport"]').value.trim();
    wizardData.destination_delivery_location = document.querySelector('[name="destination_delivery_location"]')?.value.trim() || '';
    wizardData.destination_delivery_postcode = document.querySelector('[name="destination_delivery_postcode"]')?.value.trim() || '';
    wizardData.destination_phone_country_code = document.querySelector('[name="destination_phone_country_code"]')?.value || '';
    wizardData.destination_phone_local = document.querySelector('[name="destination_phone_local"]')?.value.trim() || '';
  }
}

// ============================================================================
// PRICING CALCULATOR (STEP 1)
// ============================================================================

function initializePricingCalculator() {
  const pricePerKgInput = document.querySelector('[name="price_per_kg"]');
  const totalWeightInput = document.querySelector('[name="total_weight"]');
  const discountInput = document.querySelector('[name="discount_percent"]');
  const currencySelect = document.querySelector('[name="currency"]');
  
  if (!pricePerKgInput || !totalWeightInput) return;
  
  [pricePerKgInput, totalWeightInput, discountInput, currencySelect].forEach(input => {
    input?.addEventListener('input', updatePricePreview);
  });
  
  updatePricePreview();
}

function updatePricePreview() {
  const pricePerKg = parseFloat(document.querySelector('[name="price_per_kg"]')?.value || 0);
  const totalWeight = parseFloat(document.querySelector('[name="total_weight"]')?.value || 0);
  const discountPercent = parseFloat(document.querySelector('[name="discount_percent"]')?.value || 0);
  const currency = document.querySelector('[name="currency"]')?.value || 'AUD';
  
  const basePrice = pricePerKg * totalWeight;
  const discountAmount = basePrice * (discountPercent / 100);
  const finalPrice = basePrice - discountAmount;
  
  const previewPricePerKg = document.getElementById('preview-price-per-kg');
  const previewWeight = document.getElementById('preview-weight');
  const previewBasePrice = document.getElementById('preview-base-price');
  const previewDiscount = document.getElementById('preview-discount');
  const previewFinalPrice = document.getElementById('preview-final-price');
  
  if (previewPricePerKg) previewPricePerKg.textContent = `${currency} ${pricePerKg.toFixed(2)}/kg`;
  if (previewWeight) previewWeight.textContent = `${totalWeight.toFixed(1)} kg`;
  if (previewBasePrice) previewBasePrice.textContent = `${currency} ${basePrice.toFixed(2)}`;
  if (previewDiscount) previewDiscount.textContent = `-${currency} ${discountAmount.toFixed(2)} (${discountPercent}%)`;
  if (previewFinalPrice) previewFinalPrice.textContent = `${currency} ${finalPrice.toFixed(2)}`;
}

// ============================================================================
// FILE UPLOAD (STEP 1) - FIREBASE STORAGE
// ============================================================================

function initializeFileUploads() {
  const passportPhotoInput = document.getElementById('passport-photo-input');
  if (passportPhotoInput) {
    passportPhotoInput.addEventListener('change', (e) => {
      handleFileUpload(e.target.files[0], 'passport-photo');
    });
  }
  
  const ticketCopyInput = document.getElementById('ticket-copy-input');
  if (ticketCopyInput) {
    ticketCopyInput.addEventListener('change', (e) => {
      handleFileUpload(e.target.files[0], 'ticket-copy');
    });
  }
}

async function handleFileUpload(file, type) {
  if (!file) return;
  
  const maxSize = type === 'passport-photo' ? 10 * 1024 * 1024 : 5 * 1024 * 1024;
  if (file.size > maxSize) {
    alert(`File too large. Maximum size: ${maxSize / (1024 * 1024)}MB`);
    return;
  }
  
  const validTypes = ['image/jpeg', 'image/jpg', 'image/png', 'image/gif', 'application/pdf'];
  if (!validTypes.includes(file.type)) {
    alert('Invalid file type. Please upload an image or PDF.');
    return;
  }
  
  const timestamp = Date.now();
  const filename = `${type}_${timestamp}_${file.name}`;
  const storagePath = `category1_listings/${filename}`;
  
  const storageRef = ref(storage, storagePath);
  const uploadTask = uploadBytesResumable(storageRef, file);
  
  const progressBar = document.getElementById(`${type}-progress-bar`);
  const progressContainer = document.getElementById(`${type}-progress`);
  const fileNameDisplay = document.getElementById(`${type}-name`);
  
  if (progressContainer) progressContainer.style.display = 'block';
  
  uploadTask.on('state_changed',
    (snapshot) => {
      const progress = (snapshot.bytesTransferred / snapshot.totalBytes) * 100;
      if (progressBar) {
        progressBar.style.width = progress + '%';
      }
    },
    (error) => {
      console.error('Upload error:', error);
      alert('Upload failed: ' + error.message);
      if (progressContainer) progressContainer.style.display = 'none';
    },
    async () => {
      try {
        const downloadURL = await getDownloadURL(uploadTask.snapshot.ref);
        
        const urlInput = document.getElementById(`${type}-url`);
        if (urlInput) {
          urlInput.value = downloadURL;
        }
        
        if (fileNameDisplay) {
          fileNameDisplay.textContent = `✓ ${file.name} uploaded successfully`;
        }
        
        setTimeout(() => {
          if (progressContainer) progressContainer.style.display = 'none';
        }, 2000);
        
      } catch (error) {
        console.error('Error getting download URL:', error);
        alert('Failed to get file URL');
      }
    }
  );
}

// ============================================================================
// PHONE VERIFICATION (STEP 3)
// ============================================================================

function initializePhoneVerification() {
  const fullPhone = wizardData.origin_phone_country_code + wizardData.origin_phone_local;
  
  const phoneDisplay = document.getElementById('phone-display');
  if (phoneDisplay) {
    phoneDisplay.textContent = maskPhoneNumber(fullPhone);
  }
  
  if (!recaptchaVerifier) {
    recaptchaVerifier = new RecaptchaVerifier('recaptcha-container', {
      size: 'invisible',
      callback: () => {
        console.log('reCAPTCHA verified');
      }
    }, auth);
  }
  
  const sendOtpBtn = document.getElementById('send-otp-btn');
  const verifyOtpBtn = document.getElementById('verify-otp-btn');
  
  if (sendOtpBtn) {
    sendOtpBtn.addEventListener('click', sendOTP);
  }
  
  if (verifyOtpBtn) {
    verifyOtpBtn.addEventListener('click', verifyOTP);
  }
}

function maskPhoneNumber(phone) {
  if (phone.length < 8) return phone;
  const last4 = phone.slice(-4);
  const masked = '*'.repeat(phone.length - 4);
  return masked + last4;
}

async function sendOTP() {
  const sendBtn = document.getElementById('send-otp-btn');
  const messageEl = document.getElementById('step3-message');
  const otpSection = document.getElementById('otp-input-section');
  
  sendBtn.disabled = true;
  sendBtn.textContent = 'Sending OTP...';
  showMessage(messageEl, 'Sending OTP...', 'info');
  
  try {
    const fullPhone = wizardData.origin_phone_country_code + wizardData.origin_phone_local;
    
    confirmationResult = await signInWithPhoneNumber(auth, fullPhone, recaptchaVerifier);
    
    if (otpSection) {
      otpSection.style.display = 'block';
    }
    
    showMessage(messageEl, `OTP sent to ${maskPhoneNumber(fullPhone)}`, 'success');
    sendBtn.textContent = '📱 Resend OTP';
    sendBtn.disabled = false;
    
  } catch (error) {
    console.error('Error sending OTP:', error);
    showMessage(messageEl, `Failed to send OTP: ${error.message}`, 'error');
    sendBtn.textContent = '📱 Send OTP';
    sendBtn.disabled = false;
  }
}

async function verifyOTP() {
  const otpInput = document.getElementById('otp-code');
  const verifyBtn = document.getElementById('verify-otp-btn');
  const messageEl = document.getElementById('step3-message');
  
  const otpCode = otpInput.value.trim();
  
  if (otpCode.length !== 6) {
    showMessage(messageEl, 'Please enter a valid 6-digit OTP', 'error');
    return;
  }
  
  verifyBtn.disabled = true;
  verifyBtn.textContent = 'Verifying...';
  showMessage(messageEl, 'Verifying OTP...', 'info');
  
  try {
    await confirmationResult.confirm(otpCode);
    
    wizardData.phone_verified = true;
    document.getElementById('phone-verified').value = 'true';
    
    showMessage(messageEl, '✓ Phone verified successfully!', 'success');
    
    const verificationSection = document.querySelector('.verification-section');
    if (verificationSection) {
      verificationSection.classList.add('verification-success');
    }
    
    setTimeout(() => {
      submitListing();
    }, 1500);
    
  } catch (error) {
    console.error('Error verifying OTP:', error);
    showMessage(messageEl, `Verification failed: ${error.message}`, 'error');
    verifyBtn.textContent = '✓ Verify OTP & Submit Listing';
    verifyBtn.disabled = false;
  }
}

// ============================================================================
// FINAL SUBMISSION
// ============================================================================

async function submitListing() {
  const messageEl = document.getElementById('step3-message');
  
  showMessage(messageEl, 'Submitting listing...', 'info');
  
  try {
    const payload = {
      // Step 1: Travel & Pricing
      travel_date: wizardData.travel_date,
      service_type: wizardData.service_type,
      description: wizardData.description,
      currency: wizardData.currency,
      price_per_kg: wizardData.price_per_kg,
      total_weight: wizardData.total_weight,
      discount_percent: wizardData.discount_percent,
      passport_photo_url: wizardData.passport_photo_url,
      ticket_copy_url: wizardData.ticket_copy_url,
      
      // Step 2: Locations
      origin: wizardData.origin,
      origin_airport: wizardData.origin_airport,
      origin_delivery_location: wizardData.origin_delivery_location,
      origin_delivery_postcode: wizardData.origin_delivery_postcode,
      origin_phone_number: wizardData.origin_phone_country_code + wizardData.origin_phone_local,
      
      destination: wizardData.destination,
      destination_airport: wizardData.destination_airport,
      destination_delivery_location: wizardData.destination_delivery_location,
      destination_delivery_postcode: wizardData.destination_delivery_postcode,
      destination_phone_number: wizardData.destination_phone_country_code + wizardData.destination_phone_local,
      
      // Step 3: Verification
      phone_verified: wizardData.phone_verified
    };
    
    const url = window.WIZARD_MODE === 'edit' 
      ? window.UPDATE_URL 
      : window.CREATE_URL;
    
    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(payload)
    });
    
    const data = await response.json();
    
    if (!response.ok) {
      throw new Error(data.error || 'Submission failed');
    }
    
    showMessage(messageEl, data.message, 'success');
    
    setTimeout(() => {
      window.location.href = data.redirect_url;
    }, 2000);
    
  } catch (error) {
    console.error('Submission error:', error);
    showMessage(messageEl, `Failed to submit: ${error.message}`, 'error');
  }
}

// ============================================================================
// UTILITY FUNCTIONS
// ============================================================================

function showMessage(element, text, type) {
  if (!element) return;
  
  element.textContent = text;
  element.className = `form-message ${type}`;
  element.style.display = 'block';
}

// ============================================================================
// INITIALIZATION
// ============================================================================

document.addEventListener('DOMContentLoaded', () => {
  console.log('Listing Wizard initialized (reordered steps)');
  
  initializePricingCalculator();
  initializeFileUploads();
  updateProgressIndicator(1);
  
  // Service type radio button interaction
  const serviceOptions = document.querySelectorAll('.service-option');
  const serviceRadios = document.querySelectorAll('input[name="service_type"]');
  
  serviceRadios.forEach(radio => {
    radio.addEventListener('change', function() {
      serviceOptions.forEach(opt => opt.classList.remove('selected'));
      if (this.checked) {
        this.closest('.service-option').classList.add('selected');
      }
    });
  });
  
  serviceOptions.forEach(option => {
    option.addEventListener('click', function(e) {
      if (e.target.tagName !== 'INPUT') {
        const radio = this.querySelector('input[type="radio"]');
        if (radio) {
          radio.checked = true;
          radio.dispatchEvent(new Event('change'));
        }
      }
    });
  });
});