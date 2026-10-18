import assert from 'node:assert/strict'
import { createRequire } from 'node:module'
const { chromium } = createRequire(import.meta.url)(process.env.PLAYWRIGHT_MODULE_PATH || 'playwright')
const browser = await chromium.launch({ headless: true, executablePath: process.env.TEST_CHROMIUM_EXECUTABLE || undefined })
function gate() { let release, seen; return { wait: new Promise((r) => { release = r }), entered: new Promise((r) => { seen = r }), release: () => release(), seen: () => seen() } }
function content(id) {
  const pair = () => ({ positive: '', negative: '', overrides: { positive: false, negative: false } })
  const prompts = Object.fromEntries(['appearance', 'upper_underwear', 'lower_underwear'].map((key) => [key, pair()]))
  prompts.appearance.positive = `test-only-${id}`
  return { schema_version: 1, cpu_id: id, revision: 0, pack_revision_id: null, pack: null, pack_source: null, measurements_cm: { height: null, bust: null, waist: null, hips: null }, measurement_overrides: { height: false, bust: false, waist: false, hips: false }, prompts, levels: Object.fromEntries([0, 1, 2, 3].map((level) => [level, Object.fromEntries(['profile', 'full_body', 'cg'].map((kind) => [kind, { ...pair(), revision: 0 }]))])) }
}
try {
  const page = await browser.newPage(); page.setDefaultTimeout(8000)
  const errors = []; page.on('pageerror', (e) => errors.push(e.message))
  page.on('dialog', (dialog) => void dialog.accept())
  await page.addInitScript(() => { window.nrnfDesktop = { isDesktop: true } })
  const saved = { 1: content(1), 2: content(2), 3: content(3) }
  saved[1].measurements_cm = { height: '170.0', bust: null, waist: '62.5', hips: null }
  const cpus = [1, 2, 3].map((id) => ({ id, slug: `cpu-${id}`, name: `CPU ${id}`, defeat_stage: 0, style: 'balanced', short_description: 'test-only', profile_image_key: null, measurements_cm: id === 1 ? { height: '170.0', bust: null, waist: '62.5', hips: null } : { height: null, bust: null, waist: null, hips: null } }))
  let saveMode = 'ok', loseSaveResponse = false, saveGate, saveGateCommitFirst = false, readGate, scanGate, scans = 0, lastPatch, applyGate, applyGateCommitFirst = false, applyMode = 'ok', loseApplyResponse = false, lastApplication, applications = 0
  let sharedSequence = 0, sharedItems = [], sharedDefaults = {}, sharedCandidateRows = {}
  const sharedKey = (cpuId, level, kind) => `${cpuId}:${level}:${kind}`
  const sharedDefaultKey = (level, kind) => `${level}:${kind}`
  const sharedCandidate = (cpuId, level, kind) => {
    const key = sharedKey(cpuId, level, kind), row = sharedCandidateRows[key]
    const stored = row?.item_ids ?? []
    const explicit = stored.map((id) => sharedItems.find((item) => item.id === id && item.active && item.level === level && item.kind === kind)).filter(Boolean)
    const fallback = sharedDefaults[sharedDefaultKey(level, kind)]
    const usingDefault = explicit.length === 0
    const effective = usingDefault ? sharedItems.filter((item) => item.id === fallback?.item_id && item.active && item.level === level && item.kind === kind) : explicit
    return { cpu_id: cpuId, level, kind, revision: row?.revision ?? 0, stored_item_ids: stored,
      effective_items: effective, uses_default: usingDefault, default_revision: fallback?.revision ?? 0, unregistered: effective.length === 0 }
  }
  const listing = { schema_version: 1, packs: [], scan_entries: [] }
  await page.route('**/api/**', async (route) => {
    const request = route.request(), path = new URL(request.url()).pathname
    if (path === '/api/local/shared-prompts') {
      const query = new URL(request.url()).searchParams
      const kind = query.get('kind'), level = Number(query.get('level'))
      if (request.method() === 'GET') return route.fulfill({ json: { items: sharedItems.filter((item) => item.active && item.kind === kind && item.level === level) } })
      const body = request.postDataJSON(), item = { id: `shared-${++sharedSequence}`, ...body, revision: 1, active: true }
      sharedItems.push(item); return route.fulfill({ json: item })
    }
    const sharedItemPath = path.match(/^\/api\/local\/shared-prompts\/([^/]+)$/)
    if (sharedItemPath && request.method() === 'PATCH') {
      const item = sharedItems.find((value) => value.id === sharedItemPath[1]), body = request.postDataJSON()
      Object.assign(item, Object.fromEntries(Object.entries(body).filter(([key]) => key !== 'expected_revision'))); item.revision++
      return route.fulfill({ json: item })
    }
    const sharedDefaultPath = path.match(/^\/api\/local\/shared-prompt-defaults\/(\d+)\/(clothing_state|pose)$/)
    if (sharedDefaultPath) {
      const level = Number(sharedDefaultPath[1]), kind = sharedDefaultPath[2], key = sharedDefaultKey(level, kind)
      if (request.method() === 'GET') { const row = sharedDefaults[key]; return route.fulfill({ json: { level, kind, revision: row?.revision ?? 0, item_id: row?.item_id ?? null, valid: !!row?.item_id, item: sharedItems.find((item) => item.id === row?.item_id) ?? null } }) }
      const body = request.postDataJSON(), row = sharedDefaults[key]
      if (body.expected_revision !== (row?.revision ?? 0)) return route.fulfill({ status: 409, json: { detail: { message: 'test default conflict' } } })
      sharedDefaults[key] = { item_id: body.item_id, revision: (row?.revision ?? 0) + 1 }
      return route.fulfill({ json: { level, kind, ...sharedDefaults[key], valid: !!body.item_id, item: sharedItems.find((item) => item.id === body.item_id) ?? null } })
    }
    const sharedCandidatesPath = path.match(/^\/api\/local\/characters\/(\d+)\/prompt-candidates\/(\d+)\/(clothing_state|pose)$/)
    if (sharedCandidatesPath) {
      const cpuId = Number(sharedCandidatesPath[1]), level = Number(sharedCandidatesPath[2]), kind = sharedCandidatesPath[3], key = sharedKey(cpuId, level, kind)
      if (request.method() === 'GET') return route.fulfill({ json: sharedCandidate(cpuId, level, kind) })
      const body = request.postDataJSON(), row = sharedCandidateRows[key]
      if (body.expected_revision !== (row?.revision ?? 0)) return route.fulfill({ status: 409, json: { detail: { message: 'test candidate conflict' } } })
      sharedCandidateRows[key] = { item_ids: body.item_ids, revision: (row?.revision ?? 0) + 1 }
      return route.fulfill({ json: sharedCandidate(cpuId, level, kind) })
    }
    const changePreviewPath = path.match(/^\/api\/local\/shared-prompts\/([^/]+)\/change-preview$/)
    if (changePreviewPath) {
      const item = sharedItems.find((value) => value.id === changePreviewPath[1]), body = request.postDataJSON()
      const candidate_changes = Object.entries(sharedCandidateRows).filter(([key, row]) => key.endsWith(`:${item.level}:${item.kind}`) && row.item_ids.includes(item.id)).map(([key, row]) => ({ cpu_id: Number(key.split(':')[0]), cpu_name: `CPU ${key.split(':')[0]}`, cpu_slug: `cpu-${key.split(':')[0]}`, candidate_set_id: key, candidate_revision: row.revision, stored_item_ids: row.item_ids, after_item_ids: row.item_ids.filter((id) => id !== item.id), after_effective_item_ids: [], uses_default_after: true, fallback_item_id: null, unregistered_after: true }))
      const defaultRow = sharedDefaults[sharedDefaultKey(item.level, item.kind)]
      return route.fulfill({ json: { item: { id: item.id, kind: item.kind, level: item.level, label: item.label, revision: item.revision }, action: body.action, target_level: body.target_level ?? null, preview_digest: 'a'.repeat(64), candidate_changes, candidate_scope_snapshot: [], affected_cpus: [], source_default: { item_id: defaultRow?.item_id ?? null, revision: defaultRow?.revision ?? 0, after_item_id: null, after_item_revision: null, will_clear: defaultRow?.item_id === item.id }, new_level: body.target_level ? { level: body.target_level, candidate_auto_inclusion: false, default_auto_assignment: false } : null } })
    }
    const changeConfirmPath = path.match(/^\/api\/local\/shared-prompts\/([^/]+)\/change-confirmation$/)
    if (changeConfirmPath) {
      const item = sharedItems.find((value) => value.id === changeConfirmPath[1]), body = request.postDataJSON()
      for (const [key, row] of Object.entries(sharedCandidateRows)) {
        if (row.item_ids.includes(item.id) && key.endsWith(`:${item.level}:${item.kind}`)) {
          row.item_ids = row.item_ids.filter((id) => id !== item.id); row.revision++
        }
      }
      const defaultKey = sharedDefaultKey(item.level, item.kind), fallback = sharedDefaults[defaultKey]
      if (fallback?.item_id === item.id) { fallback.item_id = null; fallback.revision++ }
      if (body.action === 'move') item.level = body.target_level; else item.active = false
      item.revision++
      return route.fulfill({ json: { item, action: body.action, confirmed: true, changed_candidate_sets: 0, cleared_default: false } })
    }
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
      const hips = next.pack.applied_revision >= 4 ? '95.4' : '94.2'
      next.pack_source = { prompts: {}, levels: {}, metadata: { name: 'test-only', adult: true, measurements_cm: { height: '171', bust: '88.5', waist: '65', hips } } }
      for (const key of ['height', 'bust', 'waist', 'hips']) if (!next.measurement_overrides[key]) next.measurements_cm[key] = ({ height: '171.0', bust: '88.5', waist: '65.0', hips: key === 'hips' ? hips : '94.2' })[key]
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
      const held = applyGate
      if (held && applyGateCommitFirst) saved[id] = next
      if (held) { held.seen(); await held.wait }
      if (!held || !applyGateCommitFirst) saved[id] = next
      if (loseApplyResponse) { loseApplyResponse = false; return route.abort() }
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
      for (const [key, value] of Object.entries(lastPatch.measurements_cm || {})) { next.measurements_cm[key] = value; next.measurement_overrides[key] = true }
      const held = saveGate
      if (held && saveGateCommitFirst) saved[id] = next
      if (held) { held.seen(); await held.wait }
      if (!held || !saveGateCommitFirst) saved[id] = next
      if (loseSaveResponse) { loseSaveResponse = false; return route.abort() }
      return route.fulfill({ json: next })
    }
    if (path === '/api/admin/cpus') return route.fulfill({ json: cpus })
    if (path === '/api/local/play/roster-candidates') return route.fulfill({ json: cpus.map((cpu) => ({ ...cpu, content_revision: saved[cpu.id].revision, measurements_cm: saved[cpu.id].measurements_cm })) })
    if (path === '/api/local/packs/rescan') { scans++; const held = scanGate; if (held) { held.seen(); await held.wait }; return route.fulfill({ json: { registry: listing } }) }
    if (path === '/api/local/packs') return route.fulfill({ json: listing })
    if (path === '/api/profile/me') return route.fulfill({ json: { player_name: 'test-only', current_hp: null, max_hp: null } })
    if (path === '/api/local/play/roster' && request.method() === 'POST') return route.fulfill({ json: { generation: 'test-game', phase: 'progress', roster: cpus.map((cpu) => ({ cpu_character_id: cpu.id, defeat_stage: 0 })), ending_event_id: null, ending_payload: null, active_session_id: null, recent_session_id: null, legacy_active: false } })
    if (path === '/api/local/play/reset' && request.method() === 'POST') return route.fulfill({ json: { generation: 'test-reset', phase: 'roster_required', roster: [], ending_event_id: null, ending_payload: null, active_session_id: null, recent_session_id: null, legacy_active: false } })
    if (path === '/api/local/play') return route.fulfill({ json: { generation: 'test-only', phase: 'roster_required', roster: [], ending_event_id: null, ending_payload: null, active_session_id: null, recent_session_id: null, legacy_active: false } })
    if (path === '/api/game/sessions' && request.method() === 'POST') return route.fulfill({ json: { session_id: 'test-game-session', generation: 'test-game', players: [{ seat: 0, name: 'test-only', isHuman: true }, ...cpus.map((cpu, index) => ({ seat: index + 1, name: cpu.name, isHuman: false }))] } })
    if (path === '/api/game/sessions/active') return route.fulfill({ json: null })
    if (path === '/api/local/sound-selection') return route.fulfill({ json: { effect_set_id: null, bgm_ids: [], effect_sets: [], tracks: [], effect_set_available: false, bgm_available: [] } })
    throw new Error(`Unexpected API: ${path}`)
  })
  await page.goto(process.env.TEST_BASE_URL || 'http://127.0.0.1:5173')
  await page.getByText('키 170.0 cm', { exact: true }).waitFor()
  assert.equal(await page.getByText('가슴(B)', { exact: true }).count(), 0, 'selection card must omit unset measurement rows')
  const cpuCards = page.locator('.cpu-card')
  for (let index = 0; index < 3; index++) await cpuCards.nth(index).click()
  assert.equal(await page.locator('.cpu-card.selected').count(), 3, 'test must retain the full selected CPU list')
  await page.getByRole('button', { name: '캐릭터 프롬프트·팩 설정' }).click()
  let panel = page.getByRole('region', { name: '캐릭터 프롬프트와 팩 관리' })
  const select = panel.getByRole('combobox', { name: '캐릭터', exact: true })
  assert.equal(await select.inputValue(), '')
  await select.selectOption('1')
  await panel.getByRole('tab', { name: '공유 복장·포즈' }).click()
  const sharedLabel = panel.getByRole('textbox', { name: '공유 항목 표시 이름' })
  await sharedLabel.fill('test-only-shared-prompt')
  await panel.getByRole('textbox', { name: '공유 항목 Positive' }).fill('  test-only P\n<lora:fixture:0.7>  ')
  await panel.getByRole('tab', { name: '캐릭터 편집' }).click()
  await panel.getByRole('tab', { name: '공유 복장·포즈' }).click()
  assert.equal(await sharedLabel.inputValue(), 'test-only-shared-prompt', 'switching editor tabs must preserve a pending shared item draft')
  await panel.getByRole('button', { name: '공유 항목 추가' }).click()
  const sharedItemButton = panel.getByRole('button', { name: 'test-only-shared-prompt', exact: true })
  await sharedItemButton.waitFor()
  const sharedItem = sharedItems.find((item) => item.label === 'test-only-shared-prompt')
  assert.equal(sharedItem.positive, '  test-only P\n<lora:fixture:0.7>  ', 'shared prompt whitespace and newline must be preserved')
  await panel.getByRole('combobox', { name: '지정 기본 항목' }).selectOption(sharedItem.id)
  const defaultWrite = page.waitForResponse((response) => response.url().includes('/shared-prompt-defaults/0/clothing_state') && response.request().method() === 'PUT')
  await panel.getByRole('button', { name: '기본값 저장' }).click()
  await defaultWrite
  const candidateCheck = panel.locator('.shared-candidate-list label').filter({ hasText: 'test-only-shared-prompt' }).locator('input')
  await candidateCheck.check()
  const candidateWrite = page.waitForResponse((response) => response.url().includes('/prompt-candidates/0/clothing_state') && response.request().method() === 'PUT')
  await panel.getByRole('button', { name: '캐릭터 후보 저장' }).click()
  await candidateWrite
  assert.ok(sharedCandidateRows['1:0:clothing_state']?.item_ids.includes(sharedItem.id))
  assert.equal(sharedCandidate(1, 0, 'clothing_state').uses_default, false, 'explicit candidate must take precedence over the configured default')
  await panel.getByRole('button', { name: '영향 확인' }).click()
  await panel.getByRole('region', { name: '변경 영향 확인' }).waitFor()
  await panel.getByRole('button', { name: '확인 후 이동' }).click()
  await page.waitForFunction(() => !document.querySelector('.shared-prompt-list button'))
  assert.equal(sharedCandidateRows['1:0:clothing_state'].item_ids.length, 0, 'confirmed move must detach the source candidate')
  await panel.getByRole('tab', { name: '공유 복장·포즈' }).click()
  const sharedLevelSelect = panel.locator('.shared-prompt-controls select').first()
  await sharedLevelSelect.selectOption('1')
  await panel.getByRole('button', { name: 'test-only-shared-prompt', exact: true }).waitFor()
  assert.equal(sharedCandidate(1, 1, 'clothing_state').unregistered, true, 'a moved item must not be auto-attached at its target level')
  await sharedLevelSelect.selectOption('0')
  await panel.getByRole('tab', { name: '캐릭터 편집' }).click()
  const positive = panel.getByRole('group', { name: '외모', exact: true }).locator('textarea').first()
  const save = panel.locator('.content-editor:not(.shared-prompt-manager) button.primary-button')
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
    await panel.locator('input[aria-label="키 (cm)"]').fill('172.4')
    const measurementResponse = page.waitForResponse((r) => r.url().endsWith('/characters/1/content') && r.request().method() === 'PATCH')
    await save.click(); await measurementResponse
    await page.waitForFunction(() => !document.querySelector('.content-editor button.primary-button')?.textContent.includes('저장 중'))
    assert.deepEqual(lastPatch, { expected_revision: 3, measurements_cm: { height: '172.4' } })
    assert.equal(await panel.locator('input[aria-label^="키"]').inputValue(), '172.4')
    await page.getByText('키 172.4 cm', { exact: true }).waitFor({ timeout: 1000 })
    assert.equal(await page.locator('.cpu-card.selected').count(), 3, 'saving measurements must preserve selected CPUs')
    await panel.locator('input[aria-label="키 (cm)"]').fill('')
    const clearResponse = page.waitForResponse((r) => r.url().endsWith('/characters/1/content') && r.request().method() === 'PATCH')
    await save.click(); await clearResponse
    await page.waitForFunction(() => !document.querySelector('.content-editor button.primary-button')?.textContent.includes('저장 중'))
    assert.deepEqual(lastPatch, { expected_revision: 4, measurements_cm: { height: null } })
    assert.equal(await page.getByText('키 172.4 cm', { exact: true }).count(), 0, 'cleared measurement must disappear from the selection card')
    assert.equal(await page.locator('.cpu-card.selected').count(), 3, 'clearing measurements must preserve selected CPUs')
    // The server commits before delaying only the old response. Reopening, reloading,
    // and saving again must establish a newer per-character revision for the card.
    await panel.locator('input[aria-label="키 (cm)"]').fill('175.1')
    const oldSaveGate = gate(); saveGate = oldSaveGate; saveGateCommitFirst = true; await save.click(); await oldSaveGate.entered
    saveGate = undefined
    const oldSaveResponse = page.waitForResponse((r) => r.url().endsWith('/characters/1/content') && r.request().method() === 'PATCH', { timeout: 30000 })
    await panel.getByRole('button', { name: '닫기', exact: true }).click()
    await page.getByRole('button', { name: '캐릭터 프롬프트·팩 설정' }).click()
    const reopened = page.getByRole('region', { name: '캐릭터 프롬프트와 팩 관리' })
    panel = reopened
    const reopenedSelect = reopened.getByRole('combobox', { name: '캐릭터', exact: true })
    await reopenedSelect.selectOption('1')
    await reopened.locator('input[aria-label="키 (cm)"]').waitFor()
    await reopened.locator('input[aria-label="키 (cm)"]').fill('176.2')
    const newerSaveResponse = page.waitForResponse((r) => r.url().endsWith('/characters/1/content') && r.request().method() === 'PATCH')
    await reopened.locator('button.primary-button').click(); await newerSaveResponse
    await page.getByText('키 176.2 cm', { exact: true }).waitFor()
    oldSaveGate.release(); saveGateCommitFirst = false; await oldSaveResponse
    await page.evaluate(() => new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r))))
    assert.equal(await page.getByText('키 176.2 cm', { exact: true }).count(), 1, 'older save response must not overwrite the newer card value after settings re-entry')
    assert.equal(await page.locator('.cpu-card.selected').count(), 3, 'stale save must preserve selected CPUs')
    await reopened.locator('input[aria-label="키 (cm)"]').fill('')
    const clearAfterRace = page.waitForResponse((r) => r.url().endsWith('/characters/1/content') && r.request().method() === 'PATCH')
    await reopened.locator('button.primary-button').click(); await clearAfterRace
    assert.equal(await page.getByText('키 176.2 cm', { exact: true }).count(), 0, 'clear after a revision race must update the card')
    // A lost save response leaves the client cache behind the committed server
    // revision. Reset re-queries roster candidates and must adopt the server value.
    await reopened.locator('input[aria-label="허리(W) (cm)"]').fill('66.6')
    loseSaveResponse = true
    const lostSave = page.waitForEvent('requestfailed', { predicate: (request) => request.url().endsWith('/characters/1/content') && request.method() === 'PATCH' })
    await reopened.locator('button.primary-button').click(); await lostSave
    await reopened.getByRole('alert').waitFor()
    assert.equal(await page.locator('.cpu-card.selected').count(), 3, 'lost save response must not change CPU selection before reset')
    await reopened.getByRole('button', { name: '닫기', exact: true }).click()
    await page.getByRole('button', { name: '진행 초기화', exact: true }).click()
    await page.getByText('허리(W) 66.6 cm', { exact: true }).waitFor()
    assert.equal(await page.locator('.cpu-card.selected').count(), 0, 'reset still clears selected CPUs')
    for (let index = 0; index < 3; index++) await page.locator('.cpu-card').nth(index).click()
    assert.equal(await page.locator('.cpu-card.selected').count(), 3)
    await page.getByRole('button', { name: '캐릭터 프롬프트·팩 설정' }).click()
    panel = page.getByRole('region', { name: '캐릭터 프롬프트와 팩 관리' })
    await panel.getByRole('combobox', { name: '캐릭터', exact: true }).selectOption('1')
    await panel.locator('input[aria-label="키 (cm)"]').waitFor()
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
  assert.equal(await panel.locator('input[aria-label^="키"]').inputValue(), '', 'directly cleared measurement must survive first pack application')
  assert.equal(await page.getByText('키 172.4 cm', { exact: true }).count(), 0, 'pack application must not restore a cleared measurement on the card')
  await page.getByText('가슴(B) 88.5 cm', { exact: true }).waitFor({ timeout: 1000 })
  assert.equal(await page.locator('.cpu-card.selected').count(), 3, 'applying a pack must preserve selected CPUs')
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
  assert.equal(await panel.locator('input[aria-label^="키"]').inputValue(), '', 'directly cleared measurement must survive pack revision update')
  assert.equal(await panel.locator('input[aria-label^="가슴(B)"]').inputValue(), '88.5')
  assert.equal(await panel.getByRole('group', { name: '하의 속옷', exact: true }).locator('textarea').first().inputValue(), 'test-source-2-P')
  assert.equal(await update.isEnabled(), false)
  // Pack application also commits before delaying only its response. Re-entering
  // settings, then saving a measurement, must keep the new value after the old apply.
  listing.packs[0].registered_revision = { id: 'test-rev-3', revision: 3 }
  await panel.getByRole('button', { name: '연결할 팩 다시 검색' }).click()
  await panel.getByRole('button', { name: '연결할 팩 다시 검색' }).waitFor()
  const delayedApplyGate = gate(); applyGate = delayedApplyGate; applyGateCommitFirst = true
  await panel.getByRole('button', { name: '같은 팩의 등록 revision 적용', exact: true }).click()
  await delayedApplyGate.entered; applyGate = undefined
  const oldApplyResponse = page.waitForResponse((r) => r.url().endsWith('/characters/1/pack-application') && r.request().method() === 'POST', { timeout: 30000 })
  await panel.getByRole('button', { name: '닫기', exact: true }).click()
  await page.getByRole('button', { name: '캐릭터 프롬프트·팩 설정' }).click()
  panel = page.getByRole('region', { name: '캐릭터 프롬프트와 팩 관리' })
  const reenteredSelect = panel.getByRole('combobox', { name: '캐릭터', exact: true })
  await reenteredSelect.selectOption('1')
  await panel.locator('input[aria-label^="가슴(B)"]').waitFor()
  await panel.locator('input[aria-label^="가슴(B)"]').fill('89.7')
  const newerPackSave = page.waitForResponse((r) => r.url().endsWith('/characters/1/content') && r.request().method() === 'PATCH')
  await panel.locator('button.primary-button').click(); await newerPackSave
  await page.getByText('가슴(B) 89.7 cm', { exact: true }).waitFor()
  delayedApplyGate.release(); await oldApplyResponse
  await page.evaluate(() => new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r))))
  assert.equal(await page.getByText('가슴(B) 89.7 cm', { exact: true }).count(), 1, 'older pack response must not overwrite a newer card value after settings re-entry')
  assert.equal(await page.locator('.cpu-card.selected').count(), 3, 'stale pack response must preserve selected CPUs')
  assert.equal(applications, 5)
  // A committed pack application whose response is lost must be recovered from
  // server revision data on the next roster query after reset.
  listing.packs[0].registered_revision = { id: 'test-rev-4', revision: 4 }
  await panel.getByRole('button', { name: '연결할 팩 다시 검색' }).click()
  await panel.getByRole('button', { name: '연결할 팩 다시 검색' }).waitFor()
  loseApplyResponse = true
  const lostApply = page.waitForEvent('requestfailed', { predicate: (request) => request.url().endsWith('/characters/1/pack-application') && request.method() === 'POST' })
  await panel.getByRole('button', { name: '같은 팩의 등록 revision 적용', exact: true }).click(); await lostApply
  await panel.getByRole('alert').waitFor()
  assert.equal(await page.getByText('엉덩이(H) 94.2 cm', { exact: true }).count(), 1, 'card remains at the last known revision until roster re-query')
  await panel.getByRole('button', { name: '닫기', exact: true }).click()
  await page.getByRole('button', { name: '진행 초기화', exact: true }).click()
  await page.getByText('엉덩이(H) 95.4 cm', { exact: true }).waitFor()
  assert.equal(await page.locator('.cpu-card.selected').count(), 0, 'reset clears selection while recovering committed pack measurements')
  for (let index = 0; index < 3; index++) await page.locator('.cpu-card').nth(index).click()
  assert.equal(await page.locator('.cpu-card.selected').count(), 3)
  await page.getByRole('button', { name: '캐릭터 프롬프트·팩 설정' }).click()
  panel = page.getByRole('region', { name: '캐릭터 프롬프트와 팩 관리' })
  await panel.getByRole('combobox', { name: '캐릭터', exact: true }).selectOption('1')
  await panel.getByText('연결된 팩: test-pack', { exact: false }).waitFor()
  await panel.getByRole('group', { name: '외모', exact: true }).getByText('적용한 팩 원본 P/N').click()
  await panel.getByText('Positive: test-source-4-P', { exact: true }).first().waitFor()
  // A measurement response arriving after the game starts must not restore the selection screen.
  await panel.locator('input[aria-label="키 (cm)"]').fill('173.3')
  saveGate = gate(); await save.click(); await saveGate.entered
  await panel.getByRole('button', { name: '닫기', exact: true }).click()
  await page.getByRole('button', { name: '참가 명단 확정', exact: true }).click()
  await page.getByRole('button', { name: '동풍전 시작', exact: true }).waitFor()
  for (let index = 0; index < 3; index++) await page.locator('.cpu-card').nth(index).click()
  await page.getByRole('button', { name: '동풍전 시작', exact: true }).click()
  await page.locator('.game-toolbar').waitFor()
  assert.equal(await page.locator('.cpu-grid').count(), 0)
  const lateMeasurementResponse = page.waitForResponse((response) => response.url().endsWith('/characters/1/content') && response.request().method() === 'PATCH')
  saveGate.release(); saveGate = undefined
  await lateMeasurementResponse
  await page.evaluate(() => new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve))))
  assert.equal(await page.locator('.cpu-grid').count(), 0, 'late measurement save must not restore selection screen after game start')
  assert.equal(await page.locator('.game-toolbar').count(), 1, 'late measurement save must preserve the current game')
  await page.getByRole('button', { name: '캐릭터 프롬프트·팩 설정', exact: true }).click()
  const resetPanel = page.getByRole('region', { name: '캐릭터 프롬프트와 팩 관리' })
  await resetPanel.getByRole('combobox', { name: '캐릭터', exact: true }).selectOption('1')
  await resetPanel.locator('input[aria-label="키 (cm)"]').fill('174.0')
  saveGate = gate(); await resetPanel.locator('button.primary-button').click(); await saveGate.entered
  await resetPanel.getByRole('button', { name: '닫기', exact: true }).click()
  await page.getByRole('button', { name: '초기화', exact: true }).click()
  await page.locator('.cpu-grid').waitFor()
  assert.equal(await page.locator('.cpu-card.selected').count(), 0, 'reset must clear the CPU selection before the late response')
  const lateResetResponse = page.waitForResponse((response) => response.url().endsWith('/characters/1/content') && response.request().method() === 'PATCH')
  saveGate.release(); saveGate = undefined
  await lateResetResponse
  await page.evaluate(() => new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve))))
  assert.equal(await page.locator('.cpu-grid').count(), 1, 'late measurement save must not change the reset selection screen')
  assert.equal(await page.locator('.cpu-card.selected').count(), 0, 'late measurement save must not restore pre-reset CPU selections')
  await page.getByText('가슴(B) 89.7 cm', { exact: true }).waitFor()
  assert.equal(await page.getByText('가슴(B) 89.7 cm', { exact: true }).count(), 1, 'roster re-query after reset must retain the newest cached revision value')
  assert.equal(await page.locator('.game-toolbar').count(), 0)
  if (process.env.TEST_SCREENSHOT) await page.screenshot({ path: process.env.TEST_SCREENSHOT, fullPage: true })
  assert.deepEqual(errors, [])
  console.log('PASS: dirty-only/empty saves, failure/conflict drafts, pending save, stale selection/save/pack revision guards, settings re-entry, scan deduplication, immediate save/clear/pack card updates, selection preservation and late-response isolation after reset/game start')
} finally { await browser.close() }
