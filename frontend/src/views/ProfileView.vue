<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/authStore'
import { changePassword } from '@/services/auth'

const router = useRouter()
const auth = useAuthStore()

// User profile state
const userEmail = ref('')
const userName = ref('')
const userId = ref('')
const memberSince = ref('')

// Password change state
const currentPassword = ref('')
const newPassword = ref('')
const confirmPassword = ref('')
const showPasswords = ref(false)
const isChangingPassword = ref(false)
const passwordMessage = ref<{ type: 'success' | 'error'; text: string } | null>(null)

// Computed properties
const isLoggedIn = computed(() => auth.isLoggedIn)
const passwordsMatch = computed(() => newPassword.value === confirmPassword.value)
const canSubmit = computed(
  () =>
    currentPassword.value &&
    newPassword.value &&
    confirmPassword.value &&
    passwordsMatch.value &&
    newPassword.value.length >= 6
)

// Load user data
async function loadUserData() {
  try {
    userEmail.value = auth.userEmail
    userName.value = auth.userName
    userId.value = auth.userId
    memberSince.value = auth.createdAt || new Date().toISOString()
  } catch (error) {
    console.error('Failed to load user data:', error)
  }
}

// Change password handler
async function handleChangePassword() {
  if (!canSubmit.value) {
    return
  }

  isChangingPassword.value = true
  passwordMessage.value = null

  try {
    await changePassword(currentPassword.value, newPassword.value)

    passwordMessage.value = {
      type: 'success',
      text: 'Password changed successfully! Please log in again.',
    }

    // Reset form
    currentPassword.value = ''
    newPassword.value = ''
    confirmPassword.value = ''

    // Redirect to login after 2 seconds
    setTimeout(() => {
      auth.logout()
      router.push('/login')
    }, 2000)
  } catch (error: any) {
    console.error('Failed to change password:', error)
    passwordMessage.value = {
      type: 'error',
      text: error.response?.data?.detail || 'Failed to change password. Please try again.',
    }
  } finally {
    isChangingPassword.value = false
  }
}

// Format date
function formatDate(dateString: string): string {
  if (!dateString) return 'N/A'
  try {
    const date = new Date(dateString)
    return date.toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
    })
  } catch {
    return dateString
  }
}

// Initialize
onMounted(() => {
  if (!isLoggedIn.value) {
    router.push('/login')
  } else {
    loadUserData()
  }
})
</script>

<template>
  <div v-if="isLoggedIn" class="profile-container">
    <div class="profile-wrapper">
      <h1>Profile</h1>

      <!-- User Info Section -->
      <div class="info-section">
        <h2>Account Information</h2>
        <div class="info-grid">
          <div class="info-item">
            <label>Email</label>
            <p>{{ userEmail }}</p>
          </div>
          <div class="info-item">
            <label>User ID</label>
            <p class="user-id">{{ userId }}</p>
          </div>
          <div class="info-item">
            <label>Member Since</label>
            <p>{{ formatDate(memberSince) }}</p>
          </div>
        </div>
      </div>

      <!-- Password Change Section -->
      <div class="password-section">
        <h2>Change Password</h2>
        <p class="section-description">
          Update your password regularly to keep your account secure. For beta users, we recommend
          changing the temporary password provided to you.
        </p>

        <!-- Success/Error Message -->
        <transition name="message">
          <div v-if="passwordMessage" :class="['message', passwordMessage.type]">
            {{ passwordMessage.text }}
          </div>
        </transition>

        <form @submit.prevent="handleChangePassword">
          <!-- Current Password -->
          <div class="form-group">
            <label for="current-password">Current Password</label>
            <div class="password-input-wrapper">
              <input
                id="current-password"
                v-model="currentPassword"
                :type="showPasswords ? 'text' : 'password'"
                placeholder="Enter your current password"
                required
                autocomplete="current-password"
              />
            </div>
          </div>

          <!-- New Password -->
          <div class="form-group">
            <label for="new-password">New Password</label>
            <div class="password-input-wrapper">
              <input
                id="new-password"
                v-model="newPassword"
                :type="showPasswords ? 'text' : 'password'"
                placeholder="Enter a new password"
                required
                autocomplete="new-password"
                minlength="6"
              />
            </div>
            <small v-if="newPassword.length < 6" class="password-hint">
              Password must be at least 6 characters
            </small>
          </div>

          <!-- Confirm Password -->
          <div class="form-group">
            <label for="confirm-password">Confirm New Password</label>
            <div class="password-input-wrapper">
              <input
                id="confirm-password"
                v-model="confirmPassword"
                :type="showPasswords ? 'text' : 'password'"
                placeholder="Re-enter your new password"
                required
                autocomplete="new-password"
                minlength="6"
              />
            </div>
            <transition name="fade">
              <small v-if="confirmPassword && !passwordsMatch" class="error-hint">
                Passwords do not match
              </small>
              <small v-else-if="confirmPassword && passwordsMatch" class="success-hint">
                Passwords match
              </small>
            </transition>
          </div>

          <!-- Show/Hide Password Toggle -->
          <div class="checkbox-group">
            <input
              id="show-passwords"
              v-model="showPasswords"
              type="checkbox"
            />
            <label for="show-passwords">Show passwords</label>
          </div>

          <!-- Submit Button -->
          <button
            type="submit"
            :disabled="!canSubmit || isChangingPassword"
            class="btn-primary"
          >
            <span v-if="!isChangingPassword">Change Password</span>
            <span v-else>Updating...</span>
          </button>
        </form>
      </div>

      <!-- Security Tips -->
      <div class="security-tips">
        <h3>Security Tips</h3>
        <ul>
          <li>Use a unique password that you don't use on other websites</li>
          <li>Include a mix of uppercase, lowercase, numbers, and special characters</li>
          <li>Avoid using personal information in your password</li>
          <li>Never share your password with anyone</li>
        </ul>
      </div>
    </div>
  </div>
