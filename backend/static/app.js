/**
 * PayrollFlow — Front-End Application Architecture
 * Pure vanilla ES6+ for maximum speed, zero build steps, and robust reliability.
 */

const API_BASE = '/api';

// Application State
const state = {
  token: localStorage.getItem('payroll_token') || null,
  user: JSON.parse(localStorage.getItem('payroll_user') || 'null'),
  currentTab: localStorage.getItem('payroll_tab') || 'dashboard',
  liquidaciones: [],
  activeLiquidacion: null,
  empleados: [],
  tiposHora: [],
  jornadas: [],
  horas: [],
  auditLogs: [],
  reporteConsolidado: null
};

// ================= UTILITIES =================

function formatCOP(amount) {
  if (amount === null || amount === undefined) return '$0 COP';
  const num = typeof amount === 'string' ? parseFloat(amount) : amount;
  return new Intl.NumberFormat('es-CO', {
    style: 'currency',
    currency: 'COP',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0
  }).format(num);
}

function showToast(message, type = 'success') {
  const toast = document.getElementById('toast');
  const inner = document.getElementById('toast-inner');
  const msg = document.getElementById('toast-msg');
  const icon = document.getElementById('toast-icon');

  msg.textContent = message;
  toast.classList.remove('hidden');

  if (type === 'success') {
    inner.className = 'flex items-center space-x-3 px-4 py-3 rounded-xl shadow-xl text-sm font-medium bg-emerald-600 text-white';
    icon.className = 'fa-solid fa-circle-check text-base';
  } else if (type === 'error') {
    inner.className = 'flex items-center space-x-3 px-4 py-3 rounded-xl shadow-xl text-sm font-medium bg-rose-600 text-white';
    icon.className = 'fa-solid fa-circle-exclamation text-base';
  } else {
    inner.className = 'flex items-center space-x-3 px-4 py-3 rounded-xl shadow-xl text-sm font-medium bg-blue-600 text-white';
    icon.className = 'fa-solid fa-circle-info text-base';
  }

  setTimeout(() => {
    toast.classList.add('hidden');
  }, 4000);
}

async function apiRequest(endpoint, options = {}) {
  const headers = options.headers || {};
  if (state.token) {
    headers['Authorization'] = `Bearer ${state.token}`;
  }
  if (!(options.body instanceof FormData) && !headers['Content-Type']) {
    headers['Content-Type'] = 'application/json';
  }

  const response = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers
  });

  if (response.status === 401) {
    logout();
    throw new Error('Sesión expirada o credenciales inválidas');
  }

  const data = await response.json().catch(() => null);

  if (!response.ok) {
    const errorMsg = data?.detail || `Error en la petición (${response.status})`;
    throw new Error(errorMsg);
  }

  return data;
}

// ================= AUTHENTICATION =================

async function login(email, password) {
  try {
    const res = await apiRequest('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password })
    });

    state.token = res.access_token;
    state.user = res.user;
    localStorage.setItem('payroll_token', res.access_token);
    localStorage.setItem('payroll_user', JSON.stringify(res.user));

    // Asignar tab inicial según rol
    if (res.user.rol === 'GERENTE') state.currentTab = 'dashboard';
    else if (res.user.rol === 'ADMIN') state.currentTab = 'liquidar';
    else state.currentTab = 'mi-volante';
    localStorage.setItem('payroll_tab', state.currentTab);

    closeLoginModal();
    updateUI();
    showToast(`Bienvenido/a, ${res.user.nombre_completo}`);
  } catch (err) {
    const errBox = document.getElementById('login-error');
    errBox.textContent = err.message;
    errBox.classList.remove('hidden');
  }
}

function logout() {
  state.token = null;
  state.user = null;
  state.currentTab = 'landing';
  localStorage.removeItem('payroll_token');
  localStorage.removeItem('payroll_user');
  localStorage.removeItem('payroll_tab');
  updateUI();
  showToast('Has cerrado sesión correctamente', 'info');
}

function demoLogin(email) {
  login(email, 'Cambiar123*');
}

function openLoginModal() {
  document.getElementById('modal-login').classList.remove('hidden');
  document.getElementById('login-error').classList.add('hidden');
}

function closeLoginModal() {
  document.getElementById('modal-login').classList.add('hidden');
}

function handleLoginSubmit(e) {
  e.preventDefault();
  const email = document.getElementById('login-email').value;
  const pw = document.getElementById('login-password').value;
  login(email, pw);
}

// ================= NAVIGATION & ROUTING =================

function setTab(tabName) {
  state.currentTab = tabName;
  localStorage.setItem('payroll_tab', tabName);
  renderNav();
  renderView();
}

function renderNav() {
  const navContainer = document.getElementById('nav-links');
  if (!state.user) {
    navContainer.innerHTML = '';
    return;
  }

  let links = [];
  const rol = state.user.rol;

  if (rol === 'GERENTE') {
    links = [
      { id: 'dashboard', label: 'Dashboard Financiero', icon: 'fa-chart-pie' },
      { id: 'liquidaciones', label: 'Aprobación de Nómina', icon: 'fa-file-signature' },
      { id: 'auditoria', label: 'Auditoría', icon: 'fa-clipboard-list' }
    ];
  } else if (rol === 'ADMIN') {
    links = [
      { id: 'liquidar', label: 'Motor de Liquidación', icon: 'fa-bolt' },
      { id: 'horas', label: 'Gestión de Horas', icon: 'fa-clock' },
      { id: 'empleados', label: 'Empleados', icon: 'fa-users' },
      { id: 'tarifas', label: 'Tarifas y Reglas', icon: 'fa-sliders' }
    ];
  } else if (rol === 'OPERARIO') {
    links = [
      { id: 'mi-volante', label: 'Mi Volante de Pago', icon: 'fa-receipt' },
      { id: 'registrar-horas', label: 'Registrar Horas', icon: 'fa-stopwatch' },
      { id: 'mis-horas', label: 'Historial de Horas', icon: 'fa-calendar-days' }
    ];
  }

  navContainer.innerHTML = links.map(l => {
    const active = state.currentTab === l.id;
    return `
      <button onclick="setTab('${l.id}')"
        class="px-3 py-1.5 rounded-lg text-xs font-semibold flex items-center space-x-1.5 transition ${
          active
            ? 'bg-blue-600 text-white shadow-sm'
            : 'text-slate-300 hover:text-white hover:bg-slate-800'
        }">
        <i class="fa-solid ${l.icon}"></i>
        <span>${l.label}</span>
      </button>
    `;
  }).join('');
}

// ================= VIEW RENDERING =================

function updateUI() {
  const userPill = document.getElementById('user-pill');
  const btnLogin = document.getElementById('btn-login-modal');
  const roleBadge = document.getElementById('user-role-badge');
  const userName = document.getElementById('user-name');
  const demoBar = document.getElementById('demo-roles-bar');

  if (state.user) {
    // Ocultar barra de acceso rápido al iniciar sesión
    if (demoBar) demoBar.classList.add('hidden');

    userPill.classList.remove('hidden');
    userPill.classList.add('flex');
    btnLogin.classList.add('hidden');

    userName.textContent = state.user.nombre_completo;
    roleBadge.textContent = state.user.rol;

    if (state.user.rol === 'GERENTE') {
      roleBadge.className = 'text-xs font-bold px-2 py-0.5 rounded-full bg-amber-500/20 text-amber-300 border border-amber-500/30';
      if (!['dashboard', 'liquidaciones', 'auditoria'].includes(state.currentTab)) {
        state.currentTab = 'dashboard';
        localStorage.setItem('payroll_tab', 'dashboard');
      }
    } else if (state.user.rol === 'ADMIN') {
      roleBadge.className = 'text-xs font-bold px-2 py-0.5 rounded-full bg-blue-500/20 text-blue-300 border border-blue-500/30';
      if (!['liquidar', 'horas', 'empleados', 'tarifas'].includes(state.currentTab)) {
        state.currentTab = 'liquidar';
        localStorage.setItem('payroll_tab', 'liquidar');
      }
    } else {
      roleBadge.className = 'text-xs font-bold px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-300 border border-emerald-500/30';
      if (!['mi-volante', 'registrar-horas', 'mis-horas'].includes(state.currentTab)) {
        state.currentTab = 'mi-volante';
        localStorage.setItem('payroll_tab', 'mi-volante');
      }
    }
  } else {
    // Mostrar barra de acceso rápido al cerrar sesión o en modo landing
    if (demoBar) demoBar.classList.remove('hidden');

    userPill.classList.add('hidden');
    userPill.classList.remove('flex');
    btnLogin.classList.remove('hidden');
    state.currentTab = 'landing';
  }

  renderNav();
  renderView();
}

