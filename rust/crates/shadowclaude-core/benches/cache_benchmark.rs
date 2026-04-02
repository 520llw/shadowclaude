//! Cache benchmarks

use criterion::{black_box, criterion_group, criterion_main, Criterion};
use shadowclaude_core::{CacheConfig, CacheManager, CacheStrategy};
use std::time::Duration;

async fn setup_cache() -> CacheManager {
    let config = CacheConfig {
        max_entries: 10000,
        max_size_bytes: 100 * 1024 * 1024,
        default_ttl_secs: 3600,
        ..Default::default()
    };
    CacheManager::new(config).await.unwrap()
}

fn bench_cache_set(c: &mut Criterion) {
    let rt = tokio::runtime::Runtime::new().unwrap();
    
    c.bench_function("cache_set", |b| {
        b.to_async(&rt).iter(|| async {
            let cache = setup_cache().await;
            for i in 0..100 {
                cache.set(format!("key_{}", i), &format!("value_{}", i), None).unwrap();
            }
        });
    });
}

fn bench_cache_get(c: &mut Criterion) {
    let rt = tokio::runtime::Runtime::new().unwrap();
    
    c.bench_function("cache_get", |b| {
        b.to_async(&rt).iter(|| async {
            let cache = setup_cache().await;
            for i in 0..100 {
                cache.set(format!("key_{}", i), &format!("value_{}", i), None).unwrap();
            }
            
            for i in 0..100 {
                let _: Option<String> = cache.get(&format!("key_{}", i)).unwrap();
            }
        });
    });
}

fn bench_cache_mixed(c: &mut Criterion) {
    let rt = tokio::runtime::Runtime::new().unwrap();
    
    c.bench_function("cache_mixed", |b| {
        b.to_async(&rt).iter(|| async {
            let cache = setup_cache().await;
            
            // Mixed workload
            for i in 0..1000 {
                if i % 3 == 0 {
                    cache.set(format!("key_{}", i), &format!("value_{}", i), None).unwrap();
                } else if i % 3 == 1 {
                    let _: Option<String> = cache.get(&format!("key_{}", i / 2)).unwrap();
                } else {
                    cache.remove(&format!("key_{}", i / 3));
                }
            }
        });
    });
}

criterion_group!(cache_benchmarks, bench_cache_set, bench_cache_get, bench_cache_mixed);
criterion_main!(cache_benchmarks);
