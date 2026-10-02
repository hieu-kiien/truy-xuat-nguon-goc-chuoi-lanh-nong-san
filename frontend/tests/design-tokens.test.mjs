import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'

const css = readFileSync(new URL('../src/styles/tokens.css', import.meta.url), 'utf8')
function luminance(hex) {
  const channels = [1, 3, 5].map((index) => parseInt(hex.slice(index, index + 2), 16) / 255)
    .map((value) => value <= .04045 ? value / 12.92 : ((value + .055) / 1.055) ** 2.4)
  return channels.reduce((total, value, index) => total + value * [.2126, .7152, .0722][index], 0)
}
const contrast = (a, b) => (Math.max(luminance(a), luminance(b)) + .05) / (Math.min(luminance(a), luminance(b)) + .05)

test('semantic foreground and focus tokens meet contrast targets in both themes', () => {
  for (const [theme, block] of [['light', css.split('html.dark')[0]], ['dark', css.split('html.dark')[1]]]) {
    const tokens = Object.fromEntries([...block.matchAll(/--([\w-]+): (#[a-f0-9]{6});/g)].map((match) => [match[1], match[2]]))
    for (const ink of ['ink', 'ink-soft', 'muted', 'quiet']) {
      for (const surface of ['canvas', 'surface', 'surface-raised', 'surface-muted']) {
        assert.ok(contrast(tokens[ink], tokens[surface]) >= 4.5, `${theme} ${ink}/${surface} needs 4.5:1`)
      }
    }
    for (const status of ['success', 'warning', 'danger']) {
      assert.ok(contrast(tokens[status], tokens[`${status}-soft`]) >= 4.5, `${theme} ${status} label needs 4.5:1`)
    }
    assert.ok(contrast(tokens.focus, tokens.canvas) >= 3, `${theme} focus needs 3:1 against canvas`)
    assert.ok(contrast(tokens.focus, tokens.surface) >= 3, `${theme} focus needs 3:1 against surface`)
  }
})