async function renderView() {
  const container = document.getElementById('content-container');

  if (!state.user) {
    container.innerHTML = renderLandingPage();
    return;
  }

  try {
    switch (state.currentTab) {
      case 'dashboard':
        container.innerHTML = await renderGerenteDashboard();
        break;
      case 'liquidaciones':
        container.innerHTML = await renderGerenteLiquidaciones();
        break;
      case 'auditoria':
        container.innerHTML = await renderAuditoriaView();
        break;
      case 'liquidar':
        container.innerHTML = await renderAdminLiquidar();
        break;
      case 'horas':
        container.innerHTML = await renderAdminHoras();
        break;
      case 'empleados':
        container.innerHTML = await renderAdminEmpleados();
        break;
      case 'tarifas':
        container.innerHTML = await renderAdminTarifas();
        break;
      case 'mi-volante':
        container.innerHTML = await renderOperarioVolante();
        break;
      case 'registrar-horas':
        container.innerHTML = await renderOperarioRegistroHoras();
        break;
      case 'mis-horas':
        container.innerHTML = await renderOperarioMisHoras();
        break;
      default:
        container.innerHTML = `<div class="p-8 text-center text-slate-500">Módulo en construcción</div>`;
    }
  } catch (err) {
    container.innerHTML = `
      <div class="bg-rose-50 border border-rose-200 rounded-2xl p-6 text-center max-w-lg mx-auto">
        <i class="fa-solid fa-triangle-exclamation text-rose-500 text-3xl mb-3"></i>
        <h4 class="font-bold text-slate-800">Error al cargar la información</h4>
        <p class="text-xs text-rose-600 mt-1">${err.message}</p>
        <button onclick="renderView()" class="mt-4 px-4 py-2 bg-rose-600 text-white rounded-lg text-xs font-semibold hover:bg-rose-700 transition">Reintentar</button>
      </div>
    `;
  }
}

// ================= LANDING / WELCOME VIEW =================

function renderLandingPage() {
  return `
    <div class="py-12 px-4 max-w-4xl mx-auto text-center space-y-8">
      <div class="inline-flex items-center space-x-2 px-3 py-1 rounded-full bg-blue-50 border border-blue-200 text-blue-700 text-xs font-semibold">
        <i class="fa-solid fa-sparkles"></i>
        <span>Nómina Automatizada con Trazabilidad y Rigor Financiero</span>
      </div>

      <h1 class="text-3xl sm:text-5xl font-extrabold text-slate-900 tracking-tight leading-tight">
        Liquidación de Nómina Segura, Auditable y sin Errores
      </h1>

      <p class="text-base text-slate-600 max-w-2xl mx-auto">
        Plataforma fintech implementada para el sector financiero con PostgreSQL 16 y FastAPI. Cálculo dinámico de horas, escalas de bonificación por hijos no acumulables y segregación estricta de roles.
      </p>

      <div class="grid grid-cols-1 md:grid-cols-3 gap-6 text-left pt-6">
        <div class="bg-white p-6 rounded-2xl shadow-sm border border-slate-200 space-y-3">
          <div class="w-10 h-10 rounded-xl bg-amber-100 text-amber-700 flex items-center justify-center">
            <i class="fa-solid fa-crown text-lg"></i>
          </div>
          <h3 class="font-bold text-slate-800">Gerencia Financiera</h3>
          <p class="text-xs text-slate-500 leading-relaxed">
            KPIs de costo real de empresa (devengado + bonos + aportes patronales), aprobación/rechazo formal de nómina y exportación a PDF/CSV.
          </p>
          <button onclick="demoLogin('gerente@empresa.test')" class="text-xs font-semibold text-amber-600 hover:text-amber-700 flex items-center space-x-1">
            <span>Ingresar como Gerente</span>
            <i class="fa-solid fa-arrow-right text-[10px]"></i>
          </button>
        </div>

        <div class="bg-white p-6 rounded-2xl shadow-sm border border-slate-200 space-y-3">
          <div class="w-10 h-10 rounded-xl bg-blue-100 text-blue-700 flex items-center justify-center">
            <i class="fa-solid fa-shield-halved text-lg"></i>
          </div>
          <h3 class="font-bold text-slate-800">Administración de RRHH</h3>
          <p class="text-xs text-slate-500 leading-relaxed">
            Configuración de tarifas con herencia (Empleado > Perfil > Global), gestión de novedades de horas y ejecución en lote en &lt; 1 seg.
          </p>
          <button onclick="demoLogin('admin01@empresa.test')" class="text-xs font-semibold text-blue-600 hover:text-blue-700 flex items-center space-x-1">
            <span>Ingresar como Admin</span>
            <i class="fa-solid fa-arrow-right text-[10px]"></i>
          </button>
        </div>

        <div class="bg-white p-6 rounded-2xl shadow-sm border border-slate-200 space-y-3">
          <div class="w-10 h-10 rounded-xl bg-emerald-100 text-emerald-700 flex items-center justify-center">
            <i class="fa-solid fa-user-clock text-lg"></i>
          </div>
          <h3 class="font-bold text-slate-800">Portal del Colaborador</h3>
          <p class="text-xs text-slate-500 leading-relaxed">
            Registro ágil de horas trabajadas (≤ 3 clics) y consulta/descarga digital de volantes de pago individuales con desglose exacto.
          </p>
          <button onclick="demoLogin('operario01@empresa.test')" class="text-xs font-semibold text-emerald-600 hover:text-emerald-700 flex items-center space-x-1">
            <span>Ingresar como Operario</span>
            <i class="fa-solid fa-arrow-right text-[10px]"></i>
          </button>
        </div>
      </div>
    </div>
  `;
}

// ================= GERENTE MODULES =================

