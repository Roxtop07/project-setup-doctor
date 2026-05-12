import type { ScanResult } from "../types";

interface CacheEntry {
  result: ScanResult;
  timestamp: number;
}

const CACHE_TTL_MS = 60_000;

export class ScanCache {
  private cache = new Map<string, CacheEntry>();

  get(rootPath: string): ScanResult | null {
    const entry = this.cache.get(rootPath);
    if (!entry) return null;
    if (Date.now() - entry.timestamp > CACHE_TTL_MS) {
      this.cache.delete(rootPath);
      return null;
    }
    return entry.result;
  }

  set(rootPath: string, result: ScanResult): void {
    this.cache.set(rootPath, { result, timestamp: Date.now() });
  }

  invalidate(rootPath: string): void {
    this.cache.delete(rootPath);
  }

  clear(): void {
    this.cache.clear();
  }
}
