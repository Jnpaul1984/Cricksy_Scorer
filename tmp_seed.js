const { seedMatch } = require('./frontend/cypress/support/matchSimulator.runtime.js')
const origFetch = global.fetch
if (!origFetch) {
  throw new Error('fetch not available')
}

global.fetch = async (input, init = {}) => {
  const method = init.method || 'GET'
  const body = typeof init.body === 'string' ? init.body : ''
  console.log('fetch', method, input)
  if (body) {
    console.log(' body', body.slice(0, 120))
  }
  const res = await origFetch(input, init)
  const text = await res.clone().text()
  console.log(' status', res.status, res.statusText)
  if (text) {
    console.log(' response', text.slice(0, 200))
  }
  return res
}

seedMatch('http://127.0.0.1:8000', 'C:/Users/SRLF/Cricksy_Scorer/frontend')
  .then((result) => {
    console.log('seed result', result)
  })
  .catch((err) => {
    console.error('seed error', err)
  })
  .finally(() => {
    process.exit(0)
  })
