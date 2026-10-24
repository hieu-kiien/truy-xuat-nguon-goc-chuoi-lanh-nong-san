import assert from 'node:assert/strict'
import { after, afterEach, beforeEach, test } from 'node:test'
import { fileURLToPath } from 'node:url'
import { JSDOM } from 'jsdom'
import { createServer } from 'vite'
import React, { act } from 'react'

const dom = new JSDOM('<div id="root"></div>', { url: 'http://test.local/lots', pretendToBeVisual: true })
for (const key of [
  'window',
  'document',
  'HTMLElement',
  'HTMLDivElement',
  'HTMLDialogElement',
  'SVGElement',
  'Element',
  'Node',
  'Event',
  'MouseEvent',
  'sessionStorage',
  'getComputedStyle',
  'requestAnimationFrame',
  'cancelAnimationFrame',
]) {
  globalThis[key] = dom.window[key]
}
Object.defineProperty(globalThis, 'navigator', { value: dom.window.navigator, configurable: true })
globalThis.ResizeObserver = dom.window.ResizeObserver = class {
  observe() {}
  unobserve() {}
  disconnect() {}
}
if (!dom.window.HTMLDialogElement.prototype.showModal) {
  dom.window.HTMLDialogElement.prototype.showModal = function () {
    this.open = true
  }
}
if (!dom.window.HTMLDialogElement.prototype.close) {
  dom.window.HTMLDialogElement.prototype.close = function () {
    this.open = false
  }
}
globalThis.IS_REACT_ACT_ENVIRONMENT = true

const { createRoot } = await import('react-dom/client')
const server = await createServer({
  root: fileURLToPath(new URL('..', import.meta.url)),
  configFile: false,
  optimizeDeps: { noDiscovery: true, include: [] },
  server: { middlewareMode: true, hmr: false },
})
const originalFetch = globalThis.fetch
let root, routes, calls

beforeEach(() => {
  routes = new Map()
  calls = []
  dom.window.history.replaceState({}, '', '/lots')
  globalThis.fetch = async (url, options = {}) => {
    const path = new URL(url, dom.window.location.href).pathname
    const key = `${options.method ?? 'GET'} ${path}`
    calls.push({ key, body: options.body ? JSON.parse(options.body) : null, url: String(url) })
    if (!routes.has(key)) {
      return new Response(JSON.stringify([]), { headers: { 'Content-Type': 'application/json' } })
    }
    const value = routes.get(key)
    if (value instanceof Response) return value
    return new Response(JSON.stringify(typeof value === 'function' ? value() : value), {
      headers: { 'Content-Type': 'application/json' },
    })
  }
  root = createRoot(document.getElementById('root'))
})

afterEach(async () => {
  await act(async () => {
    root.unmount()
    await new Promise((resolve) => setTimeout(resolve, 50))
  })
})

after(async () => {
  globalThis.fetch = originalFetch
  await server.close()
  dom.window.close()
})

const load = async (name) => (await server.ssrLoadModule(`/src/components/${name}.tsx`))[name]
const mount = async (name, props) => {
  const component = await load(name)
  await act(async () => {
    root.render(React.createElement(component, props))
  })
}

const waitFor = async (condition, message = 'Condition not met') => {
  const deadline = Date.now() + 5000
  while (!condition() && Date.now() < deadline) {
    await act(async () => {
      await new Promise((resolve) => setTimeout(resolve, 20))
    })
  }
  assert.ok(condition(), message)
}

const click = async (element) => {
  assert.ok(element, 'Target element must exist')
  await act(() => element.click())
}

const input = async (element, value) => {
  assert.ok(element, 'Target input element must exist')
  await act(() => {
    Object.getOwnPropertyDescriptor(dom.window.HTMLInputElement.prototype, 'value').set.call(element, value)
    element.dispatchEvent(new dom.window.Event('input', { bubbles: true }))
  })
}