async function renderGerenteDashboard() {
  const rep = await apiRequest('/reportes/consolidado?anio=2026&mes=9');
  state.reporteConsolidado = rep;

  const t = rep.totales;
  const isPrelim = rep.es_preliminar;

  return `
    <div class="space-y-6">
      
      <!-- Top Title & Controls -->
      <div class="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h2 class="text-2xl font-extrabold text-slate-900 tracking-tight">Dashboard Ejecutivo de Nómina</h2>
          <p class="text-xs text-slate-500 mt-0.5">
            Periodo: Septiembre 2026 · ${isPrelim ? '<span class="text-amber-600 font-semibold">(Vista Preliminar - Pendiente de Aprobación)</span>' : '<span class="text-emerald-600 font-semibold">(Nómina Oficial Aprobada)</span>'}
          </p>
        </div>
        <div class="flex items-center space-x-2">
          <a href="${API_BASE}/reportes/export/csv?anio=2026&mes=9" class="px-3.5 py-2 rounded-xl bg-white border border-slate-200 hover:bg-slate-50 text-slate-700 text-xs font-semibold shadow-sm transition flex items-center space-x-1.5">
            <i class="fa-solid fa-file-csv text-emerald-600"></i>
            <span>Exportar CSV</span>
          </a>
          <a href="${API_BASE}/reportes/export/pdf?anio=2026&mes=9" target="_blank" class="px-3.5 py-2 rounded-xl bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold shadow-sm transition flex items-center space-x-1.5">
            <i class="fa-solid fa-file-pdf"></i>
            <span>Descargar Reporte PDF</span>
          </a>
        </div>
      </div>

      <!-- Financial Metric Cards -->
      <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        
        <div class="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm relative overflow-hidden">
          <div class="flex items-center justify-between mb-2">
            <span class="text-xs font-bold text-slate-500 uppercase tracking-wider">Costo Real Empresa</span>
            <div class="w-8 h-8 rounded-lg bg-blue-100 text-blue-600 flex items-center justify-center text-sm font-bold">
              <i class="fa-solid fa-building-columns"></i>
            </div>
          </div>
          <div class="text-2xl font-extrabold text-slate-900">${formatCOP(t.costo_total_empresa)}</div>
          <div class="text-[11px] text-blue-600 font-semibold mt-1">
            +${t.sobrecosto_patronal_pct}% sobre el neto pagado
          </div>
        </div>

        <div class="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm relative overflow-hidden">
          <div class="flex items-center justify-between mb-2">
            <span class="text-xs font-bold text-slate-500 uppercase tracking-wider">Neto a Empleados</span>
            <div class="w-8 h-8 rounded-lg bg-emerald-100 text-emerald-600 flex items-center justify-center text-sm font-bold">
              <i class="fa-solid fa-money-check-dollar"></i>
            </div>
          </div>
          <div class="text-2xl font-extrabold text-slate-900">${formatCOP(t.neto_pagado)}</div>
          <div class="text-[11px] text-slate-500 mt-1">
            Consignación en cuentas bancarias
          </div>
        </div>

        <div class="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm relative overflow-hidden">
          <div class="flex items-center justify-between mb-2">
            <span class="text-xs font-bold text-slate-500 uppercase tracking-wider">Carga Prestacional</span>
            <div class="w-8 h-8 rounded-lg bg-indigo-100 text-indigo-600 flex items-center justify-center text-sm font-bold">
              <i class="fa-solid fa-umbrella"></i>
            </div>
          </div>
          <div class="text-2xl font-extrabold text-slate-900">${formatCOP(t.costo_patronal)}</div>
          <div class="text-[11px] text-slate-500 mt-1">
            Aportes seguridad social + provisiones
          </div>
        </div>

        <div class="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm relative overflow-hidden">
          <div class="flex items-center justify-between mb-2">
            <span class="text-xs font-bold text-slate-500 uppercase tracking-wider">Total Colaboradores</span>
            <div class="w-8 h-8 rounded-lg bg-purple-100 text-purple-600 flex items-center justify-center text-sm font-bold">
              <i class="fa-solid fa-users"></i>
            </div>
          </div>
          <div class="text-2xl font-extrabold text-slate-900">${t.empleados} colaboradores</div>
          <div class="text-[11px] text-slate-500 mt-1">
            80 Operarios · 4 Admins · 1 Gerente
          </div>
        </div>

      </div>

      <!-- Breakdown By Profile Table -->
      <div class="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
        <div class="px-6 py-4 border-b border-slate-100 flex items-center justify-between">
          <div>
            <h3 class="font-bold text-slate-800 text-sm">Distribución Financiera por Perfil Laboral</h3>
            <p class="text-xs text-slate-400">Desglose exacto generado a partir de la vista <code class="text-blue-600 font-mono">v_costo_nomina_aprobada</code></p>
          </div>
        </div>

        <div class="overflow-x-auto">
          <table class="w-full text-xs text-left">
            <thead class="bg-slate-50 text-slate-600 font-bold uppercase tracking-wider border-b border-slate-100">
              <tr>
                <th class="py-3 px-4">Perfil</th>
                <th class="py-3 px-3 text-center">Colab.</th>
                <th class="py-3 px-4 text-right">Devengado</th>
                <th class="py-3 px-4 text-right">Bonificación Hijos</th>
                <th class="py-3 px-4 text-right">Deducciones 8%</th>
                <th class="py-3 px-4 text-right">Neto Pagado</th>
                <th class="py-3 px-4 text-right">Aportes Patronales</th>
                <th class="py-3 px-4 text-right font-extrabold text-blue-900">Costo Total Empresa</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-slate-100">
              ${rep.perfiles.map(p => `
                <tr class="hover:bg-slate-50 transition">
                  <td class="py-3.5 px-4 font-bold text-slate-800">${p.perfil}</td>
                  <td class="py-3.5 px-3 text-center font-semibold text-slate-600">${p.empleados}</td>
                  <td class="py-3.5 px-4 text-right font-medium text-slate-700">${formatCOP(p.devengado)}</td>
                  <td class="py-3.5 px-4 text-right font-medium text-emerald-600">+${formatCOP(p.bonificaciones)}</td>
                  <td class="py-3.5 px-4 text-right font-medium text-rose-600">-${formatCOP(p.deducciones_empleado)}</td>
                  <td class="py-3.5 px-4 text-right font-bold text-slate-900">${formatCOP(p.neto_pagado_empleados)}</td>
                  <td class="py-3.5 px-4 text-right font-medium text-indigo-600">${formatCOP(p.aportes_patronales + p.prestaciones)}</td>
                  <td class="py-3.5 px-4 text-right font-extrabold text-blue-900">${formatCOP(p.costo_total_empresa)}</td>
                </tr>
              `).join('')}
            </tbody>
            <tfoot class="bg-slate-100/70 font-bold border-t-2 border-slate-200">
              <tr>
                <td class="py-3.5 px-4 text-slate-900 uppercase">Total Consolidado</td>
                <td class="py-3.5 px-3 text-center text-slate-900">${t.empleados}</td>
                <td class="py-3.5 px-4 text-right text-slate-900">${formatCOP(t.devengado)}</td>
                <td class="py-3.5 px-4 text-right text-emerald-700">+${formatCOP(t.bonificaciones)}</td>
                <td class="py-3.5 px-4 text-right text-rose-700">-${formatCOP(t.deducciones_empleado)}</td>
                <td class="py-3.5 px-4 text-right text-slate-900">${formatCOP(t.neto_pagado)}</td>
                <td class="py-3.5 px-4 text-right text-indigo-700">${formatCOP(t.costo_patronal)}</td>
                <td class="py-3.5 px-4 text-right font-extrabold text-blue-900 text-sm">${formatCOP(t.costo_total_empresa)}</td>
              </tr>
            </tfoot>
          </table>
        </div>
      </div>

    </div>
  `;
}

async function renderGerenteLiquidaciones() {
  const liquidaciones = await apiRequest('/liquidaciones');
  state.liquidaciones = liquidaciones;

  return `
    <div class="space-y-6">
      <div class="flex items-center justify-between">
        <div>
          <h2 class="text-2xl font-extrabold text-slate-900 tracking-tight">Gestión y Aprobación de Nómina</h2>
          <p class="text-xs text-slate-500 mt-0.5">Como Gerente, tu autorización formal es obligatoria para el desembolso.</p>
        </div>
      </div>

      <div class="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
        <div class="overflow-x-auto">
          <table class="w-full text-xs text-left">
            <thead class="bg-slate-50 text-slate-600 font-bold uppercase tracking-wider border-b border-slate-100">
              <tr>
                <th class="py-3 px-4">Periodo</th>
                <th class="py-3 px-4">Estado</th>
                <th class="py-3 px-4 text-right">Total Nómina (Neto)</th>
                <th class="py-3 px-4">Ejecutado Por</th>
                <th class="py-3 px-4">Fecha Corrida</th>
                <th class="py-3 px-4 text-center">Acciones Gerenciales</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-slate-100">
              ${liquidaciones.length === 0 ? `
                <tr><td colspan="6" class="text-center py-8 text-slate-400">No hay liquidaciones registradas en el sistema.</td></tr>
              ` : liquidaciones.map(l => {
                let statusBadge = '';
                if (l.estado === 'APROBADA') {
                  statusBadge = '<span class="px-2.5 py-1 rounded-full bg-emerald-100 text-emerald-800 font-bold text-[10px]">APROBADA</span>';
                } else if (l.estado === 'LIQUIDADA') {
                  statusBadge = '<span class="px-2.5 py-1 rounded-full bg-amber-100 text-amber-800 font-bold text-[10px]">PENDIENTE REVISIÓN</span>';
                } else if (l.estado === 'RECHAZADA') {
                  statusBadge = '<span class="px-2.5 py-1 rounded-full bg-rose-100 text-rose-800 font-bold text-[10px]">RECHAZADA</span>';
                } else {
                  statusBadge = '<span class="px-2.5 py-1 rounded-full bg-slate-100 text-slate-600 font-bold text-[10px]">ANULADA</span>';
                }

                return `
                  <tr class="hover:bg-slate-50 transition">
                    <td class="py-3.5 px-4 font-bold text-slate-800 text-sm">${l.anio} - Mes ${String(l.mes).padStart(2, '0')}</td>
                    <td class="py-3.5 px-4">${statusBadge}</td>
                    <td class="py-3.5 px-4 text-right font-extrabold text-slate-900">${formatCOP(l.total_nomina)}</td>
                    <td class="py-3.5 px-4 text-slate-600">${l.ejecutada_por_nombre || 'Admin'}</td>
                    <td class="py-3.5 px-4 text-slate-400 text-[11px]">${new Date(l.ejecutada_en).toLocaleString()}</td>
                    <td class="py-3.5 px-4 text-center space-x-1">
                      <button onclick="verDetalleLiquidacionModal(${l.id})" class="px-2 py-1 rounded bg-slate-100 hover:bg-slate-200 text-slate-700 font-semibold text-[11px] transition">
                        <i class="fa-solid fa-eye"></i> Detalle
                      </button>

                      ${l.estado === 'LIQUIDADA' ? `
                        <button onclick="aprobarLiquidacionDirecto(${l.id})" class="px-2 py-1 rounded bg-emerald-600 hover:bg-emerald-700 text-white font-semibold text-[11px] transition shadow-sm">
                          <i class="fa-solid fa-check"></i> Aprobar
                        </button>
                        <button onclick="abrirModalRechazo(${l.id})" class="px-2 py-1 rounded bg-rose-600 hover:bg-rose-700 text-white font-semibold text-[11px] transition shadow-sm">
                          <i class="fa-solid fa-xmark"></i> Rechazar
                        </button>
                      ` : ''}
                    </td>
                  </tr>
                `;
              }).join('')}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  `;
}

