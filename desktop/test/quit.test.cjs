const assert = require('node:assert/strict')
const { EventEmitter } = require('node:events')
const test = require('node:test')
const { createQuitCoordinator } = require('../quit.cjs')

function fakeApp() {
  const app = new EventEmitter()
  app.exited = false
  app.quit = () => {
    const event = { prevented: false, preventDefault() { this.prevented = true } }
    app.emit('before-quit', event)
    if (!event.prevented) app.exited = true
  }
  return app
}

function deferred() {
  let resolve
  let reject
  const promise = new Promise((yes, no) => { resolve = yes; reject = no })
  return { promise, resolve, reject }
}

test('window close and app.quit share one shutdown and wait for the owned engine', async () => {
  const app = fakeApp()
  const gate = deferred()
  const events = []
  let stopCalls = 0
  const quit = createQuitCoordinator({
    app,
    stopEngine: async () => { stopCalls += 1; events.push('engine-close-start'); await gate.promise; events.push('engine-close') },
    onStart: reason => events.push(`input-stopped:${reason}`),
    onComplete: () => events.push('final-close'),
  })

  const windowClose = quit.requestQuit('window-close')
  app.quit()
  app.emit('window-all-closed')
  await Promise.resolve()
  assert.equal(app.exited, false)
  assert.equal(stopCalls, 1)
  assert.deepEqual(events, ['input-stopped:window-close', 'engine-close-start'])

  gate.resolve()
  await windowClose
  assert.equal(app.exited, true)
  assert.equal(events.at(-2), 'engine-close')
  assert.equal(events.at(-1), 'final-close')
})

test('delayed and repeated app.quit requests re-enter the same shutdown', async () => {
  const app = fakeApp()
  const gate = deferred()
  let stopCalls = 0
  const quit = createQuitCoordinator({ app, stopEngine: async () => { stopCalls += 1; await gate.promise } })
  app.quit()
  const first = quit.shutdownPromise
  app.quit()
  app.quit()
  await Promise.resolve()
  assert.equal(app.exited, false)
  assert.equal(stopCalls, 1)
  gate.resolve()
  await first
  assert.equal(app.exited, true)
})

test('failed timeout cleanup never permits Electron exit and a later close can retry', async () => {
  const app = fakeApp()
  const events = []
  let attempts = 0
  const quit = createQuitCoordinator({
    app,
    stopEngine: async () => {
      attempts += 1
      if (attempts === 1) throw new Error('owned child was not reaped')
      events.push('owned child close observed')
    },
    onFailure: error => events.push(`shutdown-failed:${error.message}`),
  })

  app.quit()
  await quit.shutdownPromise
  assert.equal(app.exited, false)
  assert.equal(quit.finalQuitAllowed, false)
  assert.match(events[0], /shutdown-failed/)

  await quit.requestQuit('retry')
  assert.equal(app.exited, true)
  assert.equal(attempts, 2)
  assert.equal(events[1], 'owned child close observed')
})
