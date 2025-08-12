/**
 * Main Application Entry Point for Cricksy Scorer
 * 
 * This file initializes the Vue.js application with all necessary plugins,
 * stores, and configurations for the cricket scoring application.
 */

import { createApp } from 'vue';
import App from './App.vue';
import router from './router';
import pinia from '@/stores'
createApp(App).use(pinia).use(router).mount('#app')


// Import global styles
import '@picocss/pico/css/pico.min.css';
import './assets/main.css';

// Create the Vue application instance
const app = createApp(App);

// Configure the application with plugins
app.use(pinia);  // Pinia store management
app.use(router); // Vue Router for navigation

// Global error handler for unhandled errors
app.config.errorHandler = (error, instance, info) => {
  console.error('Global error:', error);
  console.error('Component instance:', instance);
  console.error('Error info:', info);
  
  // You could send this to an error reporting service
  // errorReportingService.captureException(error, { extra: { info } });
};

// Global warning handler for development
if (import.meta.env.DEV) {
  app.config.warnHandler = (msg, instance, trace) => {
    console.warn('Vue warning:', msg);
    console.warn('Component trace:', trace);
  };
}

// Mount the application to the DOM
app.mount('#app');

// Add this to your main.ts file after the app.mount('#app') line
console.log('🔧 Vue app mounted to #app element')
console.log('📱 App element:', document.getElementById('app'))

// Log successful initialization in development
if (import.meta.env.DEV) {
  console.log('🏏 Cricksy Scorer application initialized successfully');
  console.log('Environment:', import.meta.env.MODE);
  console.log('API Base URL:', import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000');
}

