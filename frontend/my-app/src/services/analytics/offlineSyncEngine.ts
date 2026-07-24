import { OfflineQueueItem, SyncStatus } from '../../types/feedback';
import { LOCAL_STORAGE_OFFLINE_QUEUE_KEY, GOOGLE_SHEETS_WEBHOOK_URL } from '../../constants/feedback';

export function getOfflineQueue(): OfflineQueueItem[] {
  if (typeof window === 'undefined') return [];
  try {
    const raw = localStorage.getItem(LOCAL_STORAGE_OFFLINE_QUEUE_KEY);
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}

export function saveOfflineQueue(queue: OfflineQueueItem[]): void {
  if (typeof window === 'undefined') return;
  try {
    localStorage.setItem(LOCAL_STORAGE_OFFLINE_QUEUE_KEY, JSON.stringify(queue));
  } catch (e) {
    console.warn('[OfflineSyncEngine] LocalStorage queue write error:', e);
  }
}

export function enqueueOfflinePayload(worksheet: string, payload: any): OfflineQueueItem {
  const item: OfflineQueueItem = {
    id: `queue_${Date.now()}_${Math.random().toString(36).substr(2, 5)}`,
    worksheet,
    payload,
    createdAt: new Date().toISOString(),
    retryCount: 0,
    status: 'Pending',
  };

  const queue = getOfflineQueue();
  queue.push(item);
  saveOfflineQueue(queue);

  if (typeof window !== 'undefined') {
    window.dispatchEvent(
      new CustomEvent('feedback_submitted', { detail: { item, syncStatus: 'Pending' } })
    );
  }

  return item;
}

export async function syncOfflineQueue(): Promise<{ syncedCount: number; failedCount: number }> {
  if (typeof window === 'undefined' || !navigator.onLine) {
    return { syncedCount: 0, failedCount: 0 };
  }

  const queue = getOfflineQueue();
  if (queue.length === 0) return { syncedCount: 0, failedCount: 0 };

  let syncedCount = 0;
  let failedCount = 0;
  const remainingQueue: OfflineQueueItem[] = [];

  for (const item of queue) {
    item.status = 'Retrying';
    item.retryCount += 1;

    if (typeof window !== 'undefined') {
      window.dispatchEvent(
        new CustomEvent('feedback_retry', { detail: { item } })
      );
    }

    try {
      await fetch(GOOGLE_SHEETS_WEBHOOK_URL, {
        method: 'POST',
        headers: { 'Content-Type': 'text/plain;charset=utf-8' },
        body: JSON.stringify(item.payload),
        mode: 'no-cors',
      });

      syncedCount += 1;
      item.status = 'Synced';
      if (typeof window !== 'undefined') {
        window.dispatchEvent(
          new CustomEvent('feedback_synced', { detail: { item } })
        );
      }
    } catch (err: any) {
      failedCount += 1;
      item.status = item.retryCount > 5 ? 'Failed' : 'Pending';
      item.lastError = err.message || 'Network fetch error';
      remainingQueue.push(item);

      if (typeof window !== 'undefined') {
        window.dispatchEvent(
          new CustomEvent('feedback_failed', { detail: { item } })
        );
      }
    }
  }

  saveOfflineQueue(remainingQueue);
  return { syncedCount, failedCount };
}

// Auto-register online listener
if (typeof window !== 'undefined') {
  window.addEventListener('online', () => {
    syncOfflineQueue();
  });
}
