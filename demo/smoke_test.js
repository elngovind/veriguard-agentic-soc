const fs = require('fs');
const { JSDOM } = require('jsdom');

const html = fs.readFileSync('Veriguard_Demo.html', 'utf8');

// Strip CDN script tags (jsdom can't fetch external resources reliably / Chart.js & Lucide need canvas/real browser APIs)
const cleaned = html
  .replace(/<script src="https:\/\/cdn\.tailwindcss\.com"><\/script>/, '')
  .replace(/<script src="https:\/\/cdn\.jsdelivr\.net[^"]*"><\/script>/, '')
  .replace(/<script src="https:\/\/unpkg\.com[^"]*"><\/script>/, '');

const dom = new JSDOM(cleaned, { runScripts: 'dangerously', resources: 'usable' });

const errors = [];
dom.window.onerror = (msg) => errors.push(msg);

// Stub Chart and lucide since CDN scripts were stripped
dom.window.Chart = function() { return {}; };
dom.window.lucide = { createIcons: () => {} };

// Re-run the inline app script manually since we stripped chart/lucide deps timing
const scriptMatch = cleaned.match(/<script>\s*\/\* ====+ MOCK DATA[\s\S]*<\/script>/);
if (!scriptMatch) { console.error('Could not find main app script'); process.exit(1); }

try {
  dom.window.eval(scriptMatch[0].replace(/<\/?script>/g, ''));
} catch (e) {
  errors.push('eval error: ' + e.message + '\n' + e.stack);
}

const doc = dom.window.document;

function check(label, cond) {
  console.log((cond ? 'PASS' : 'FAIL') + ' - ' + label);
  if (!cond) process.exitCode = 1;
}

check('No JS runtime errors', errors.length === 0);
if (errors.length) console.log(errors.join('\n---\n'));

check('page-title populated', doc.getElementById('page-title').textContent.trim().length > 0);
check('Overview KPI cards rendered (4)', doc.querySelectorAll('#page-content .card').length >= 4);
check('Sidebar nav items present (6)', doc.querySelectorAll('[data-nav]').length === 6);

// Simulate clicking "Tenants" nav
const tenantsNav = doc.querySelector('[data-nav="tenants"]');
tenantsNav.dispatchEvent(new dom.window.Event('click', { bubbles: true }));
check('Tenants page shows 6 rows', doc.querySelectorAll('[data-open-tenant]').length === 6);

// Simulate drilling into a tenant
const row = doc.querySelector('[data-open-tenant="t1"]');
row.dispatchEvent(new dom.window.Event('click', { bubbles: true }));
check('Tenant detail shows Atlas Financial Group', doc.getElementById('page-content').textContent.includes('Atlas Financial Group'));
check('Tenant detail shows findings table', doc.querySelectorAll('#page-content table tbody tr').length > 0);

// Back to tenants via in-page back button
const backBtn = doc.querySelector('[data-nav="tenants"]');
backBtn.dispatchEvent(new dom.window.Event('click', { bubbles: true }));
check('Back to tenants list works', doc.querySelectorAll('[data-open-tenant]').length === 6);

// Comply -> Control Mapping
doc.querySelector('[data-nav="mapping"]').dispatchEvent(new dom.window.Event('click', { bubbles: true }));
check('Mapping page has framework selector', !!doc.getElementById('sel-framework'));
const fwSelect = doc.getElementById('sel-framework');
fwSelect.value = 'PCI-DSS';
fwSelect.dispatchEvent(new dom.window.Event('change', { bubbles: true }));
check('Switching framework to PCI-DSS updates table', doc.getElementById('page-content').textContent.includes('Req 6.2'));

// Evidence packages + generate flow
doc.querySelector('[data-nav="evidence"]').dispatchEvent(new dom.window.Event('click', { bubbles: true }));
check('Evidence packages list rendered', doc.querySelectorAll('#evidence-tbody tr').length === 6);
const genBtn = doc.getElementById('btn-generate-evidence');
check('Generate button present', !!genBtn);
genBtn.dispatchEvent(new dom.window.Event('click', { bubbles: true }));
check('Modal opens on generate click', !!doc.getElementById('modal-backdrop'));
const confirmBtn = doc.getElementById('modal-confirm');
confirmBtn.dispatchEvent(new dom.window.Event('click', { bubbles: true }));
check('New evidence row added after confirm (7 rows)', doc.querySelectorAll('#evidence-tbody tr').length === 7);
check('Modal closes after confirm', !doc.getElementById('modal-backdrop'));

// Drift page
doc.querySelector('[data-nav="drift"]').dispatchEvent(new dom.window.Event('click', { bubbles: true }));
check('Drift events rendered', doc.getElementById('page-content').textContent.includes('Capitol Defense Systems'));

// SLA page
doc.querySelector('[data-nav="sla"]').dispatchEvent(new dom.window.Event('click', { bubbles: true }));
check('SLA breaches table rendered', doc.getElementById('page-content').textContent.includes('Atlas Financial Group'));
check('Billing table rendered with MRR', doc.getElementById('page-content').textContent.includes('$'));

console.log('\nDone.');
