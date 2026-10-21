/** Checks that the forms run before a value is sent to the server. */

/** Check the three cold chain thresholds of one product. */
export function validateColdChainConfig(
  minTemp: string,
  maxTemp: string,
  delay: string,
): string | null {
  if (
    minTemp.trim() === '' ||
    maxTemp.trim() === '' ||
    delay.trim() === ''
  ) {
    return 'Cả ba ô cấu hình đều phải có số.'
  }
  const min = Number(minTemp)
  const max = Number(maxTemp)
  const minutes = Number(delay)
  if (!Number.isFinite(min) || !Number.isFinite(max) || !Number.isFinite(minutes)) {
    return 'Các ô cấu hình phải là số.'
  }
  if (min >= max) {
    return 'Ngưỡng dưới phải nhỏ hơn ngưỡng trên.'
  }
  if (minutes < 1 || minutes > 1440) {
    return 'Độ trễ phải từ 1 đến 1440 phút.'
  }
  return null
}

/** Check one temperature reading before it is sent to the server. */
export function readingError(
  temperature: string,
  recordedAt: string,
): string | null {
  const value = Number(temperature)
  if (!Number.isFinite(value) || temperature.trim() === '') {
    return 'Vui lòng nhập nhiệt độ.'
  }
  if (Number.isNaN(new Date(recordedAt).getTime())) {
    return 'Thời điểm ghi nhận không hợp lệ.'
  }
  return null
}
