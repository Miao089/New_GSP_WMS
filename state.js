// state.js - Shared State Management for Multi-Page WMS & TMS

const INITIAL_STATE = {
  suppliers: [
    { id: 'S01', name: '江苏医工器械制造有限公司', permitNo: '苏食药监械经营许20220815号', allowedCategories: ['6846', '6815'], expiryDate: '2028-12-31' },
    { id: 'S02', name: '常州生物医疗试剂厂', permitNo: '苏食药监械经营许20230114号', allowedCategories: ['6840'], expiryDate: '2027-05-15' },
    { id: 'S03', name: '无锡一次性耗材总厂', permitNo: '苏食药监械经营许20211022号', allowedCategories: ['6815'], expiryDate: '2029-10-22' }
  ],
  clients: [
    { id: 'C01', name: '南京第一人民医院', permitNo: '苏械经营备20200001号', allowedCategories: ['6846', '6840', '6815'], expiryDate: '2029-01-01' },
    { id: 'C02', name: '苏州仁爱社区门诊部', permitNo: '苏械经营备20210088号', allowedCategories: ['6815'], expiryDate: '2028-08-18' }
  ],
  materials: [
    { id: 'M01', name: '骨科金属接骨板', spec: 'A-Type 12孔', category: '6846', class: 'III', regNo: '国械注准20223130982', regExpiry: '2027-12-31', tempZone: 'normal', requiresSN: true, di: '06971122334455', manufacturer: '江苏医工器械制造有限公司' },
    { id: 'M02', name: '体外诊断测试检测试剂盒', spec: '24人份/盒', category: '6840', class: 'II', regNo: '国械注准20232400124', regExpiry: '2028-06-30', tempZone: 'cold', requiresSN: false, di: '06971122334466', manufacturer: '常州生物医疗试剂厂' },
    { id: 'M03', name: '一次性无菌注射器', spec: '5ml (带针)', category: '6815', class: 'II', regNo: '国械注备20212040188', regExpiry: '2026-12-31', tempZone: 'normal', requiresSN: false, di: '06971122334477', manufacturer: '无锡一次性耗材总厂' }
  ],
  inboundOrders: [
    { id: 'PO-20260614001', supplierId: 'S01', date: '2026-06-14', items: [{ materialId: 'M01', qty: 10 }], status: 'pending' },
    { id: 'PO-20260614002', supplierId: 'S02', date: '2026-06-14', items: [{ materialId: 'M02', qty: 20 }], status: 'pending' },
    { id: 'PO-20260614003', supplierId: 'S03', date: '2026-06-14', items: [{ materialId: 'M03', qty: 50 }], status: 'pending' }
  ],
  outboundOrders: [
    { id: 'SO-20260614001', clientId: 'C01', date: '2026-06-14', items: [{ materialId: 'M01', qty: 5 }, { materialId: 'M02', qty: 5 }], status: 'pending' },
    { id: 'SO-20260614002', clientId: 'C02', date: '2026-06-14', items: [{ materialId: 'M01', qty: 2 }], status: 'pending', blockedReason: '' }
  ],
  inventory: [
    { loc: 'A-01-01', materialId: 'M01', qty: 10, batch: 'B260510', expiry: '2028-05-10', sn: ['SN1001', 'SN1002', 'SN1003', 'SN1004', 'SN1005', 'SN1006', 'SN1007', 'SN1008', 'SN1009', 'SN1010'], locked: false, lockReason: '' },
    { loc: 'B-01-01', materialId: 'M03', qty: 200, batch: 'LOT260420', expiry: '2026-10-20', sn: [], locked: false, lockReason: '' },
    { loc: 'B-01-02', materialId: 'M03', qty: 150, batch: 'LOT260501', expiry: '2026-11-01', sn: [], locked: false, lockReason: '' },
    { loc: 'C-01-01', materialId: 'M02', qty: 15, batch: 'B260601', expiry: '2028-06-01', sn: [], locked: false, lockReason: '' }
  ],
  waybills: [
    { id: 'SF14992019902', orderId: 'SO-20260614001', carrier: '顺丰冷运', status: '运输中', tempHistory: [4.8, 5.0, 5.2, 5.1, 4.9, 4.6, 5.1, 5.3, 5.2], boxId: 'BOX-0048', handoverTemp: 5.1, sealNo: 'SF-SEAL-9874', signee: '李晓华 (人民医院药剂科)', handoverTime: '' }
  ],
  auditLogs: [
    { timestamp: '2026-06-14 10:00:00', actor: 'SYSTEM', type: 'system', content: 'WMS多页面系统部署，跨页面状态引擎启动成功。' },
    { timestamp: '2026-06-14 10:05:00', actor: 'Admin', type: 'system', content: '同步完成往来单位与器械产品主数据。' }
  ],
  syncLogs: [
    { timestamp: '16:45:00', content: '成功轮询同步采购入库通知单：PO-20260614001' },
    { timestamp: '16:40:00', content: '成功同步器械主数据 [骨科金属接骨板] 注册证信息更新' },
    { timestamp: '16:30:00', content: '成功轮询同步销售出库申请单：SO-20260614002' }
  ]
};

// Exportable shared states
export let state = {};
export let simState = {};

// Load states from localStorage or init
export function loadAllState() {
  const savedState = localStorage.getItem('gsp_wms_state');
  if (savedState) {
    state = JSON.parse(savedState);
  } else {
    state = JSON.parse(JSON.stringify(INITIAL_STATE));
    saveState();
  }

  const savedSimState = localStorage.getItem('gsp_wms_sim_state');
  if (savedSimState) {
    simState = JSON.parse(savedSimState);
  } else {
    simState = {
      supplierExpired: false,
      clientScopeMismatch: false,
      materialExpired: false,
      coldTempAlarm: false
    };
    saveSimState();
  }
}

export function saveState() {
  localStorage.setItem('gsp_wms_state', JSON.stringify(state));
}

export function saveSimState() {
  localStorage.setItem('gsp_wms_sim_state', JSON.stringify(simState));
}

export function resetAllData() {
  state = JSON.parse(JSON.stringify(INITIAL_STATE));
  simState = {
    supplierExpired: false,
    clientScopeMismatch: false,
    materialExpired: false,
    coldTempAlarm: false
  };
  saveState();
  saveSimState();
  addAuditLog('Admin', 'system', '已重置所有原型数据至系统期初出厂状态。');
}

export function addAuditLog(actor, type, content) {
  const time = new Date().toISOString().replace('T', ' ').substring(0, 19);
  state.auditLogs.unshift({ timestamp: time, actor, type, content });
  saveState();
  
  // Dispatch local event for same page refresh
  window.dispatchEvent(new Event('wms_state_changed'));
}

export function appendSyncLog(log) {
  const time = new Date().toTimeString().split(' ')[0];
  state.syncLogs.unshift({ timestamp: time, content: log });
  saveState();
  
  window.dispatchEvent(new Event('wms_state_changed'));
}

// Initial invocation
loadAllState();

// Listen to storage event (cross-window/cross-tab updates)
window.addEventListener('storage', (e) => {
  if (e.key === 'gsp_wms_state' || e.key === 'gsp_wms_sim_state') {
    loadAllState();
    window.dispatchEvent(new CustomEvent('wms_state_changed', { detail: { crossPage: true } }));
  }
});
