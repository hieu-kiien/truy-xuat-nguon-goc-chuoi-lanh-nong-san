/**
 * utils/index.ts
 * Các hàm tiện ích dùng chung trong toàn dự án.
 */

/** Format ngày giờ theo chuẩn Việt Nam */
export function formatDate(date: Date | string): string {
  return new Intl.DateTimeFormat('vi-VN', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
  }).format(new Date(date))
}

/** Cắt ngắn chuỗi nếu quá dài */
export function truncate(str: string, maxLength: number): string {
  return str.length > maxLength ? `${str.slice(0, maxLength)}...` : str
}
