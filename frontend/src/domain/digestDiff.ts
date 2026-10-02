export function digestDiff(recorded: string, computed: string) {
  if (!/^[a-f0-9]{64}$/i.test(recorded) || !/^[a-f0-9]{64}$/i.test(computed)) throw new Error('Cần hai SHA-256 hex digest đầy đủ.')
  const characters = Array.from(computed, (value, index) => ({ value, changed: value.toLowerCase() !== recorded[index].toLowerCase() }))
  const changedBits = characters.reduce((sum, { value }, index) => {
    const xor = Number.parseInt(value, 16) ^ Number.parseInt(recorded[index], 16)
    return sum + xor.toString(2).replaceAll('0', '').length
  }, 0)
  return { characters, changedHex: characters.filter((character) => character.changed).length, changedBits }
}