const sampleLot = {
  id: '89d69962-fa86-59d7-8adf-26cb56fa9ef4',
  lot_code: 'XOAI-001',
  name: 'Xoài Cát Chu',
  product_id: 'prod-xoai',
  product: { id: 'prod-xoai', name: 'Xoài Cát Chu', unit: 'kg' },
  current_holder_organization_id: 'org-test',
  current_holder_organization_name: 'Hợp tác xã Nông sản An Toàn',
  remaining_quantity: '40.000',
  quantity: '40.000',
  status: 'active',
  harvested_on: '2026-10-15',
  current_location_id: 'loc-1',
  current_location: { id: 'loc-1', name: 'Kho lạnh Tiền Giang', address: 'QL1A, Tiền Giang' },
  event_count: 3,
  parents: [],
  children: [],
  direct_farms: [{ id: 'farm-1', name: 'Nông trại Cái Bè' }],
  root_farms: [{ id: 'farm-1', name: 'Nông trại Cái Bè' }],
}

const sampleLot2 = {
  ...sampleLot,
  id: '89d69962-fa86-59d7-8adf-26cb56fa9ef5',
  lot_code: 'XOAI-002',
  name: 'Xoài Cát Chu Lô 2',
  remaining_quantity: '25.000',
  quantity: '25.000',
}

// =========================================================================
// CHALLENGE 1: In-Place Modal Dialogs in LotsPanel Never Unmount Table / Search / Pagination
// =========================================================================
test('CHALLENGER-1: LotsPanel Create and Merge modals preserve table DOM, search query, and pagination state', async () => {
  routes.set('GET /api/v1/products/', [sampleLot.product])
  routes.set('GET /api/v1/farms/', [{ id: 'farm-1', name: 'Nông trại Cái Bè' }])
  routes.set('GET /api/v1/lots/', () => ({
    items: [sampleLot, sampleLot2],
    next_cursor: 'cursor-page-2',
  }))

  await mount('LotsPanel', {
    canReadLots: true,
    canCreateLots: true,
    canReadFarms: true,
    canReadEvents: true,
    canTransform: true,
    organizationId: 'org-test',
    onOpenLot: () => {},
  })

  // Wait for initial fetch to finish loading table
  await waitFor(() => !document.querySelector('td[aria-busy="true"]'), 'Table must finish loading')

  // Verify table is mounted and displays rows
  const table = document.querySelector('table.lots-table')
  assert.ok(table, 'Lots table is mounted')
  let rows = table.querySelectorAll('tbody tr')
  assert.equal(rows.length, 2, '2 lot rows visible')

  // 1. Enter search query
  const searchInput = document.querySelector('input[type="search"]')
  assert.ok(searchInput, 'Search input exists')
  await input(searchInput, 'XOAI')
  assert.equal(searchInput.value, 'XOAI', 'Search input holds query')

  // 2. Open Create Lot modal
  const createBtn = document.querySelector('a[href*="task=create"]')
  assert.ok(createBtn, 'Create lot button exists')
  await click(createBtn)

  // Verify EditDialog modal is opened
  const dialog = document.querySelector('dialog')
  assert.ok(dialog, 'Create lot modal dialog is open')
  assert.match(dialog.getAttribute('aria-label') ?? dialog.textContent, /Ghi nhận lô thu hoạch/)

  // VERIFY EMPIRICALLY: Table is STILL in the DOM, search input STILL has "XOAI"
  assert.ok(document.querySelector('table.lots-table'), 'Table MUST NOT be unmounted while create dialog is open')
  assert.equal(document.querySelector('input[type="search"]').value, 'XOAI', 'Search query MUST NOT be reset')

  // Close Create Lot dialog
  const closeBtn = dialog.querySelector('button[aria-label="Đóng hộp thoại"]')
  assert.ok(closeBtn, 'Dialog close button exists')
  await click(closeBtn)

  // Dialog should be gone
  assert.equal(document.querySelector('dialog'), null, 'Modal dialog is closed')
  // Verify table and query are completely preserved
  assert.ok(document.querySelector('table.lots-table'), 'Table remains mounted after close')
  assert.equal(document.querySelector('input[type="search"]').value, 'XOAI', 'Search query remains intact after close')

  // Wait for debounced search query to complete fetching table rows
  await waitFor(() => !document.querySelector('td[aria-busy="true"]'), 'Debounced search must finish loading')

  // 3. Test Merge In-Place Modal
  // Select first lot
  const firstCheckbox = document.querySelector('[aria-label^="Chọn XOAI-001"]')
  assert.ok(firstCheckbox, 'First lot checkbox exists')
  await click(firstCheckbox)

  // Wait for product filter synchronization and table reload
  await act(async () => {
    await new Promise((resolve) => setTimeout(resolve, 350))
  })
  await waitFor(() => !document.querySelector('td[aria-busy="true"]'), 'Table reload after first selection')

  // Select second lot
  const secondCheckbox = document.querySelector('[aria-label^="Chọn XOAI-002"]')
  assert.ok(secondCheckbox, 'Second lot checkbox exists')
  await click(secondCheckbox)

  const mergeLink = document.querySelector('a[href*="task=merge"]')
  assert.ok(mergeLink, 'Merge link appears when 2 lots selected')
  await click(mergeLink)

  // Merge modal dialog should be open
  const mergeDialog = document.querySelector('dialog')
  assert.ok(mergeDialog, 'Merge dialog is open')
  assert.match(mergeDialog.getAttribute('aria-label') ?? mergeDialog.textContent, /Gộp các lô/)

  // Check that table and search query still exist behind the dialog
  assert.ok(document.querySelector('table.lots-table'), 'Table MUST NOT be unmounted while merge dialog is open')
  assert.equal(document.querySelector('input[type="search"]').value, 'XOAI', 'Search query intact during merge modal')

  // Close merge dialog via "Hủy" button or close icon
  const cancelBtn = mergeDialog.querySelector('button.ds-button-secondary')
  await click(cancelBtn)

  assert.equal(document.querySelector('dialog'), null, 'Merge modal dialog is closed')
  assert.ok(document.querySelector('table.lots-table'), 'Table remains mounted after merge modal closed')
  assert.equal(document.querySelector('input[type="search"]').value, 'XOAI', 'Search query intact after merge modal closed')
})

