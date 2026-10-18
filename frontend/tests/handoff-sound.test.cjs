const { test } = require('node:test')
const assert = require('node:assert/strict')
const fs = require('node:fs')
const path = require('node:path')
const vm = require('node:vm')
const ts = require('typescript')

function load(name, mocks, globals = {}) {
  const source = fs.readFileSync(path.join(__dirname, '../src/components', name), 'utf8')
  const compiled = ts.transpileModule(source, {
    compilerOptions: { target: ts.ScriptTarget.ES2020, module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX },
  }).outputText
  const exports = {}
  vm.runInNewContext(compiled, {
    exports, require: name => {
      if (!(name in mocks)) throw Error('Unexpected import: ' + name)
      return mocks[name]
    }, ...globals,
  })
  return exports
}

function listener(responses, permissions = ['tally.services']) {
  let poll
  const urls = []
  const sounds = []
  const mocks = {
    react: { useRef: current => ({ current }) },
    '@tanstack/react-query': { useQuery: options => { poll = options.queryFn } },
    '@mantine/core': {},
    'lucide-react': {},
    '../api/client': { apiGet: async url => {
      urls.push(url)
      const next = responses.shift()
      if (next instanceof Error) throw next
      return next
    } },
    '../auth/usePermissions': { usePermissions: () => ({
      user: { id: 7, permissions, must_change_password: false },
      can: permission => permissions.includes(permission),
    }) },
    './useHandoffSound': { useHandoffSound: () => ({
      ready: true, enqueue: count => sounds.push(count),
    }) },
    'react/jsx-runtime': { jsx: (component, props) => component(props) },
  }
  load('HandoffSoundNotifications.tsx', mocks).HandoffSoundNotifications()
  return { get poll() { return poll }, urls, sounds }
}

test('both directions sound once per delivery, independently of queue size', async () => {
  const state = listener([
    { cursor: '8', keeper: 0, operator: 0 },
    { cursor: '11', keeper: 2, operator: 1 },
    { cursor: '11', keeper: 0, operator: 0 },
  ], ['tally.services', 'ghabz.issue'])
  await state.poll()
  assert.deepEqual(state.sounds, [])
  await state.poll()
  await state.poll()
  assert.deepEqual(state.sounds, [3, 0])
  assert.deepEqual(state.urls, [
    '/kartabl/handoff-events', '/kartabl/handoff-events?after=8',
    '/kartabl/handoff-events?after=11',
  ])
})

test('network failure keeps the last cursor for retry', async () => {
  const state = listener([
    { cursor: '2', keeper: 0, operator: 0 },
    Error('offline'), { cursor: '4', keeper: 0, operator: 2 },
  ], ['ghabz.issue'])
  await state.poll()
  await assert.rejects(state.poll(), /offline/)
  await state.poll()
  assert.deepEqual(state.sounds, [2])
  assert.equal(state.urls[1], state.urls[2])
})

test('unrelated roles do not poll or enable audio', () => {
  assert.equal(listener([], ['reports.view']).poll, undefined)
})

function audioHook() {
  const handlers = new Map()
  const timers = new Map()
  const contexts = []
  let nextTimer = 0
  let cleanup
  class AudioContext {
    constructor() {
      this.state = 'suspended'
      this.currentTime = 0
      this.notes = 0
      contexts.push(this)
    }
    async resume() { this.state = 'running'; this.onstatechange?.() }
    async close() { this.state = 'closed' }
    createOscillator() {
      this.notes++
      return { frequency: {}, connect() {}, disconnect() {}, start() {}, stop() {} }
    }
    createGain() {
      return {
        gain: { setValueAtTime() {}, exponentialRampToValueAtTime() {} },
        connect() {}, disconnect() {},
      }
    }
  }
  const window = {
    AudioContext,
    addEventListener: (type, fn) => handlers.set(type, fn),
    removeEventListener: type => handlers.delete(type),
    setTimeout: fn => { const id = ++nextTimer; timers.set(id, fn); return id },
    clearTimeout: id => timers.delete(id),
  }
  const hook = load('useHandoffSound.ts', {
    react: {
      useCallback: fn => fn,
      useRef: current => ({ current }),
      useState: initial => [initial, () => {}],
      useEffect: fn => { cleanup = fn() },
    },
  }, { window }).useHandoffSound(true)
  const tick = () => {
    const [id, fn] = timers.entries().next().value
    timers.delete(id)
    fn()
  }
  return { hook, contexts, timers, handlers, tick, cleanup: () => cleanup() }
}

test('blocked audio queues each chime until a user enables sound', async () => {
  const state = audioHook()
  state.hook.enqueue(3)
  assert.equal(state.contexts.length, 0)
  await state.hook.enable()
  assert.equal(state.contexts.length, 1)
  assert.equal(state.contexts[0].notes, 2)
  state.tick()
  assert.equal(state.contexts[0].notes, 4)
  state.tick()
  assert.equal(state.contexts[0].notes, 6)
  state.tick()
  assert.equal(state.timers.size, 0)
  state.cleanup()
})

test('browser suspension preserves the remaining chimes until resumed', async () => {
  const state = audioHook()
  await state.hook.enable()
  state.hook.enqueue(2)
  state.contexts[0].state = 'suspended'
  state.tick()
  assert.equal(state.contexts[0].notes, 2)
  await state.hook.enable()
  assert.equal(state.contexts.length, 1)
  assert.equal(state.contexts[0].notes, 4)
  state.cleanup()
  assert.equal(state.timers.size, 0)
  assert.equal(state.handlers.size, 0)
  assert.equal(state.contexts[0].state, 'closed')
})