async function renderAuditoriaView() {
  const logs = await apiRequest('/reportes/auditoria?limit=100');

  return `
    <div class="space-y-6">
      <div>
        <h2 class="text-2xl font-extrabold text-slate-900 tracking-tight">Registro de Auditoría y Trazabilidad (O3)</h2>
        <p class="text-xs text-slate-500 mt-0.5">Toda operación crítica en la base de datos queda asentada de forma inmutable.</p>
      </div>

      <div class="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
        <div class="overflow-x-auto">
          <table class="w-full text-xs text-left">
            <thead class="bg-slate-50 text-slate-600 font-bold uppercase tracking-wider border-b border-slate-100">
              <tr>
                <th class="py-3 px-4">Fecha y Hora</th>
                <th class="py-3 px-4">Usuario</th>
                <th class="py-3 px-4">Acción</th>
                <th class="py-3 px-4">Entidad</th>
                <th class="py-3 px-4">ID</th>
                <th class="py-3 px-4">Detalles (JSON)</th>
                <th class="py-3 px-4">IP</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-slate-100 font-mono text-[11px]">
              ${logs.map(log => `
                <tr class="hover:bg-slate-50 transition">
                  <td class="py-3 px-4 text-slate-500 whitespace-nowrap">${log.creado_en}</td>
                  <td class="py-3 px-4 font-bold text-slate-700">${log.usuario_email || 'Sistema'}</td>
                  <td class="py-3 px-4">
                    <span class="px-2 py-0.5 rounded bg-blue-100 text-blue-800 font-bold">${log.accion}</span>
                  </td>
                  <td class="py-3 px-4 text-slate-600">${log.entidad}</td>
                  <td class="py-3 px-4 text-slate-500">${log.entidad_id || '-'}</td>
                  <td class="py-3 px-4 text-slate-600 max-w-xs truncate" title='${JSON.stringify(log.datos || {})}'>
                    ${log.datos ? JSON.stringify(log.datos) : '-'}
                  </td>
                  <td class="py-3 px-4 text-slate-400">${log.ip || '127.0.0.1'}</td>
                </tr>
              `).join('')}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  `;
}

// ================= ADMIN MODULES =================

async function renderAdminLiquidar() {
  const liquidaciones = await apiRequest('/liquidaciones');
  state.liquidaciones = liquidaciones;

  return `
    <div class="space-y-6">
      
      <!-- Action Banner -->
      <div class="bg-gradient-to-r from-blue-900 to-indigo-900 rounded-2xl p-6 text-white shadow-lg flex flex-col md:flex-row items-start md:items-center justify-between gap-6">
        <div class="space-y-1">
          <div class="inline-flex items-center space-x-1 px-2.5 py-0.5 rounded-full bg-blue-500/20 text-blue-200 border border-blue-400/30 text-[11px] font-bold">
            <i class="fa-solid fa-microchip"></i>
            <span>Motor de Cálculo Automático en PostgreSQL & Python</span>
          </div>
          <h2 class="text-2xl font-bold">Disparar Corrida de Nómina</h2>
          <p class="text-xs text-blue-200/80 max-w-xl">
            Liquida automáticamente las tarifas dinámicas por perfil, horas aprobadas, subsidios por hijos no acumulables y retenciones legales para todos los 85 colaboradores.
          </p>
        </div>

        <div class="bg-white/10 backdrop-blur-md p-4 rounded-xl border border-white/20 flex flex-wrap items-center gap-3">
          <div>
            <label class="block text-[11px] text-blue-200 font-semibold mb-1">Año</label>
            <input type="number" id="run-anio" value="2026" min="2020" max="2030" class="w-20 px-2.5 py-1.5 text-xs text-slate-900 rounded-lg outline-none font-bold">
          </div>
          <div>
            <label class="block text-[11px] text-blue-200 font-semibold mb-1">Mes</label>
            <select id="run-mes" class="px-2.5 py-1.5 text-xs text-slate-900 rounded-lg outline-none font-bold">
              <option value="9" selected>09 - Septiembre</option>
              <option value="10">10 - Octubre</option>
              <option value="11">11 - Noviembre</option>
              <option value="12">12 - Diciembre</option>
            </select>
          </div>
          <button onclick="ejecutarLiquidacionAction()" class="mt-4 sm:mt-0 px-4 py-2 rounded-lg bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-extrabold text-xs transition shadow-md flex items-center space-x-2">
            <i class="fa-solid fa-play"></i>
            <span>Calcular Nómina</span>
          </button>
        </div>
      </div>

      <!-- History of Runs Table -->
      <div class="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
        <div class="px-6 py-4 border-b border-slate-100 flex items-center justify-between">
          <h3 class="font-bold text-slate-800 text-sm">Historial de Corridas de Liquidación</h3>
        </div>

        <div class="overflow-x-auto">
          <table class="w-full text-xs text-left">
            <thead class="bg-slate-50 text-slate-600 font-bold uppercase tracking-wider border-b border-slate-100">
              <tr>
                <th class="py-3 px-4">ID</th>
                <th class="py-3 px-4">Periodo</th>
                <th class="py-3 px-4">Estado</th>
                <th class="py-3 px-4 text-right">Total Nómina</th>
                <th class="py-3 px-4">Ejecutado Por</th>
                <th class="py-3 px-4">Fecha</th>
                <th class="py-3 px-4 text-center">Acciones</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-slate-100">
              ${liquidaciones.map(l => `
                <tr class="hover:bg-slate-50 transition">
                  <td class="py-3.5 px-4 font-mono font-bold text-slate-600">#${l.id}</td>
                  <td class="py-3.5 px-4 font-bold text-slate-900">${l.anio} - Mes ${String(l.mes).padStart(2, '0')}</td>
                  <td class="py-3.5 px-4">
                    <span class="px-2 py-0.5 rounded-full text-[10px] font-bold ${
                      l.estado === 'APROBADA' ? 'bg-emerald-100 text-emerald-800' :
                      l.estado === 'LIQUIDADA' ? 'bg-amber-100 text-amber-800' :
                      l.estado === 'RECHAZADA' ? 'bg-rose-100 text-rose-800' :
                      'bg-slate-100 text-slate-600'
                    }">${l.estado}</span>
                  </td>
                  <td class="py-3.5 px-4 text-right font-extrabold text-slate-900">${formatCOP(l.total_nomina)}</td>
                  <td class="py-3.5 px-4 text-slate-600">${l.ejecutada_por_nombre || 'Admin'}</td>
                  <td class="py-3.5 px-4 text-slate-400 text-[11px]">${new Date(l.ejecutada_en).toLocaleDateString()}</td>
                  <td class="py-3.5 px-4 text-center space-x-1">
                    <button onclick="verDetalleLiquidacionModal(${l.id})" class="px-2 py-1 rounded bg-slate-100 hover:bg-slate-200 text-slate-700 font-semibold text-[11px] transition">
                      <i class="fa-solid fa-list-check"></i> Desglose
                    </button>
                    ${l.estado !== 'ANULADA' ? `
                      <button onclick="abrirModalAnular(${l.id})" class="px-2 py-1 rounded bg-rose-50 hover:bg-rose-100 text-rose-700 border border-rose-200 font-semibold text-[11px] transition">
                        <i class="fa-solid fa-ban"></i> Anular
                      </button>
                    ` : ''}
                  </td>
                </tr>
              `).join('')}
            </tbody>
          </table>
        </div>
      </div>

    </div>
  `;
}

async function renderAdminHoras() {
  const horas = await apiRequest('/horas?fecha_desde=2026-09-01&fecha_hasta=2026-09-30');
  state.horas = horas;

  return `
    <div class="space-y-6">
      <div class="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h2 class="text-2xl font-extrabold text-slate-900 tracking-tight">Aprobación y Gestión de Horas</h2>
          <p class="text-xs text-slate-500 mt-0.5">Solo las horas con estado APROBADA entran al cálculo del motor de nómina (RF-10).</p>
        </div>

        <button onclick="aprobarHorasBatchAction()" class="px-3.5 py-2 rounded-xl bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold shadow-sm transition flex items-center space-x-1.5">
          <i class="fa-solid fa-check-double"></i>
          <span>Aprobar Todo el Mes Pendiente</span>
        </button>
      </div>

      <div class="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
        <div class="overflow-x-auto">
          <table class="w-full text-xs text-left">
            <thead class="bg-slate-50 text-slate-600 font-bold uppercase tracking-wider border-b border-slate-100">
              <tr>
                <th class="py-3 px-4">Fecha</th>
                <th class="py-3 px-4">Empleado</th>
                <th class="py-3 px-4">Tipo de Hora</th>
                <th class="py-3 px-4">Jornada</th>
                <th class="py-3 px-4 text-center">Horas</th>
                <th class="py-3 px-4">Estado</th>
                <th class="py-3 px-4 text-center">Acción</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-slate-100">
              ${horas.slice(0, 50).map(h => `
                <tr class="hover:bg-slate-50 transition">
                  <td class="py-3 px-4 font-mono font-medium text-slate-700">${h.fecha}</td>
                  <td class="py-3 px-4 font-bold text-slate-800">${h.empleado_nombre} <span class="text-[10px] text-slate-400 font-normal">(${h.documento})</span></td>
                  <td class="py-3 px-4 font-semibold text-blue-700">${h.tipo_hora_nombre} (${h.tipo_hora_codigo})</td>
                  <td class="py-3 px-4 text-slate-600">${h.jornada_nombre}</td>
                  <td class="py-3 px-4 text-center font-bold text-slate-900">${h.horas} h</td>
                  <td class="py-3 px-4">
                    <span class="px-2 py-0.5 rounded-full text-[10px] font-bold ${
                      h.estado === 'APROBADA' ? 'bg-emerald-100 text-emerald-800' :
                      h.estado === 'PENDIENTE' ? 'bg-amber-100 text-amber-800' :
                      'bg-rose-100 text-rose-800'
                    }">${h.estado}</span>
                  </td>
                  <td class="py-3 px-4 text-center">
                    ${h.estado === 'PENDIENTE' ? `
                      <button onclick="aprobarHoraIndividual(${h.id})" class="px-2 py-1 rounded bg-emerald-600 hover:bg-emerald-700 text-white font-semibold text-[10px] transition">
                        Aprobar
                      </button>
                    ` : '<span class="text-slate-400 text-[10px]">-</span>'}
                  </td>
                </tr>
              `).join('')}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  `;
}

