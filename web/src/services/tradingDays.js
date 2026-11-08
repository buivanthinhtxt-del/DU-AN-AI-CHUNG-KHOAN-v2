/**
 * Tiện ích tính toán ngày giao dịch (Trading Days) bỏ qua Thứ Bảy và Chủ Nhật.
 * Đảm bảo ngày dự báo tương lai luôn rơi vào các phiên giao dịch thực tế của thị trường VN.
 */

export function addTradingDays(dateStrOrObj, daysToAdd) {
  if (!dateStrOrObj) return { dateObj: new Date(), isoDate: '', formatted: '' };

  let year, month, day;
  if (typeof dateStrOrObj === 'string') {
    const parts = dateStrOrObj.substring(0, 10).split('-');
    year = parseInt(parts[0], 10);
    month = parseInt(parts[1], 10) - 1;
    day = parseInt(parts[2], 10);
  } else if (dateStrOrObj instanceof Date) {
    year = dateStrOrObj.getFullYear();
    month = dateStrOrObj.getMonth();
    day = dateStrOrObj.getDate();
  } else {
    const d = new Date(dateStrOrObj);
    year = d.getFullYear();
    month = d.getMonth();
    day = d.getDate();
  }

  const date = new Date(year, month, day, 12, 0, 0);
  let added = 0;
  const target = Math.max(1, Math.round(daysToAdd || 1));

  while (added < target) {
    date.setDate(date.getDate() + 1);
    const dayOfWeek = date.getDay();
    // 0 = Chủ Nhật, 6 = Thứ Bảy
    if (dayOfWeek !== 0 && dayOfWeek !== 6) {
      added++;
    }
  }

  const y = date.getFullYear();
  const m = String(date.getMonth() + 1).padStart(2, '0');
  const d = String(date.getDate()).padStart(2, '0');

  return {
    dateObj: date,
    isoDate: `${y}-${m}-${d}`,
    formatted: `${d}/${m}`,
  };
}
