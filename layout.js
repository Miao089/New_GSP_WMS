// layout.js - Dynamic Layout Injection and Simulation Sync

import { state, simState, saveState, saveSimState, addAuditLog, appendSyncLog, resetAllData } from './state.js';

document.addEventListener('DOMContentLoaded', () => {
  injectShell();
  initTime();
  syncSimDrawerControls();
  highlightActiveMenu();
  
  // Set up event listeners for layout controls
  document.getElementById('drawer-toggle-btn').addEventListener('click', toggleSimulationDrawer);
});

// Inject Sidebar, Header and Simulation Drawer
function injectShell() {
  const container = document.querySelector('.app-container');
  if (!container) return;
  
  // 1. Ingest Sidebar
  const sidebar = document.createElement('aside');
  sidebar.className = 'sidebar';
  sidebar.innerHTML = `
    <div class="brand">
      <i class="fa-solid fa-square-virus brand-icon"></i>
      <div class="brand-text">
        <h1>GSP WMS & TMS</h1>
        <span>医疗器械合规系统</span>
      </div>
    </div>
    
    <nav class="menu">
      <a href="index.html" class="menu-item" id="nav-index">
        <i class="fa-solid fa-chart-line"></i> <span>数字化大屏</span>
      </a>
      <a href="qualifications.html" class="menu-item" id="nav-qualifications">
        <i class="fa-solid fa-id-card-clip"></i> <span>GSP 资质核查</span>
      </a>
      <a href="inbound.html" class="menu-item" id="nav-inbound">
        <i class="fa-solid fa-file-import"></i> <span>采购入库验收</span>
      </a>
      <a href="inventory.html" class="menu-item" id="nav-inventory">
        <i class="fa-solid fa-cubes"></i> <span>库内可视化大屏</span>
      </a>
      <a href="outbound.html" class="menu-item" id="nav-outbound">
        <i class="fa-solid fa-file-export"></i> <span>出库复核 FEFO</span>
      </a>
      <a href="tms.html" class="menu-item" id="nav-tms">
        <i class="fa-solid fa-truck-ramp-box"></i> <span>3PL 冷链与交接</span>
      </a>
      <a href="audit.html" class="menu-item" id="nav-audit">
        <i class="fa-solid fa-clipboard-check"></i> <span>审计追踪与验证</span>
      </a>
    </nav>
    
    <div class="sidebar-footer">
      <div class="erp-status">
        <span class="pulse-dot green"></span>
        <span>金蝶 ERP 中间库: 已连接</span>
      </div>
    </div>
  `;
  container.insertBefore(sidebar, container.firstChild);

  // 2. Ingest Top Navbar (into the main-content)
  const mainContent = document.querySelector('.main-content');
  if (mainContent) {
    const navbar = document.createElement('header');
    navbar.className = 'top-navbar';
    
    // Page Title based on current page
    const pageTitles = {
      'index.html': { t: '数字化大屏', s: 'Warehouse & Transport Management System for GSP Compliance' },
      'qualifications.html': { t: 'GSP 资质核查', s: '供应商资质、客户网络核查与注册证有效期卡控' },
      'inbound.html': { t: '采购入库验收', s: '符合 GSP 规定的 UDI 解析验收与温区上架推荐' },
      'inventory.html': { t: '库内可视化大屏', s: '仓库可视化货位大屏、货位温湿度及审计锁定' },
      'outbound.html': { t: '出库复核 FEFO', s: '购货方资质校验、FEFO 智能配货分配与 SN 追踪复核' },
      'tms.html': { t: '3PL 冷链与交接', s: '委托三方运输轨迹、在途冷箱温度回传与签收交接' },
      'audit.html': { t: '审计追踪与验证', s: '计算机系统验证 (CVS) 测试沙箱与系统日志审计' }
    };
    
    const pageName = getPageName();
    const activeTitle = pageTitles[pageName] || { t: 'WMS & TMS 系统', s: 'GSP Compliant Warehouse Platform' };
    
    navbar.innerHTML = `
      <div class="page-title-area">
        <h2 id="current-page-title">${activeTitle.t}</h2>
        <p id="current-page-subtitle">${activeTitle.s}</p>
      </div>
      
      <div class="header-widgets">
        <div class="time-widget">
          <i class="fa-regular fa-clock"></i>
          <span id="live-time">00:00:00</span>
        </div>
        
        <div class="status-badge" id="system-health-badge">
          <i class="fa-solid fa-shield-halved"></i> GSP 合规护航中
        </div>
      </div>
    `;
    mainContent.insertBefore(navbar, mainContent.firstChild);
  }

  // 3. Ingest Simulation Control Drawer
  const drawer = document.createElement('div');
  drawer.className = 'simulation-drawer';
  drawer.id = 'simulation-drawer';
  drawer.innerHTML = `
    <button class="drawer-toggle" id="drawer-toggle-btn">
      <i class="fa-solid fa-screwdriver-wrench"></i>
      <span>模拟控制中心</span>
    </button>
    
    <div class="drawer-content">
      <h3><i class="fa-solid fa-sliders"></i> GSP 实操模拟控制器</h3>
      <p class="drawer-desc">在此切换各种外部限制状态，验证 WMS 是否能实时拦截并符合 GSP 合规逻辑。</p>
      
      <div class="sim-section">
        <h4><i class="fa-solid fa-store"></i> 供应链资质模拟控制</h4>
        
        <div class="control-item">
          <span class="label">供应商资质 [医工器械]</span>
          <div class="toggle-switch">
            <label class="switch">
              <input type="checkbox" id="sim-supplier-expired">
              <span class="slider round"></span>
            </label>
            <span class="status-lbl" id="lbl-supplier-state">有效期内</span>
          </div>
        </div>

        <div class="control-item">
          <span class="label">客户资质 [人民医院]</span>
          <div class="toggle-switch">
            <label class="switch">
              <input type="checkbox" id="sim-client-scope">
              <span class="slider round"></span>
            </label>
            <span class="status-lbl" id="lbl-client-state">范围合规</span>
          </div>
        </div>

        <div class="control-item">
          <span class="label">金属板注册证 [国械注准]</span>
          <div class="toggle-switch">
            <label class="switch">
              <input type="checkbox" id="sim-material-expired">
              <span class="slider round"></span>
            </label>
            <span class="status-lbl" id="lbl-material-state">有效期内</span>
          </div>
        </div>
      </div>

      <div class="sim-section">
        <h4><i class="fa-solid fa-temperature-arrow-up"></i> 温湿度突发异常模拟</h4>
        
        <div class="control-item">
          <span class="label">冷藏库温度 (2-8℃)</span>
          <div class="input-action-row">
            <input type="number" id="sim-cold-temp-val" value="4.5" step="0.1" style="width: 70px;">
            <button class="btn btn-secondary btn-sm" id="sim-push-temp-btn">模拟推送</button>
          </div>
        </div>
      </div>

      <div class="sim-section">
        <h4><i class="fa-solid fa-network-wired"></i> 金蝶 ERP 数据下发</h4>
        <button class="btn btn-secondary btn-block btn-sm" id="sim-erp-inbound-btn"><i class="fa-solid fa-circle-down"></i> 下发一批采购入库单</button>
        <button class="btn btn-secondary btn-block btn-sm" id="sim-erp-outbound-btn" style="margin-top: 5px;"><i class="fa-solid fa-circle-up"></i> 下发一批销售出库单</button>
      </div>

      <div class="sim-section">
        <h4><i class="fa-solid fa-arrow-rotate-right"></i> 数据重置</h4>
        <button class="btn btn-danger btn-block btn-sm" id="sim-reset-btn"><i class="fa-solid fa-trash-can"></i> 重置所有原型数据</button>
      </div>
    </div>
  `;
  container.appendChild(drawer);
  
  // Bind events to the dynamically generated controls
  bindSimDrawerEvents();
}

