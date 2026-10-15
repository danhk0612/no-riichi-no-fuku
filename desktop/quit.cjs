function createQuitCoordinator({ app, stopEngine, onStart = () => {}, onFailure = () => {}, onComplete = () => {}, exit }) {
  let shutdownPromise
  let finalQuitAllowed = false

  function requestQuit(reason = 'requested') {
    if (shutdownPromise) return shutdownPromise
    shutdownPromise = (async () => {
      await onStart(reason)
      await stopEngine()
      finalQuitAllowed = true
      await onComplete(reason)
      if (exit) exit()
      else app.quit()
      return true
    })().catch(error => {
      shutdownPromise = undefined
      onFailure(error, reason)
      return false
    })
    return shutdownPromise
  }

  app.on('before-quit', event => {
    if (finalQuitAllowed) return
    event.preventDefault()
    void requestQuit('app-quit')
  })
  app.on('window-all-closed', () => {
    if (finalQuitAllowed) return
    void requestQuit('window-all-closed')
  })

  return {
    requestQuit,
    get finalQuitAllowed() { return finalQuitAllowed },
    get shutdownPromise() { return shutdownPromise },
  }
}

module.exports = { createQuitCoordinator }
