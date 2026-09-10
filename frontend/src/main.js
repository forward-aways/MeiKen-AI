import { createApp } from 'vue'
import App from './App.vue'
import './assets/main.css'
import { installGlobalHandlers } from './logger.js'

installGlobalHandlers()

const app = createApp(App)
app.mount('#app')