async function renderAdminEmpleados() {
  const empleados = await apiRequest('/empleados');
  state.empleados = empleados;

  return `
    <div class="space-y-6">
      <div class="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h2 class="text-2xl font-extrabold text-slate-900 tracking-tight">Directorio de Colaboradores (85 Empleados)</h2>
          <p class="text-xs text-slate-500 mt-0.5">Gestión de datos salariales, hijos a cargo y perfil laboral.</p>
        </div>

        <button onclick="abrirModalNuevoEmpleado()" class="px-3.5 py-2 rounded-xl bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold shadow-sm transition flex items-center space-x-1.5">
          <i class="fa-solid fa-user-plus"></i>
          <span>Registrar Empleado</span>
        </button>
      </div>

      <div class="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
        <div class="overflow-x-auto">
          <table class="w-full text-xs text-left">
            <thead class="bg-slate-50 text-slate-600 font-bold uppercase tracking-wider border-b border-slate-100">
              <tr>
                <th class="py-3 px-4">ID</th>
                <th class="py-3 px-4">Documento</th>
                <th class="py-3 px-4">Nombres y Apellidos</th>
                <th class="py-3 px-4">Perfil</th>
                <th class="py-3 px-4 text-right">Salario Base</th>
                <th class="py-3 px-4 text-center"># Hijos</th>
                <th class="py-3 px-4">Correo</th>
                <th class="py-3 px-4 text-center">Acciones</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-slate-100">
              ${empleados.map(e => `
                <tr class="hover:bg-slate-50 transition">
                  <td class="py-3 px-4 font-mono text-slate-400">#${e.id}</td>
                  <td class="py-3 px-4 font-mono font-medium text-slate-700">${e.documento}</td>
                  <td class="py-3 px-4 font-bold text-slate-900">${e.nombres} ${e.apellidos}</td>
                  <td class="py-3 px-4 font-semibold text-blue-700">${e.perfil_nombre}</td>
                  <td class="py-3 px-4 text-right font-medium text-slate-800">${formatCOP(e.salario_base)}</td>
                  <td class="py-3 px-4 text-center">
                    <span class="px-2 py-0.5 rounded-full bg-slate-100 font-bold text-slate-700">${e.num_hijos}</span>
                  </td>
                  <td class="py-3 px-4 text-slate-500">${e.email || '-'}</td>
                  <td class="py-3 px-4 text-center">
                    <button onclick="abrirModalEditarEmpleado(${JSON.stringify(e).replace(/"/g, '&quot;')})" class="px-2 py-1 rounded bg-slate-100 hover:bg-slate-200 text-slate-700 font-semibold text-[10px] transition">
                      <i class="fa-solid fa-pen"></i> Editar
                    </button>
                  </td>
                </tr>
              `).join('')}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  `;
}

async function renderAdminTarifas() {
  const tarifas = await apiRequest('/catalogos/tarifas');
  const tiposHora = await apiRequest('/catalogos/tipos-hora');
  const deducciones = await apiRequest('/catalogos/config-deducciones');

  return `
    <div class="space-y-6">
      <div>
        <h2 class="text-2xl font-extrabold text-slate-900 tracking-tight">Parametrización de Tarifas y Reglas (RF-08, O5)</h2>
        <p class="text-xs text-slate-500 mt-0.5">Herencia de tarifas: Empleado > Perfil > Global. Modificar sin recompilar código.</p>
      </div>

      <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
        
        <!-- Multiplicadores de Tipos de Hora -->
        <div class="bg-white rounded-2xl border border-slate-200 shadow-sm p-6 space-y-4">
          <h3 class="font-bold text-slate-800 text-sm flex items-center space-x-2">
            <i class="fa-solid fa-hourglass-half text-blue-600"></i>
            <span>Multiplicadores por Tipo de Hora (RN-04)</span>
          </h3>
          <table class="w-full text-xs text-left">
            <thead class="bg-slate-50 text-slate-500 font-bold border-b border-slate-100">
              <tr>
                <th class="py-2 px-3">Código</th>
                <th class="py-2 px-3">Descripción</th>
                <th class="py-2 px-3 text-right">Multiplicador</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-slate-100">
              ${tiposHora.map(th => `
                <tr>
                  <td class="py-2 px-3 font-mono font-bold text-blue-700">${th.codigo}</td>
                  <td class="py-2 px-3 font-medium text-slate-700">${th.nombre}</td>
                  <td class="py-2 px-3 text-right font-extrabold text-slate-900">${parseFloat(th.multiplicador).toFixed(3)}x</td>
                </tr>
              `).join('')}
            </tbody>
          </table>
        </div>

        <!-- Deducciones de Ley -->
        <div class="bg-white rounded-2xl border border-slate-200 shadow-sm p-6 space-y-4">
          <h3 class="font-bold text-slate-800 text-sm flex items-center space-x-2">
            <i class="fa-solid fa-scale-balanced text-emerald-600"></i>
            <span>Deducciones de Ley Vigentes (RN-02)</span>
          </h3>
          <table class="w-full text-xs text-left">
            <thead class="bg-slate-50 text-slate-500 font-bold border-b border-slate-100">
              <tr>
                <th class="py-2 px-3">Concepto</th>
                <th class="py-2 px-3 text-right">Porcentaje</th>
                <th class="py-2 px-3">Vigencia Desde</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-slate-100">
              ${deducciones.map(d => `
                <tr>
                  <td class="py-2 px-3 font-bold text-slate-800">${d.concepto} (Empleado)</td>
                  <td class="py-2 px-3 text-right font-extrabold text-rose-600">${d.porcentaje}%</td>
                  <td class="py-2 px-3 text-slate-500 font-mono text-[11px]">${d.vigente_desde}</td>
                </tr>
              `).join('')}
            </tbody>
          </table>
        </div>

      </div>

      <!-- Tarifas Base Vigentes -->
      <div class="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
        <div class="px-6 py-4 border-b border-slate-100 flex items-center justify-between">
          <h3 class="font-bold text-slate-800 text-sm">Tarifas Base por Hora (Herencia Activa)</h3>
        </div>
        <div class="overflow-x-auto">
          <table class="w-full text-xs text-left">
            <thead class="bg-slate-50 text-slate-600 font-bold uppercase tracking-wider border-b border-slate-100">
              <tr>
                <th class="py-3 px-4">Alcance</th>
                <th class="py-3 px-4">Aplica A</th>
                <th class="py-3 px-4 text-right">Tarifa Base por Hora</th>
                <th class="py-3 px-4">Vigencia</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-slate-100">
              ${tarifas.map(t => `
                <tr class="hover:bg-slate-50 transition">
                  <td class="py-3 px-4">
                    <span class="px-2 py-0.5 rounded font-mono font-bold text-[10px] ${
                      t.alcance === 'EMPLEADO' ? 'bg-purple-100 text-purple-800' :
                      t.alcance === 'PERFIL' ? 'bg-blue-100 text-blue-800' :
                      'bg-slate-100 text-slate-700'
                    }">${t.alcance}</span>
                  </td>
                  <td class="py-3 px-4 font-bold text-slate-800">
                    ${t.empleado_nombre ? `Empleado: ${t.empleado_nombre}` : t.perfil_nombre ? `Perfil: ${t.perfil_nombre}` : 'Todos los colaboradores (Global)'}
                  </td>
                  <td class="py-3 px-4 text-right font-extrabold text-slate-900">${formatCOP(t.tarifa_base)} / hora</td>
                  <td class="py-3 px-4 text-slate-500 font-mono text-[11px]">${t.vigente_desde} ${t.vigente_hasta ? 'hasta ' + t.vigente_hasta : '(Indefinido)'}</td>
                </tr>
              `).join('')}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  `;
}

// ================= OPERARIO MODULES =================