// =========================================================================
// CHALLENGE 2: Continuous Mounting of All 5 Detail Tabs in LotDetailPanel
// =========================================================================
test('CHALLENGER-2: All 5 tabs in LotDetailPanel stay continuously mounted across all 7 action modals', async () => {
  routes.set(`GET /api/v1/lots/${sampleLot.id}`, sampleLot)
  routes.set(`GET /api/v1/events/lots/${sampleLot.id}/history`, {
    events: [
      {
        id: 'evt-1',
        sequence_number: 1,
        event_type: 'harvest',
        recorded_at: '2026-10-15T08:00:00Z',
        organization_name: 'Hợp tác xã Nông sản An Toàn',
        payload: {},
        prev_hash: '0'.repeat(64),
        event_hash: 'a'.repeat(64),
      },
    ],
    total: 1,
    next_cursor: null,
    integrity: { valid: true, checked_events: 1 },
  })
  routes.set('GET /api/v1/handovers/incoming', [])
  routes.set('GET /api/v1/handovers/outgoing', [])
  routes.set('GET /api/v1/handovers/organizations', [{ id: 'org-2', name: 'Công ty Vận tải Lạnh' }])
  routes.set('GET /api/v1/locations/', [sampleLot.current_location])
  routes.set(`GET /api/v1/lots/${sampleLot.id}/input-lots`, [])
  routes.set(`GET /api/v1/lots/${sampleLot.id}/steps`, [])
  routes.set(`GET /api/v1/lots/${sampleLot.id}/lineage`, {
    selected_lot_id: sampleLot.id,
    nodes: [sampleLot],
    edges: [],
    roots: [sampleLot.id],
    root_farms: sampleLot.root_farms,
  })
  routes.set(`GET /api/v1/lots/${sampleLot.id}/recall`, {
    root_lot: sampleLot,
    summary: {
      total_descendants_count: 0,
      total_recoverable_kg: '40.000',
      total_consumed_kg: '0.000',
      involved_organizations_count: 1,
      involved_organizations: ['Hợp tác xã Nông sản An Toàn'],
      has_multi_source_merge: false,
      has_consumed_lot: false,
    },
    descendants: [],
    affected_lots: [],
  })
  routes.set('GET /api/v1/recalls/', [])

  await mount('LotDetailPanel', {
    lotId: sampleLot.id,
    organizationId: 'org-test',
    canManageDistribution: true,
    canTransform: true,
    canOpenRecall: true,
    canManageRecall: true,
    canConfirmRecall: true,
    canReadEvents: true,
    canCreateEvents: true,
    canCreateHandover: true,
    canResolveHandover: true,
    canReadInputLots: true,
    canDeclareInputLots: true,
    canReadProcessingSteps: true,
    canRecordProcessingSteps: true,
    onOpenLot: () => {},
    onBack: () => {},
  })

  // Wait for loading to finish
  await waitFor(() => document.querySelector('nav.detail-tabs'), 'Detail tabs must finish loading')

  // Verify all 5 tabs exist in DOM
  const verifyAll5TabsMounted = (contextMsg) => {
    const tabList = document.querySelector('nav.detail-tabs[role="tablist"]')
    assert.ok(tabList, `[${contextMsg}] Tablist nav must be in DOM`)
    const tabButtons = tabList.querySelectorAll('button[role="tab"]')
    assert.equal(tabButtons.length, 5, `[${contextMsg}] Exactly 5 tabs must be mounted`)
    const tabIds = [...tabButtons].map((btn) => btn.id)
    assert.deepEqual(
      tabIds,
      ['tab-overview', 'tab-history', 'tab-origins', 'tab-inputs', 'tab-steps'],
      `[${contextMsg}] All 5 tab IDs must match exactly`
    )
  }

  verifyAll5TabsMounted('Initial render')

  const actionsToTest = [
    { name: 'Split', selector: 'a[href*="task=split"]', expectedTitle: /Tách lô/ },
    { name: 'Merge', selector: 'a[href*="task=merge"]', expectedTitle: /Gộp lô/ },
    { name: 'Move', selector: 'a[href*="task=move"]', expectedTitle: /Di chuyển/ },
    { name: 'Consume', selector: 'a[href*="task=consume"]', expectedTitle: /tiêu thụ/i },
    { name: 'Handover', selector: 'a[href*="task=handover"]', expectedTitle: /Bàn giao/ },
    { name: 'Event', selector: 'a[href*="task=event"]', expectedTitle: /Ghi nhận hoạt động/ },
    { name: 'Recall', selector: 'a[href*="task=recall"]', expectedTitle: /Kế hoạch thu hồi/ },
  ]

  for (const action of actionsToTest) {
    const actionTrigger = document.querySelector(action.selector)
    assert.ok(actionTrigger, `Action trigger for ${action.name} must exist`)
    await click(actionTrigger)

    // Modal dialog is opened
    const dialog = document.querySelector('dialog')
    assert.ok(dialog, `Modal dialog for ${action.name} should open`)
    assert.match(
      dialog.getAttribute('aria-label') ?? dialog.textContent,
      action.expectedTitle,
      `Dialog title for ${action.name} matches expected`
    )

    // CRITICAL ADVERSARIAL CHECK: All 5 tabs MUST remain in the DOM!
    verifyAll5TabsMounted(`While ${action.name} modal is OPEN`)

    // Close modal dialog
    const closeBtn = dialog.querySelector('button[aria-label="Đóng hộp thoại"]')
    assert.ok(closeBtn, `Close button in ${action.name} dialog must exist`)
    await click(closeBtn)

    // Dialog is closed
    assert.equal(document.querySelector('dialog'), null, `Modal for ${action.name} is closed`)

    // Verify all 5 tabs still mounted after close
    verifyAll5TabsMounted(`After ${action.name} modal is CLOSED`)
  }

  // Also verify QR modal
  const qrBtn = document.querySelector('button.lot-qr-btn')
  assert.ok(qrBtn, 'QR button exists')
  await click(qrBtn)
  const qrDialog = document.querySelector('dialog')
  assert.ok(qrDialog, 'QR dialog is open')
  verifyAll5TabsMounted('While QR modal is OPEN')
  await click(qrDialog.querySelector('button[aria-label="Đóng hộp thoại"]'))
  verifyAll5TabsMounted('After QR modal is CLOSED')
})