function getPageName() {
  const path = window.location.pathname;
  let page = path.substring(path.lastIndexOf('/') + 1);
  if (page === '' || page === 'index') page = 'index.html';
  return page;
}

function highlightActiveMenu() {
  let pageName = getPageName();
  // Deactivate all
  const items = document.querySelectorAll('.menu-item');
  items.forEach(item => item.classList.remove('active'));
  
  // Handle default index
  if (pageName === 'index.html') {
    const el = document.getElementById('nav-index');
    if (el) el.classList.add('active');
  } else {
    // Find item with matching href
    items.forEach(item => {
      const href = item.getAttribute('href');
      if (href && pageName.includes(href)) {
        item.classList.add('active');
      }
    });
  }
}

function initTime() {
  setInterval(() => {
    const now = new Date();
    const timeStr = now.toTimeString().split(' ')[0];
    const el = document.getElementById('live-time');
    if (el) el.innerText = timeStr;
  }, 1000);
}

function toggleSimulationDrawer() {
  const drawer = document.getElementById('simulation-drawer');
  drawer.classList.toggle('open');
}

// Bind event listeners to simulation controls
function bindSimDrawerEvents() {
  document.getElementById('sim-supplier-expired').addEventListener('change', onSimulationControlChange);
  document.getElementById('sim-client-scope').addEventListener('change', onSimulationControlChange);
  document.getElementById('sim-material-expired').addEventListener('change', onSimulationControlChange);
  
  document.getElementById('sim-push-temp-btn').addEventListener('click', triggerSimColdTempPush);
  
  document.getElementById('sim-erp-inbound-btn').addEventListener('click', () => {
    const nextId = 'PO-202606140' + (state.inboundOrders.length + 1);
    state.inboundOrders.push({
      id: nextId,
      supplierId: 'S01',
      date: '2026-06-14',
      items: [{ materialId: 'M01', qty: 5 }],
      status: 'pending'
    });
    saveState();
    appendSyncLog(`成功轮询同步采购入库通知单：${nextId}`);
    addAuditLog('Kingdee ERP', 'system', `ERP推送采购入库通知单 ${nextId}`);
    
    // Refresh page
    window.location.reload();
  });
  
  document.getElementById('sim-erp-outbound-btn').addEventListener('click', () => {
    const nextId = 'SO-202606140' + (state.outboundOrders.length + 1);
    state.outboundOrders.push({
      id: nextId,
      clientId: 'C02',
      date: '2026-06-14',
      items: [{ materialId: 'M01', qty: 3 }],
      status: 'pending'
    });
    saveState();
    appendSyncLog(`成功轮询同步销售出库申请单：${nextId}`);
    addAuditLog('Kingdee ERP', 'system', `ERP推送销售出库申请单 ${nextId}`);
    
    // Refresh page
    window.location.reload();
  });
  
  document.getElementById('sim-reset-btn').addEventListener('click', () => {
    resetAllData();
    window.location.href = 'index.html';
  });
}

