import assert from 'node:assert/strict'
import { createRequire } from 'node:module'
const { chromium } = createRequire(import.meta.url)(process.env.PLAYWRIGHT_MODULE_PATH || 'playwright')
const browser = await chromium.launch({ headless: true, executablePath: process.env.TEST_CHROMIUM_EXECUTABLE || undefined })
function gate() { let release, seen; return { wait: new Promise((r) => { release = r }), entered: new Promise((r) => { seen = r }), release: () => release(), seen: () => seen() } }
function content(id) {
  const pair = () => ({ positive: '', negative: '', overrides: { positive: false, negative: false } })
  const prompts = Object.fromEntries(['appearance', 'upper_underwear', 'lower_underwear'].map((key) => [key, pair()]))
  prompts.appearance.positive = `test-only-${id}`
  return { schema_version: 1, cpu_id: id, revision: 0, pack_revision_id: null, pack: null, prompts, levels: Object.fromEntries([0, 1, 2, 3].map((level) => [level, Object.fromEntries(['profile', 'full_body', 'cg'].map((kind) => [kind, { ...pair(), revision: 0 }]))])) }
}
try {
  const page = await browser.newPage(); page.setDefaultTimeout(8000)
  const errors = []; page.on('pageerror', (e) => errors.push(e.message))
  await page.addInitScript(() => { window.nrnfDesktop = { isDesktop: true } })
  const saved = { 1: content(1), 2: content(2) }
  const cpus = [1, 2, 3].map((id) => ({ id, slug: `cpu-${id}`, name: `CPU ${id}`, defeat_stage: 0, style: 'balanced', short_description: 'test-only', profile_image_key: null }))
  let saveMode = 'ok', saveGate, readGate, scanGate, scans = 0, lastPatch, applyGate, applyMode = 'ok', lastApplication, applications = 0
  const listing = { schema_version: 1, packs: [], scan_entries: [] }
  await page.route('**/api/**', async (route) => {
    const request = route.request(), path = new URL(request.url()).pathname
    const character = path.match(/^\/api\/local\/characters\/(\d+)\/content$/)
    const application = path.match(/^\/api\/local\/characters\/(\d+)\/pack-application$/)
    if (application) {
      applications++; lastApplication = request.postDataJSON()
      if (applyMode !== 'ok') return route.fulfill({ status: applyMode === 'conflict' ? 409 : 500, json: { detail: { message: `test-apply-${applyMode}` } } })
      const id = Number(application[1]), next = structuredClone(saved[id])
      const target = listing.packs.find((p) => p.id === lastApplication.pack_id)
      next.revision++; next.pack_revision_id = target.registered_revision.id
      next.pack = { id: target.id, pack_id: target.pack_id, applied_revision_id: next.pack_revision_id, applied_revision: target.registered_revision.revision, registered_revision_id: next.pack_revision_id, update_available: false }
      const sourcePair = () => ({ positive: `test-source-${next.pack.applied_revision}-P`, negative: `test-source-${next.pack.applied_revision}-N` })
      next.pack_source = { prompts: {}, levels: {} }
      for (const [group, pair] of Object.entries(next.prompts)) {
        next.pack_source.prompts[group] = sourcePair()
        for (const field of ['positive', 'negative']) if (!pair.overrides[field]) pair[field] = sourcePair()[field]
      }
      for (const [level, kinds] of Object.entries(next.levels)) {
        next.pack_source.levels[level] = { framing: {} }
        for (const [kind, pair] of Object.entries(kinds)) {
          next.pack_source.levels[level].framing[kind] = sourcePair()
          for (const field of ['positive', 'negative']) if (!pair.overrides[field]) pair[field] = sourcePair()[field]
          pair.media = { media_id: `test-media-${next.pack.applied_revision}-${level}-${kind}`, url: '/unused-test-reference', digest: 'test-only' }
        }
      }
      const held = applyGate; if (held) { held.seen(); await held.wait }; saved[id] = next
      return route.fulfill({ json: next })
    }
    if (character) {
      const id = Number(character[1])
      if (request.method() === 'GET') {
        const snapshot = structuredClone(saved[id]), held = readGate
        if (id === 2 && held) { held.seen(); await held.wait }
        return route.fulfill({ json: snapshot })
      }
      lastPatch = request.postDataJSON()
      if (saveMode !== 'ok') return route.fulfill({ status: saveMode === 'fail' ? 500 : 409, json: { detail: { message: `test-only-${saveMode}` } } })
      const next = structuredClone(saved[id]); next.revision++
      for (const [group, edits] of Object.entries(lastPatch.prompts || {})) for (const [field, value] of Object.entries(edits)) { next.prompts[group][field] = value; next.prompts[group].overrides[field] = true }
      for (const edit of lastPatch.framing || []) for (const field of ['positive', 'negative']) if (Object.hasOwn(edit, field)) { const pair = next.levels[edit.level][edit.kind]; pair[field] = edit[field]; pair.overrides[field] = true }
      const held = saveGate; if (held) { held.seen(); await held.wait }; saved[id] = next
      return route.fulfill({ json: next })
    }
    if (path === '/api/admin/cpus' || path === '/api/local/play/roster-candidates') return route.fulfill({ json: cpus })
    if (path === '/api/local/packs/rescan') { scans++; const held = scanGate; if (held) { held.seen(); await held.wait }; return route.fulfill({ json: { registry: listing } }) }
    if (path === '/api/local/packs') return route.fulfill({ json: listing })
    if (path === '/api/profile/me') return route.fulfill({ json: { player_name: 'test-only', current_hp: null, max_hp: null } })
    if (path === '/api/local/play') return route.fulfill({ json: { generation: 'test-only', phase: 'roster_required', roster: [], ending_event_id: null, ending_payload: null, active_session_id: null, recent_session_id: null, legacy_active: false } })
    if (path === '/api/game/sessions/active') return route.fulfill({ json: null })
    if (path === '/api/local/sound-selection') return route.fulfill({ json: { effect_set_id: null, bgm_ids: [], effect_sets: [], tracks: [], effect_set_available: false, bgm_available: [] } })
    throw new Error(`Unexpected API: ${path}`)
  })
  await page.goto(process.env.TEST_BASE_URL || 'http://127.0.0.1:5173')
  await page.getByRole('button', { name: '캐릭터 프롬프트·팩 설정' }).click()
  const panel = page.getByRole('region', { name: '캐릭터 프롬프트와 팩 관리' })
  const select = panel.getByRole('combobox', { name: '캐릭터', exact: true })
  assert.equal(await select.inputValue(), '')
  await select.selectOption('1')
  const positive = panel.getByRole('group', { name: '외모', exact: true }).locator('textarea').first()
  const save = panel.locator('button.primary-button')
  await positive.waitFor()
  if (!process.argv.includes('--scan-only')) {
    // Failures/conflicts preserve drafts; only dirty strings are submitted.
    await positive.fill('test-only-draft')
    for (const mode of ['fail', 'conflict']) { saveMode = mode; await save.click(); await panel.getByRole('alert').filter({ hasText: `test-only-${mode}` }).waitFor(); assert.equal(await positive.inputValue(), 'test-only-draft') }
    saveMode = 'ok'; saveGate = gate(); await save.click(); await saveGate.entered
    assert.deepEqual(lastPatch, { expected_revision: 0, prompts: { appearance: { positive: 'test-only-draft' } } })
    const couldType = await positive.isEnabled()
    if (couldType) await positive.fill('test-only-after-save-click')
    const response = page.waitForResponse((r) => r.url().endsWith('/characters/1/content') && r.request().method() === 'PATCH')
    saveGate.release(); await response
    await page.waitForFunction(() => !document.querySelector('.content-editor button.primary-button')?.textContent.includes('저장 중'))
    assert.equal(await positive.inputValue(), couldType ? 'test-only-after-save-click' : 'test-only-draft', 'save response discarded input typed while pending')
    saveGate = undefined
    // Explicit empty edits and a late A save must not replace the B form.
    await positive.fill(''); saveGate = gate(); await save.click(); await saveGate.entered
    assert.equal(lastPatch.prompts.appearance.positive, '')
    await select.selectOption('2'); await page.waitForFunction(() => document.querySelector('.prompt-fields textarea')?.value === 'test-only-2')
    saveGate.release(); await page.waitForFunction(() => !document.querySelector('.content-editor button.primary-button')?.textContent.includes('저장 중'))
    assert.equal(await select.inputValue(), '2'); assert.equal(await positive.inputValue(), 'test-only-2'); saveGate = undefined
    // A late B GET cannot replace a newer A selection.
    await select.selectOption('1'); await page.waitForFunction(() => document.querySelector('.prompt-fields textarea')?.value === '')
    readGate = gate(); await select.selectOption('2'); await readGate.entered
    await select.selectOption('1'); await positive.waitFor(); readGate.release()
    await page.evaluate(() => new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r))))
    assert.equal(await select.inputValue(), '1'); assert.equal(await positive.inputValue(), '')
    // Framing edits keep their Level/kind/field identity and do not resubmit base prompts.
    const level = panel.locator('.framing-level').nth(2); await level.locator('summary').click()
    const framing = level.getByRole('group', { name: 'CG', exact: true }).locator('textarea').nth(1)
    await framing.fill('test-only-framing')
    const framingResponse = page.waitForResponse((r) => r.url().endsWith('/characters/1/content') && r.request().method() === 'PATCH')
    await save.click(); await framingResponse
    await page.waitForFunction(() => !document.querySelector('.content-editor button.primary-button')?.textContent.includes('저장 중'))
    assert.deepEqual(lastPatch, { expected_revision: 2, framing: [{ level: 2, kind: 'cg', negative: 'test-only-framing' }] })
    assert.equal(await framing.inputValue(), 'test-only-framing')
  }
  // Rapid tab re-entry reuses the in-flight scan.
  scanGate = gate(); await panel.getByRole('tab', { name: '팩 목록·진단' }).click(); await scanGate.entered
  await panel.getByRole('tab', { name: '캐릭터 편집' }).click(); await panel.getByRole('tab', { name: '팩 목록·진단' }).click()
  await page.evaluate(() => new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r))))
  scanGate.release(); await panel.getByRole('button', { name: '폴더 다시 검색' }).waitFor()
  assert.equal(scans, 1, 'pack tab re-entry submitted a duplicate in-flight scan')
  scanGate = undefined; await panel.getByRole('button', { name: '폴더 다시 검색' }).click()
  await panel.getByRole('button', { name: '폴더 다시 검색' }).waitFor(); assert.equal(scans, 2)
  listing.packs = [{ id: 'test-pack-uuid', kind: 'character', namespace: '', pack_id: 'test-pack', identity: ['character', '', 'test-pack'], status: 'normal', issues: [], registered_revision: { id: 'test-rev-1', revision: 1 }, applied_revision_id: null, revisions: [] }]
  await panel.getByRole('button', { name: '폴더 다시 검색' }).click()
  await panel.getByRole('button', { name: '폴더 다시 검색' }).waitFor()
  await panel.getByRole('tab', { name: '캐릭터 편집' }).click()
  const packSelect = panel.getByRole('combobox', { name: '연결할 캐릭터팩', exact: true })
  const apply = panel.getByRole('button', { name: '선택한 팩 연결·적용', exact: true })
  assert.equal(await packSelect.inputValue(), '')
  assert.equal(await apply.isEnabled(), false)
  await packSelect.selectOption('test-pack-uuid')
  await positive.fill('test-pending-draft')
  assert.equal(await apply.isEnabled(), false, 'unsaved edits must block application')
  await save.click(); await page.waitForFunction(() => !document.querySelector('.content-editor button.primary-button')?.textContent.includes('저장 중'))
  for (const mode of ['fail', 'conflict']) {
    applyMode = mode; await apply.click(); await panel.getByRole('alert').filter({ hasText: `test-apply-${mode}` }).waitFor()
    assert.equal(await positive.inputValue(), 'test-pending-draft')
    assert.equal(await packSelect.inputValue(), 'test-pack-uuid')
  }
  applyMode = 'ok'; applyGate = gate(); await apply.click(); await applyGate.entered
  assert.equal(await positive.isEnabled(), false)
  assert.equal(lastApplication.pack_id, 'test-pack-uuid'); assert.equal(lastApplication.registered_revision_id, 'test-rev-1')
  readGate = undefined
  await select.selectOption('2'); await page.waitForFunction(() => document.querySelector('.prompt-fields textarea')?.value === 'test-only-2')
  applyGate.release(); await page.waitForFunction(() => !document.querySelector('.content-editor button.primary-button')?.textContent.includes('저장 중'))
  assert.equal(await select.inputValue(), '2'); assert.equal(await positive.inputValue(), 'test-only-2')
  applyGate = undefined
  await select.selectOption('1'); await panel.getByText('연결된 팩: test-pack', { exact: false }).waitFor()
  assert.equal(await positive.inputValue(), 'test-pending-draft')
  const negative = panel.getByRole('group', { name: '외모', exact: true }).locator('textarea').nth(1)
  assert.equal(await negative.inputValue(), 'test-source-1-N')
  await negative.fill(''); await save.click()
  await page.waitForFunction(() => !document.querySelector('.content-editor button.primary-button')?.textContent.includes('저장 중'))
  listing.packs[0].registered_revision = { id: 'test-rev-2', revision: 2 }
  await panel.getByRole('button', { name: '연결할 팩 다시 검색' }).click()
  await panel.getByRole('button', { name: '연결할 팩 다시 검색' }).waitFor()
  assert.equal(await negative.inputValue(), '', 'rescan must not change edited values')
  const update = panel.getByRole('button', { name: '같은 팩의 등록 revision 적용', exact: true })
  await update.click(); await panel.getByText('적용 revision 2', { exact: false }).first().waitFor()
  assert.equal(await negative.inputValue(), ''); assert.equal(await positive.inputValue(), 'test-pending-draft')
  assert.equal(await panel.getByRole('group', { name: '하의 속옷', exact: true }).locator('textarea').first().inputValue(), 'test-source-2-P')
  assert.equal(await update.isEnabled(), false)
  assert.equal(applications, 4)
  await panel.getByRole('group', { name: '외모', exact: true }).getByText('적용한 팩 원본 P/N').click()
  await panel.getByText('Positive: test-source-2-P', { exact: true }).first().waitFor()
  if (process.env.TEST_SCREENSHOT) await page.screenshot({ path: process.env.TEST_SCREENSHOT, fullPage: true })
  assert.deepEqual(errors, [])
  console.log('PASS: dirty-only/empty saves, failure/conflict drafts, pending save, stale selection/save, scan deduplication, explicit pack link/update, empty overrides, source distinction and late application isolation')
} finally { await browser.close() }