async function renderOperarioVolante() {
  try {
    const v = await apiRequest('/reportes/me/volantes/2026/9');

    return `
      <div class="max-w-3xl mx-auto space-y-6">
        
        <div class="flex items-center justify-between">
          <div>
            <h2 class="text-2xl font-extrabold text-slate-900 tracking-tight">Mi Desprendible de Pago</h2>
            <p class="text-xs text-slate-500 mt-0.5">Liquidación de Nómina correspondiente a Septiembre 2026</p>
          </div>

          <a href="${API_BASE}/reportes/me/volantes/2026/9/pdf" target="_blank" class="px-4 py-2 rounded-xl bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold shadow-sm transition flex items-center space-x-1.5">
            <i class="fa-solid fa-download"></i>
            <span>Descargar Colilla (PDF)</span>
          </a>
        </div>

        <!-- Voucher Paper UI -->
        <div class="bg-white rounded-3xl border border-slate-200 shadow-xl overflow-hidden p-6 sm:p-8 space-y-6">
          
          <!-- Voucher Header -->
          <div class="border-b border-slate-100 pb-5 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
            <div>
              <span class="text-xs font-extrabold tracking-wider text-blue-600 uppercase">PAYROLLFLOW FINANCIERA S.A.S.</span>
              <h3 class="text-xl font-black text-slate-900">Volante Individual de Nómina</h3>
              <p class="text-xs text-slate-400">NIT: 901.458.789-0 · Periodo: 09 / 2026</p>
            </div>
            <div class="text-right sm:text-right">
              <span class="px-3 py-1 rounded-full text-xs font-bold ${
                v.estado === 'APROBADA' ? 'bg-emerald-100 text-emerald-800' : 'bg-amber-100 text-amber-800'
              }">${v.estado}</span>
            </div>
          </div>

          <!-- Employee Contract Details -->
          <div class="grid grid-cols-2 sm:grid-cols-4 gap-4 p-4 rounded-2xl bg-slate-50 border border-slate-100 text-xs">
            <div>
              <span class="text-slate-400 font-medium">Colaborador:</span>
              <div class="font-bold text-slate-800 text-sm mt-0.5">${v.nombres} ${v.apellidos}</div>
            </div>
            <div>
              <span class="text-slate-400 font-medium">Cédula:</span>
              <div class="font-bold text-slate-800 text-sm mt-0.5">${v.documento}</div>
            </div>
            <div>
              <span class="text-slate-400 font-medium">Cargo:</span>
              <div class="font-bold text-blue-700 text-sm mt-0.5">${v.perfil}</div>
            </div>
            <div>
              <span class="text-slate-400 font-medium">Hijos Registrados:</span>
              <div class="font-bold text-slate-800 text-sm mt-0.5">${v.num_hijos}</div>
            </div>
          </div>

          <!-- Concept Breakdown Table -->
          <div class="space-y-2">
            <h4 class="text-xs font-bold uppercase tracking-wider text-slate-500">Desglose de Conceptos</h4>
            <div class="border border-slate-100 rounded-xl overflow-hidden">
              <table class="w-full text-xs text-left">
                <thead class="bg-slate-50 text-slate-600 font-bold border-b border-slate-100">
                  <tr>
                    <th class="py-2.5 px-3">Tipo</th>
                    <th class="py-2.5 px-3">Concepto</th>
                    <th class="py-2.5 px-3 text-center">Cant.</th>
                    <th class="py-2.5 px-3 text-right">Vlr. Unitario</th>
                    <th class="py-2.5 px-3 text-right">Total</th>
                  </tr>
                </thead>
                <tbody class="divide-y divide-slate-100">
                  ${v.conceptos.map(c => `
                    <tr class="hover:bg-slate-50/50">
                      <td class="py-2 px-3">
                        <span class="font-semibold text-[10px] ${
                          c.tipo === 'DEDUCCION' ? 'text-rose-600' : 'text-emerald-600'
                        }">${c.tipo}</span>
                      </td>
                      <td class="py-2 px-3 font-medium text-slate-800">${c.concepto}</td>
                      <td class="py-2 px-3 text-center text-slate-500">${c.cantidad}</td>
                      <td class="py-2 px-3 text-right text-slate-600">${formatCOP(c.valor_unitario)}</td>
                      <td class="py-2 px-3 text-right font-bold ${
                        c.tipo === 'DEDUCCION' ? 'text-rose-600' : 'text-slate-900'
                      }">${c.tipo === 'DEDUCCION' ? '-' : ''}${formatCOP(c.valor_total)}</td>
                    </tr>
                  `).join('')}
                </tbody>
              </table>
            </div>
          </div>

          <!-- Net Payout Callout -->
          <div class="bg-gradient-to-r from-emerald-500 to-teal-600 rounded-2xl p-6 text-white flex flex-col sm:flex-row items-center justify-between gap-4 shadow-lg">
            <div>
              <span class="text-xs font-bold text-emerald-100 uppercase tracking-wider">Total a Consignar en Cuenta (Neto)</span>
              <div class="text-3xl font-black">${formatCOP(v.neto)}</div>
            </div>
            <div class="text-xs text-right text-emerald-100">
              <div>Devengado + Bonificación: ${formatCOP(v.devengado + v.bonificacion)}</div>
              <div>Total Deducciones de Ley: ${formatCOP(v.deduccion_salud + v.deduccion_pension)}</div>
            </div>
          </div>

        </div>

      </div>
    `;
  } catch (err) {
    return `
      <div class="bg-white rounded-2xl border border-slate-200 p-8 text-center max-w-lg mx-auto space-y-3">
        <i class="fa-solid fa-clock-rotate-left text-blue-500 text-3xl"></i>
        <h3 class="font-bold text-slate-800">Volante en proceso</h3>
        <p class="text-xs text-slate-500">Aún no hay liquidación generada para el periodo Septiembre 2026. Comunícate con RRHH.</p>
      </div>
    `;
  }
}

async function renderOperarioRegistroHoras() {
  const tiposHora = await apiRequest('/catalogos/tipos-hora');
  const jornadas = await apiRequest('/catalogos/jornadas');

  return `
    <div class="max-w-xl mx-auto space-y-6">
      <div>
        <h2 class="text-2xl font-extrabold text-slate-900 tracking-tight">Registro Rápido de Horas</h2>
        <p class="text-xs text-slate-500 mt-0.5">Ingresa tus horas trabajadas en ≤ 3 clics según el requerimiento de usabilidad.</p>
      </div>

      <div class="bg-white rounded-3xl border border-slate-200 shadow-sm p-6 sm:p-8">
        <form onsubmit="handleRegistroHorasSubmit(event)" class="space-y-4">
          
          <div>
            <label class="block text-xs font-semibold text-slate-700 mb-1">Fecha Laborada</label>
            <input type="date" id="hora-fecha" required value="2026-10-06"
              class="w-full px-3 py-2 text-sm rounded-xl border border-slate-300 focus:ring-2 focus:ring-blue-500 outline-none transition">
          </div>

          <div class="grid grid-cols-2 gap-4">
            <div>
              <label class="block text-xs font-semibold text-slate-700 mb-1">Tipo de Hora</label>
              <select id="hora-tipo" class="w-full px-3 py-2 text-sm rounded-xl border border-slate-300 focus:ring-2 focus:ring-blue-500 outline-none transition font-medium">
                ${tiposHora.map(th => `
                  <option value="${th.id}">${th.nombre} (${th.multiplicador}x)</option>
                `).join('')}
              </select>
            </div>

            <div>
              <label class="block text-xs font-semibold text-slate-700 mb-1">Jornada</label>
              <select id="hora-jornada" class="w-full px-3 py-2 text-sm rounded-xl border border-slate-300 focus:ring-2 focus:ring-blue-500 outline-none transition font-medium">
                ${jornadas.map(j => `
                  <option value="${j.id}">${j.nombre} (${j.hora_inicio} - ${j.hora_fin})</option>
                `).join('')}
              </select>
            </div>
          </div>

          <div>
            <label class="block text-xs font-semibold text-slate-700 mb-1">Cantidad de Horas (0 a 24)</label>
            <input type="number" id="hora-cantidad" required min="1" max="24" step="1" value="8"
              class="w-full px-3 py-2 text-sm rounded-xl border border-slate-300 focus:ring-2 focus:ring-blue-500 outline-none transition font-bold">
          </div>

          <button type="submit" class="w-full py-3 rounded-xl bg-blue-600 hover:bg-blue-700 text-white font-bold text-sm shadow-md transition flex items-center justify-center space-x-2 mt-2">
            <i class="fa-solid fa-paper-plane"></i>
            <span>Registrar Novedad de Horas</span>
          </button>
        </form>
      </div>
    </div>
  `;
}