</template>

<style scoped>
.profile-container {
  min-height: 100vh;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  padding: 40px 20px;
}

.profile-wrapper {
  max-width: 600px;
  margin: 0 auto;
  background: white;
  border-radius: 12px;
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.2);
  padding: 40px;
}

h1 {
  color: #333;
  font-size: 28px;
  margin-bottom: 30px;
  text-align: center;
}

h2 {
  color: #555;
  font-size: 18px;
  margin-bottom: 20px;
  border-bottom: 2px solid #667eea;
  padding-bottom: 10px;
}

h3 {
  color: #555;
  font-size: 16px;
  margin-bottom: 15px;
}

/* Info Section */
.info-section {
  margin-bottom: 40px;
  padding-bottom: 30px;
  border-bottom: 1px solid #eee;
}

.info-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 20px;
}

.info-item {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.info-item label {
  font-weight: 600;
  color: #666;
  font-size: 14px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.info-item p {
  color: #333;
  font-size: 16px;
  margin: 0;
}

.user-id {
  font-family: 'Monaco', 'Courier New', monospace;
  background: #f5f5f5;
  padding: 8px 12px;
  border-radius: 4px;
  font-size: 13px;
  word-break: break-all;
}

/* Password Section */
.password-section {
  margin-bottom: 40px;
}

.section-description {
  color: #666;
  font-size: 14px;
  margin-bottom: 20px;
  line-height: 1.5;
}

/* Message Alerts */
.message {
  padding: 12px 16px;
  border-radius: 6px;
  margin-bottom: 20px;
  font-size: 14px;
  font-weight: 500;
}

.message.success {
  background: #d4edda;
  color: #155724;
  border: 1px solid #c3e6cb;
}

.message.error {
  background: #f8d7da;
  color: #721c24;
  border: 1px solid #f5c6cb;
}

/* Form */
form {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.form-group label {
  font-weight: 600;
  color: #333;
  font-size: 14px;
}

.password-input-wrapper {
  position: relative;
}

input[type='password'],
input[type='text'] {
  width: 100%;
  padding: 12px;
  border: 1px solid #ddd;
  border-radius: 6px;
  font-size: 14px;
  transition: border-color 0.2s;
  font-family: inherit;
}

input[type='password']:focus,
input[type='text']:focus {
  outline: none;
  border-color: #667eea;
  box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
}

input[type='password']:disabled,
input[type='text']:disabled {
  background: #f5f5f5;
  cursor: not-allowed;
}

.password-hint,
.error-hint,
.success-hint {
  font-size: 12px;
  display: block;
}

.password-hint {
  color: #999;
}

.error-hint {
  color: #d32f2f;
}

.success-hint {
  color: #388e3c;
}

/* Checkbox Group */
.checkbox-group {
  display: flex;
  align-items: center;
  gap: 8px;
}

.checkbox-group input[type='checkbox'] {
  width: 18px;
  height: 18px;
  cursor: pointer;
  accent-color: #667eea;
}

.checkbox-group label {
  margin: 0;
  font-weight: 400;
  cursor: pointer;
  font-size: 14px;
}

/* Buttons */
.btn-primary {
  padding: 12px 24px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border: none;
  border-radius: 6px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.btn-primary:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 5px 15px rgba(102, 126, 234, 0.4);
}

.btn-primary:active:not(:disabled) {
  transform: translateY(0);
}

.btn-primary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* Security Tips */
.security-tips {
  background: #f9f9f9;
  padding: 20px;
  border-radius: 8px;
  border-left: 4px solid #667eea;
}

.security-tips ul {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.security-tips li {
  color: #555;
  font-size: 14px;
  padding-left: 24px;
  position: relative;
  line-height: 1.5;
}

.security-tips li::before {
  content: '✓';
  position: absolute;
  left: 0;
  color: #667eea;
  font-weight: bold;
}

/* Transitions */
.message-enter-active,
.message-leave-active {
  transition: all 0.3s ease;
}

.message-enter-from,
.message-leave-to {
  opacity: 0;
  transform: translateY(-10px);
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

/* Responsive */
@media (max-width: 600px) {
  .profile-wrapper {
    padding: 20px;
  }

  h1 {
    font-size: 24px;
  }

  h2 {
    font-size: 16px;
  }

  .info-grid {
    grid-template-columns: 1fr;
  }
}
</style>