// =========================================================================
// CHALLENGE 3: LotTransformForm Edge Cases (BigInt Rounding, Zero, Negative, Overstock)
// =========================================================================
test('CHALLENGER-3: LotTransformForm applyEvenSplit handles BigInt rounding and zero mass properly', async () => {
  routes.set('GET /api/v1/lots/', { items: [], next_cursor: null })

  // 1. Test 10.000 kg split into 3 parts (10000g / 3 = 3333g, rem 1g -> [3334g, 3333g, 3333g] -> sum 10000g)
  const lot10kg = { ...sampleLot, remaining_quantity: '10.000' }
  await mount('LotTransformForm', {
    lot: lot10kg,
    canManageDistribution: false,
    onCompleted: () => {},
  })

  // Add 3rd child
  const addBtn = [...document.querySelectorAll('button')].find((b) => b.textContent === 'Thêm lô con')
  assert.ok(addBtn, 'Add child button exists')
  await click(addBtn)

  assert.equal(document.querySelectorAll('.transform-row').length, 3, '3 child rows')

  // Click Quick Split helper
  const quickSplitBtn = [...document.querySelectorAll('button')].find((b) =>
    b.textContent.includes('Gợi ý chia đều')
  )
  assert.ok(quickSplitBtn, 'Quick split button exists')
  await click(quickSplitBtn)

  const childInputs = document.querySelectorAll('input[inputmode="decimal"]')
  assert.equal(childInputs.length, 3)
  assert.equal(childInputs[0].value, '3.334', 'Child 0 receives remainder 1g')
  assert.equal(childInputs[1].value, '3.333', 'Child 1 receives base 3333g')
  assert.equal(childInputs[2].value, '3.333', 'Child 2 receives base 3333g')

  // Check mass summary
  const summaryEl = document.querySelector('.mass-summary')
  assert.ok(summaryEl, 'Mass summary exists')
  assert.match(summaryEl.textContent, /Tổng khối lượng: 10.000 kg/)
  assert.match(summaryEl.textContent, /Lô nguồn sẽ còn 0.000 kg/)
  assert.equal(summaryEl.classList.contains('mass-error'), false, 'No mass error')

  // Submit button should be enabled
  const submitBtn = document.querySelector('button[type="submit"]')
  assert.equal(submitBtn.disabled, false, 'Valid exact split enables submit button')

  // 2. Test Zero Mass: set child 0 to "0.000"
  await input(childInputs[0], '0.000')
  assert.equal(submitBtn.disabled, true, 'Zero mass must disable submit button')

  // 3. Test Negative Mass: set child 0 to "-5"
  await input(childInputs[0], '-5')
  assert.equal(submitBtn.disabled, true, 'Negative mass must disable submit button')

  // 4. Test Overstock: set child 0 to "8.000", child 1 to "2.000", child 2 to "1.000" (total 11.000, available 10.000)
  await input(childInputs[0], '8.000')
  await input(childInputs[1], '2.000')
  await input(childInputs[2], '1.000')
  assert.equal(submitBtn.disabled, true, 'Overstock must disable submit button')
  assert.ok(summaryEl.classList.contains('mass-error'), 'Mass summary must have mass-error class on overstock')
  assert.match(summaryEl.textContent, /Vượt 1.000 kg/, 'Overstock amount is exactly 1.000 kg')
})

test('CHALLENGER-4: LotTransformForm handles 0.000 remaining lot without division by zero crash', async () => {
  routes.set('GET /api/v1/lots/', { items: [], next_cursor: null })

  const lot0kg = { ...sampleLot, remaining_quantity: '0.000' }
  await mount('LotTransformForm', {
    lot: lot0kg,
    canManageDistribution: false,
    onCompleted: () => {},
  })

  const quickSplitBtn = [...document.querySelectorAll('button')].find((b) =>
    b.textContent.includes('Gợi ý chia đều')
  )
  assert.ok(quickSplitBtn)
  // Clicking quick split on 0 quantity must not throw or crash
  await click(quickSplitBtn)

  const childInputs = document.querySelectorAll('input[inputmode="decimal"]')
  // Values should remain empty and not set to NaN
  assert.equal(childInputs[0].value, '')
  assert.equal(childInputs[1].value, '')
  assert.equal(document.querySelector('button[type="submit"]').disabled, true)
})