async function renderOperarioMisHoras() {
  const horas = await apiRequest('/horas');

  return `
    <div class="space-y-6">
      <div>
        <h2 class="text-2xl font-extrabold text-slate-900 tracking-tight">Historial de Mis Horas Registradas</h2>
        <p class="text-xs text-slate-500 mt-0.5">Tus horas son revisadas y aprobadas por Administración de RRHH.</p>
      </div>

      <div class="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
        <div class="overflow-x-auto">
          <table class="w-full text-xs text-left">
            <thead class="bg-slate-50 text-slate-600 font-bold uppercase tracking-wider border-b border-slate-100">
              <tr>
                <th class="py-3 px-4">Fecha</th>
                <th class="py-3 px-4">Tipo de Hora</th>
                <th class="py-3 px-4">Jornada</th>
                <th class="py-3 px-4 text-center">Horas</th>
                <th class="py-3 px-4">Estado</th>
                <th class="py-3 px-4">Aprobado Por</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-slate-100">
              ${horas.length === 0 ? `
                <tr><td colspan="6" class="text-center py-8 text-slate-400">Aún no has registrado horas en este periodo.</td></tr>
              ` : horas.map(h => `
                <tr class="hover:bg-slate-50 transition">
                  <td class="py-3 px-4 font-mono font-medium text-slate-700">${h.fecha}</td>
                  <td class="py-3 px-4 font-bold text-blue-700">${h.tipo_hora_nombre}</td>
                  <td class="py-3 px-4 text-slate-600">${h.jornada_nombre}</td>
                  <td class="py-3 px-4 text-center font-bold text-slate-900">${h.horas} h</td>
                  <td class="py-3 px-4">
                    <span class="px-2 py-0.5 rounded-full text-[10px] font-bold ${
                      h.estado === 'APROBADA' ? 'bg-emerald-100 text-emerald-800' :
                      h.estado === 'PENDIENTE' ? 'bg-amber-100 text-amber-800' :
                      'bg-rose-100 text-rose-800'
                    }">${h.estado}</span>
                  </td>
                  <td class="py-3 px-4 text-slate-500 text-[11px]">${h.aprobado_por_nombre || 'En revisión'}</td>
                </tr>
              `).join('')}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  `;
}

// ================= ACTIONS & EVENT HANDLERS =================

async function ejecutarLiquidacionAction() {
  const anio = parseInt(document.getElementById('run-anio').value);
  const mes = parseInt(document.getElementById('run-mes').value);

  try {
    const res = await apiRequest('/liquidaciones', {
      method: 'POST',
      body: JSON.stringify({ anio, mes })
    });
    showToast(`¡Nómina calculada! Total: ${formatCOP(res.total_nomina)} (${res.total_empleados} colaboradores)`);
    setTab('liquidar');
  } catch (err) {
    showToast(err.message, 'error');
  }
}

async function aprobarLiquidacionDirecto(id) {
  if (!confirm('¿Confirmas la aprobación formal de la nómina para este periodo?')) return;
  try {
    await apiRequest(`/liquidaciones/${id}/aprobar`, { method: 'PATCH' });
    showToast('Liquidación aprobada formalmente');
    renderView();
  } catch (err) {
    showToast(err.message, 'error');
  }
}

function abrirModalRechazo(id) {
  const modal = document.getElementById('generic-modal');
  const content = document.getElementById('generic-modal-content');

  content.innerHTML = `
    <h3 class="text-lg font-bold text-slate-900 mb-2">Rechazar Liquidación de Nómina</h3>
    <p class="text-xs text-slate-500 mb-4">Indica el motivo por el cual devuelves la nómina a RRHH:</p>
    <textarea id="motivo-rechazo" rows="3" placeholder="Ej: Discrepancia en horas extra de operarios..."
      class="w-full p-3 text-xs rounded-xl border border-slate-300 outline-none focus:ring-2 focus:ring-rose-500 mb-4"></textarea>
    <div class="flex justify-end space-x-2">
      <button onclick="cerrarGenericModal()" class="px-3 py-1.5 rounded-lg text-xs font-semibold text-slate-600 hover:bg-slate-100">Cancelar</button>
      <button onclick="confirmarRechazo(${id})" class="px-4 py-1.5 rounded-lg text-xs font-semibold bg-rose-600 text-white hover:bg-rose-700">Rechazar</button>
    </div>
  `;
  modal.classList.remove('hidden');
}

async function confirmarRechazo(id) {
  const motivo = document.getElementById('motivo-rechazo').value;
  if (!motivo) return showToast('El motivo es obligatorio', 'error');

  try {
    await apiRequest(`/liquidaciones/${id}/rechazar`, {
      method: 'PATCH',
      body: JSON.stringify({ motivo })
    });
    cerrarGenericModal();
    showToast('Liquidación rechazada');
    renderView();
  } catch (err) {
    showToast(err.message, 'error');
  }
}

function abrirModalAnular(id) {
  const modal = document.getElementById('generic-modal');
  const content = document.getElementById('generic-modal-content');

  content.innerHTML = `
    <h3 class="text-lg font-bold text-slate-900 mb-2">Anular Liquidación (RN-07)</h3>
    <p class="text-xs text-slate-500 mb-4">La anulación libera el periodo para poder reliquidar. Es obligatorio registrar el motivo formal de anulación:</p>
    <textarea id="motivo-anulacion" rows="3" placeholder="Ej: Corrección de horas ingresadas tarde por operarios..."
      class="w-full p-3 text-xs rounded-xl border border-slate-300 outline-none focus:ring-2 focus:ring-rose-500 mb-4"></textarea>
    <div class="flex justify-end space-x-2">
      <button onclick="cerrarGenericModal()" class="px-3 py-1.5 rounded-lg text-xs font-semibold text-slate-600 hover:bg-slate-100">Cancelar</button>
      <button onclick="confirmarAnulacion(${id})" class="px-4 py-1.5 rounded-lg text-xs font-semibold bg-rose-600 text-white hover:bg-rose-700">Anular Liquidación</button>
    </div>
  `;
  modal.classList.remove('hidden');
}

async function confirmarAnulacion(id) {
  const motivo = document.getElementById('motivo-anulacion').value;
  if (!motivo) return showToast('El motivo es obligatorio', 'error');

  try {
    await apiRequest(`/liquidaciones/${id}/anular`, {
      method: 'PATCH',
      body: JSON.stringify({ motivo })
    });
    cerrarGenericModal();
    showToast('Liquidación anulada. El periodo ahora puede reliquidarse.');
    renderView();
  } catch (err) {
    showToast(err.message, 'error');
  }
}

async function verDetalleLiquidacionModal(id) {
  const detalles = await apiRequest(`/liquidaciones/${id}/detalles`);
  const modal = document.getElementById('generic-modal');
  const content = document.getElementById('generic-modal-content');

  modal.firstElementChild.className = 'bg-white rounded-2xl shadow-2xl max-w-4xl w-full p-6 relative border border-slate-100 max-h-[90vh] overflow-y-auto';

  content.innerHTML = `
    <div class="flex items-center justify-between mb-4 pb-3 border-b border-slate-100">
      <div>
        <h3 class="text-lg font-bold text-slate-900">Desglose Detallado de Nómina (Corrida #${id})</h3>
        <p class="text-xs text-slate-500">Detalle individual de cada colaborador liquidado</p>
      </div>
      <button onclick="cerrarGenericModal()" class="text-slate-400 hover:text-slate-600">
        <i class="fa-solid fa-xmark text-lg"></i>
      </button>
    </div>

    <div class="overflow-x-auto">
      <table class="w-full text-xs text-left">
        <thead class="bg-slate-50 text-slate-600 font-bold uppercase tracking-wider border-b border-slate-100">
          <tr>
            <th class="py-2.5 px-3">Colaborador</th>
            <th class="py-2.5 px-3">Perfil</th>
            <th class="py-2.5 px-3 text-center">Horas</th>
            <th class="py-2.5 px-3 text-right">Devengado</th>
            <th class="py-2.5 px-3 text-right">Bonificación</th>
            <th class="py-2.5 px-3 text-right">Salud + Pensión</th>
            <th class="py-2.5 px-3 text-right font-extrabold text-blue-900">Neto Pagado</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-slate-100">
          ${detalles.map(d => `
            <tr class="hover:bg-slate-50 transition">
              <td class="py-2.5 px-3 font-bold text-slate-800">${d.nombres} ${d.apellidos}<br/><span class="text-[10px] text-slate-400 font-normal">C.C. ${d.documento} · ${d.num_hijos} hijos</span></td>
              <td class="py-2.5 px-3 text-slate-600">${d.perfil}</td>
              <td class="py-2.5 px-3 text-center font-bold text-slate-900">${d.horas_totales} h</td>
              <td class="py-2.5 px-3 text-right font-medium text-slate-700">${formatCOP(d.devengado)}</td>
              <td class="py-2.5 px-3 text-right font-medium text-emerald-600">+${formatCOP(d.bonificacion)}</td>
              <td class="py-2.5 px-3 text-right font-medium text-rose-600">-${formatCOP(d.deduccion_salud + d.deduccion_pension)}</td>
              <td class="py-2.5 px-3 text-right font-extrabold text-blue-900">${formatCOP(d.neto)}</td>
            </tr>
          `).join('')}
        </tbody>
      </table>
    </div>
  `;
  modal.classList.remove('hidden');
}

