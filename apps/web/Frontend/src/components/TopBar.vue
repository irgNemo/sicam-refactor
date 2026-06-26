<template>
  <nav class="topbar">
    <div class="logo-section">
      <div class="logo-icon"></div>
      <div class="logo-text">MicroScan</div>
    </div>

    <div class="nav-buttons">
      <button
        class="nav-btn"
        :class="{ active: seccion === 'segmentacion' }"
        @click="$emit('change-section', 'segmentacion')"
      >
        <span class="nav-icon">🧬</span>
        Segmentación
      </button>

      <button
        class="nav-btn"
        :class="{ active: seccion === 'caracterizacion' }"
        @click="$emit('change-section', 'caracterizacion')"
      >
        <span class="nav-icon">📊</span>
        Caracterización
      </button>
      
      <button
        class="nav-btn"
        :class="{ active: seccion === 'analisis' }"
        @click="$emit('change-section', 'analisis')"
      >
        <span class="nav-icon">🔍</span>
        Análisis
      </button>

      <button
        class="nav-btn"
        :class="{ active: seccion === 'registro' }"
        @click="$emit('change-section', 'registro')"
      >
        <span class="nav-icon">📝</span>
        Registro
      </button>
    </div>

    <div class="topbar-actions">
      <button class="action-btn" title="Notificaciones">
        <span class="notification-dot"></span>
        🔔
      </button>
      <button class="action-btn" title="Configuración">⚙️</button>
    </div>
  </nav>
</template>

<script>
export default {
  name: "TopBar",
  props: {
    seccion: {
      type: String,
      required: true,
    },
  },
};
</script>

<style scoped>
.topbar {
  height: 60px;
  background: linear-gradient(to right, #ffffff 0%, #f8f9fa 100%);
  border-bottom: 2px solid #e0e0e0;
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 24px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
}

/* LOGO */
.logo-section {
  display: flex;
  align-items: center;
  gap: 10px;
}

.logo-icon {
  font-size: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.logo-text {
  font-weight: 700;
  font-size: 20px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  letter-spacing: -0.5px;
}

/* NAVEGACIÓN */
.nav-buttons {
  display: flex;
  gap: 6px;
  flex: 1;
  justify-content: center;
  padding: 0 20px;
}

.nav-btn {
  background: transparent;
  border: 2px solid transparent;
  padding: 8px 18px;
  font-size: 14px;
  color: #666;
  cursor: pointer;
  border-radius: 10px;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  font-weight: 500;
  display: flex;
  align-items: center;
  gap: 6px;
  position: relative;
  overflow: hidden;
}

.nav-icon {
  font-size: 16px;
  transition: transform 0.3s ease;
}

.nav-btn:hover {
  background: #f0f4f8;
  color: #2c3e50;
  transform: translateY(-1px);
}

.nav-btn:hover .nav-icon {
  transform: scale(1.1);
}

.nav-btn.active {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: #ffffff;
  font-weight: 600;
  border-color: transparent;
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
}

.nav-btn.active .nav-icon {
  animation: bounce 0.5s ease;
}

@keyframes bounce {
  0%, 100% { transform: scale(1); }
  50% { transform: scale(1.2); }
}

/* ACCIONES */
.topbar-actions {
  display: flex;
  gap: 8px;
}

.action-btn {
  width: 36px;
  height: 36px;
  border: 2px solid #e0e0e0;
  background: white;
  border-radius: 8px;
  cursor: pointer;
  font-size: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s ease;
  position: relative;
}

.action-btn:hover {
  background: #f0f4f8;
  border-color: #1e88e5;
  transform: translateY(-1px);
}

.notification-dot {
  position: absolute;
  top: 6px;
  right: 6px;
  width: 8px;
  height: 8px;
  background: #ef5350;
  border-radius: 50%;
  border: 2px solid white;
}
</style>