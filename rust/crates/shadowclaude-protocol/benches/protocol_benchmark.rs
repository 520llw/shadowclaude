//! Protocol benchmarks

use criterion::{black_box, criterion_group, criterion_main, Criterion};
use shadowclaude_protocol::{ProtocolMessage, MessageType, MessageFrame, serde::JsonSerializer, Serializer};
use serde::Serialize;

#[derive(Serialize)]
struct TestPayload {
    id: String,
    content: String,
    metadata: std::collections::HashMap<String, String>,
}

fn create_test_payload() -> TestPayload {
    let mut metadata = std::collections::HashMap::new();
    metadata.insert("key1".to_string(), "value1".to_string());
    metadata.insert("key2".to_string(), "value2".to_string());

    TestPayload {
        id: uuid::Uuid::new_v4().to_string(),
        content: "Test content for serialization benchmark".to_string(),
        metadata,
    }
}

fn bench_message_serialization(c: &mut Criterion) {
    let payload = create_test_payload();

    c.bench_function("message_serialization", |b| {
        b.iter(|| {
            let msg = ProtocolMessage::request("test_method", black_box(&payload)).unwrap();
            let _json = msg.to_json().unwrap();
        });
    });
}

fn bench_message_deserialization(c: &mut Criterion) {
    let payload = create_test_payload();
    let msg = ProtocolMessage::request("test_method", &payload).unwrap();
    let json = msg.to_json().unwrap();

    c.bench_function("message_deserialization", |b| {
        b.iter(|| {
            let _: ProtocolMessage = ProtocolMessage::from_json(black_box(&json)).unwrap();
        });
    });
}

fn bench_json_serializer(c: &mut Criterion) {
    let serializer = JsonSerializer;
    let payload = create_test_payload();

    c.bench_function("json_serialization", |b| {
        b.iter(|| {
            let _ = serializer.serialize(black_box(&payload)).unwrap();
        });
    });
}

criterion_group!(protocol_benchmarks, bench_message_serialization, bench_message_deserialization, bench_json_serializer);
criterion_main!(protocol_benchmarks);