async function aprobarHorasBatchAction() {
  try {
    const res = await apiRequest('/horas/aprobar-batch?anio=2026&mes=9', { method: 'POST' });
    showToast(res.message);
    renderView();
  } catch (err) {
    showToast(err.message, 'error');
  }
}

async function aprobarHoraIndividual(id) {
  try {
    await apiRequest(`/horas/${id}/aprobar`, { method: 'PATCH' });
    showToast('Hora aprobada');
    renderView();
  } catch (err) {
    showToast(err.message, 'error');
  }
}

async function handleRegistroHorasSubmit(e) {
  e.preventDefault();
  const fecha = document.getElementById('hora-fecha').value;
  const tipo_hora_id = parseInt(document.getElementById('hora-tipo').value);
  const jornada_id = parseInt(document.getElementById('hora-jornada').value);
  const horas = parseFloat(document.getElementById('hora-cantidad').value);

  try {
    await apiRequest('/horas', {
      method: 'POST',
      body: JSON.stringify({ fecha, tipo_hora_id, jornada_id, horas })
    });
    showToast('Horas registradas correctamente (Pendientes de revisión)');
    setTab('mis-horas');
  } catch (err) {
    showToast(err.message, 'error');
  }
}

function abrirModalNuevoEmpleado() {
  const modal = document.getElementById('generic-modal');
  const content = document.getElementById('generic-modal-content');

  content.innerHTML = `
    <h3 class="text-lg font-bold text-slate-900 mb-3">Registrar Nuevo Colaborador</h3>
    <form onsubmit="handleNuevoEmpleadoSubmit(event)" class="space-y-3 text-xs">
      <div>
        <label class="block font-semibold text-slate-700 mb-1">Cédula / Documento</label>
        <input type="text" id="new-doc" required class="w-full p-2 rounded-lg border border-slate-300 outline-none">
      </div>
      <div class="grid grid-cols-2 gap-2">
        <div>
          <label class="block font-semibold text-slate-700 mb-1">Nombres</label>
          <input type="text" id="new-nom" required class="w-full p-2 rounded-lg border border-slate-300 outline-none">
        </div>
        <div>
          <label class="block font-semibold text-slate-700 mb-1">Apellidos</label>
          <input type="text" id="new-ape" required class="w-full p-2 rounded-lg border border-slate-300 outline-none">
        </div>
      </div>
      <div class="grid grid-cols-2 gap-2">
        <div>
          <label class="block font-semibold text-slate-700 mb-1">Salario Base (COP)</label>
          <input type="number" id="new-sal" required min="1000000" step="50000" value="2000000" class="w-full p-2 rounded-lg border border-slate-300 outline-none font-bold">
        </div>
        <div>
          <label class="block font-semibold text-slate-700 mb-1"># de Hijos</label>
          <input type="number" id="new-hij" required min="0" max="20" value="0" class="w-full p-2 rounded-lg border border-slate-300 outline-none font-bold">
        </div>
      </div>
      <div>
        <label class="block font-semibold text-slate-700 mb-1">Perfil Laboral</label>
        <select id="new-per" class="w-full p-2 rounded-lg border border-slate-300 outline-none font-semibold">
          <option value="3">Operador</option>
          <option value="2">Personal Administrativo</option>
          <option value="1">Gerencia</option>
        </select>
      </div>
      <div>
        <label class="block font-semibold text-slate-700 mb-1">Correo Electrónico (Acceso)</label>
        <input type="email" id="new-ema" required class="w-full p-2 rounded-lg border border-slate-300 outline-none">
      </div>
      <div class="flex justify-end space-x-2 pt-2">
        <button type="button" onclick="cerrarGenericModal()" class="px-3 py-1.5 rounded-lg font-semibold text-slate-600 hover:bg-slate-100">Cancelar</button>
        <button type="submit" class="px-4 py-1.5 rounded-lg font-semibold bg-blue-600 text-white hover:bg-blue-700">Crear Empleado</button>
      </div>
    </form>
  `;
  modal.classList.remove('hidden');
}

async function handleNuevoEmpleadoSubmit(e) {
  e.preventDefault();
  const documento = document.getElementById('new-doc').value;
  const nombres = document.getElementById('new-nom').value;
  const apellidos = document.getElementById('new-ape').value;
  const salario_base = parseFloat(document.getElementById('new-sal').value);
  const num_hijos = parseInt(document.getElementById('new-hij').value);
  const perfil_id = parseInt(document.getElementById('new-per').value);
  const email = document.getElementById('new-ema').value;

  try {
    await apiRequest('/empleados', {
      method: 'POST',
      body: JSON.stringify({
        documento, nombres, apellidos, salario_base, num_hijos, perfil_id, email,
        rol_codigo: perfil_id === 1 ? 'GERENTE' : perfil_id === 2 ? 'ADMIN' : 'OPERARIO'
      })
    });
    cerrarGenericModal();
    showToast('Empleado y usuario creados exitosamente');
    renderView();
  } catch (err) {
    showToast(err.message, 'error');
  }
}

function abrirModalEditarEmpleado(emp) {
  const modal = document.getElementById('generic-modal');
  const content = document.getElementById('generic-modal-content');

  content.innerHTML = `
    <h3 class="text-lg font-bold text-slate-900 mb-3">Editar Colaborador #${emp.id}</h3>
    <form onsubmit="handleEditarEmpleadoSubmit(event, ${emp.id})" class="space-y-3 text-xs">
      <div class="grid grid-cols-2 gap-2">
        <div>
          <label class="block font-semibold text-slate-700 mb-1">Nombres</label>
          <input type="text" id="edit-nom" value="${emp.nombres}" required class="w-full p-2 rounded-lg border border-slate-300 outline-none">
        </div>
        <div>
          <label class="block font-semibold text-slate-700 mb-1">Apellidos</label>
          <input type="text" id="edit-ape" value="${emp.apellidos}" required class="w-full p-2 rounded-lg border border-slate-300 outline-none">
        </div>
      </div>
      <div class="grid grid-cols-2 gap-2">
        <div>
          <label class="block font-semibold text-slate-700 mb-1">Salario Base (COP)</label>
          <input type="number" id="edit-sal" value="${emp.salario_base}" required min="1000000" step="50000" class="w-full p-2 rounded-lg border border-slate-300 outline-none font-bold">
        </div>
        <div>
          <label class="block font-semibold text-slate-700 mb-1"># de Hijos</label>
          <input type="number" id="edit-hij" value="${emp.num_hijos}" required min="0" max="20" class="w-full p-2 rounded-lg border border-slate-300 outline-none font-bold">
        </div>
      </div>
      <div class="flex justify-end space-x-2 pt-2">
        <button type="button" onclick="cerrarGenericModal()" class="px-3 py-1.5 rounded-lg font-semibold text-slate-600 hover:bg-slate-100">Cancelar</button>
        <button type="submit" class="px-4 py-1.5 rounded-lg font-semibold bg-blue-600 text-white hover:bg-blue-700">Guardar Cambios</button>
      </div>
    </form>
  `;
  modal.classList.remove('hidden');
}

async function handleEditarEmpleadoSubmit(e, id) {
  e.preventDefault();
  const nombres = document.getElementById('edit-nom').value;
  const apellidos = document.getElementById('edit-ape').value;
  const salario_base = parseFloat(document.getElementById('edit-sal').value);
  const num_hijos = parseInt(document.getElementById('edit-hij').value);

  try {
    await apiRequest(`/empleados/${id}`, {
      method: 'PUT',
      body: JSON.stringify({ nombres, apellidos, salario_base, num_hijos })
    });
    cerrarGenericModal();
    showToast('Empleado actualizado exitosamente');
    renderView();
  } catch (err) {
    showToast(err.message, 'error');
  }
}

function cerrarGenericModal() {
  document.getElementById('generic-modal').classList.add('hidden');
}

// ================= BOOTSTRAP & SESSION PERSISTENCE =================
async function initApp() {
  if (state.token) {
    try {
      // Sincronizar y validar en tiempo real el usuario y rol contra el backend
      const freshUser = await apiRequest('/auth/me');
      state.user = freshUser;
      localStorage.setItem('payroll_user', JSON.stringify(freshUser));
    } catch (err) {
      console.warn('Sesión previa inválida o expirada:', err.message);
      state.token = null;
      state.user = null;
      localStorage.removeItem('payroll_token');
      localStorage.removeItem('payroll_user');
      localStorage.removeItem('payroll_tab');
    }
  }
  updateUI();
}

window.addEventListener('DOMContentLoaded', () => {
  initApp();
});