function onSimulationControlChange() {
  simState.supplierExpired = document.getElementById('sim-supplier-expired').checked;
  simState.clientScopeMismatch = document.getElementById('sim-client-scope').checked;
  simState.materialExpired = document.getElementById('sim-material-expired').checked;
  
  saveSimState();
  
  addAuditLog('SYSTEM', 'system', `模拟卡控参数变更：供应商过期(${simState.supplierExpired}), 客户超限(${simState.clientScopeMismatch}), 注册证过期(${simState.materialExpired})`);
  
  // Update state labels inside drawer
  updateSimDrawerLabels();
  
  // Emit local event for components to catch and update
  window.dispatchEvent(new Event('wms_state_changed'));
}

function updateSimDrawerLabels() {
  const lblSupplier = document.getElementById('lbl-supplier-state');
  lblSupplier.innerText = simState.supplierExpired ? '过期拦截' : '有效期内';
  lblSupplier.className = simState.supplierExpired ? 'status-lbl expired' : 'status-lbl ok';
  
  const lblClient = document.getElementById('lbl-client-state');
  lblClient.innerText = simState.clientScopeMismatch ? '范围越界' : '范围合规';
  lblClient.className = simState.clientScopeMismatch ? 'status-lbl expired' : 'status-lbl ok';
  
  const lblMaterial = document.getElementById('lbl-material-state');
  lblMaterial.innerText = simState.materialExpired ? '注册证过期' : '有效期内';
  lblMaterial.className = simState.materialExpired ? 'status-lbl expired' : 'status-lbl ok';
}

function triggerSimColdTempPush() {
  const tempInput = document.getElementById('sim-cold-temp-val');
  const newTemp = parseFloat(tempInput.value);
  
  state.waybills.forEach(w => {
    if (w.status === '运输中') {
      w.tempHistory.push(newTemp);
    }
  });

  // Apply to GSP auto-lockdown for warehouse cold stores
  if (newTemp < 2.0 || newTemp > 8.0) {
    simState.coldTempAlarm = true;
    saveSimState();
    
    let lockedCount = 0;
    state.inventory.forEach(inv => {
      const mat = state.materials.find(m => m.id === inv.materialId);
      if (mat && mat.tempZone === 'cold' && !inv.locked) {
        inv.locked = true;
        inv.lockReason = '冷藏库温湿度发生异常超限告警，系统触发自动联动锁定。';
        lockedCount++;
        addAuditLog('SYSTEM', 'lock', `自动联动锁定货位 ${inv.loc} 商品 [${mat.name}]，原因: 冷藏库温度超标 (${newTemp}℃)`);
      }
    });
    
    if (lockedCount > 0) {
      saveState();
      alert(`[温湿度超标报警]\n冷藏库温度检测到偏离GSP规定区间(当前: ${newTemp}℃)！系统已自动冻结锁定冷藏区在库的 ${lockedCount} 个货位。`);
    }
  } else {
    simState.coldTempAlarm = false;
    saveSimState();
  }
  
  // Dispatch local state change event
  window.dispatchEvent(new CustomEvent('wms_state_changed', { detail: { tempChanged: true, newTemp: newTemp } }));
}

// Populate simulation drawer switch states from simState on load
function syncSimDrawerControls() {
  document.getElementById('sim-supplier-expired').checked = simState.supplierExpired;
  document.getElementById('sim-client-scope').checked = simState.clientScopeMismatch;
  document.getElementById('sim-material-expired').checked = simState.materialExpired;
  
  updateSimDrawerLabels();
}

// Global state sync listener
window.addEventListener('wms_state_changed', (e) => {
  if (e.detail && e.detail.crossPage) {
    syncSimDrawerControls();
  }
});
