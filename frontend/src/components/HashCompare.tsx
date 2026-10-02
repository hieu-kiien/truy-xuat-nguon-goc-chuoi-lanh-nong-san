import { digestDiff } from '../domain/digestDiff'

export function HashCompare({ recorded, computed }: { recorded: string; computed: string }) {
  const diff = digestDiff(recorded, computed)
  return <section className="digest-comparison" aria-label="Đối chiếu hai digest SHA-256 thực"><div className="digest-comparison-title"><h3>Hai dấu niêm phong, đối chiếu từng ký tự.</h3><span>{diff.changedBits} / 256 bit khác</span></div><div><span className="micro-label">HASH ĐÃ GHI</span><code>{recorded}</code></div><div><span className="micro-label">HASH TÍNH LẠI</span><code className="digest-hex-diff" aria-label={computed}>{diff.characters.map((character, index) => <span key={index} className={character.changed ? 'hex-changed' : ''}>{character.value}</span>)}</code></div><p>{diff.changedHex === 0 ? 'Cả 64 ký tự khớp. Liên kết tổ tiên vẫn được kiểm tra riêng.' : `${diff.changedHex} / 64 ký tự hex khác nhau. Các vị trí được đánh dấu là khác biệt thực sau khi băm lại payload.`}</p></section>
}
