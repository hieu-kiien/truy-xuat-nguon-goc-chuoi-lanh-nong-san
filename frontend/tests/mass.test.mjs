import assert from 'node:assert/strict'
import test from 'node:test'
import { readFile } from 'node:fs/promises'
import ts from 'typescript'

const source = await readFile(new URL('../src/utils/mass.ts', import.meta.url), 'utf8')
const compiled = ts.transpileModule(source, {compilerOptions: {module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2020}}).outputText
const { grams, formatGrams, splitSummary } = await import(`data:text/javascript;base64,${Buffer.from(compiled).toString('base64')}`)

test('decimal quantities stay exact to a gram', () => {
  assert.equal(grams('0.001'), 1n)
  assert.equal(formatGrams(grams('0.1') + grams('0.2')), '0.300')
  assert.equal(formatGrams(999999999999999n), '999999999999.999')
  for (const input of ['', 'NaN', 'Infinity', '-1', '1.0001', '1e3', '9'.repeat(33)]) assert.equal(grams(input), null)
})
test('live validation blocks invalid and overstock totals', () => {
  for (const amounts of [[], [''], ['0'], ['-1'], ['1.0001']]) assert.equal(splitSummary(amounts, '40').valid, false)
  assert.deepEqual(splitSummary(['30', '10.001'], '40'), {total: 40001n, remaining: -1n, valid: false})
  assert.deepEqual(splitSummary(['20', '20'], '40'), {total: 40000n, remaining: 0n, valid: true})
  assert.deepEqual(splitSummary(['0.001', '0.002'], '0.004'), {total: 3n, remaining: 1n, valid: true})
})
