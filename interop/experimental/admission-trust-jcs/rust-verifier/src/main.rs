use serde_json::json;
use spp_jcs_rust_verifier::{evaluate_raw, strict_parse, verify_vectors};
use std::{env, fs, process};

fn main() {
    let args: Vec<String> = env::args().collect();
    if args.get(1).map(String::as_str) == Some("--raw") {
        let path = args
            .get(2)
            .cloned()
            .unwrap_or_else(|| "../adversarial-corpus.json".into());
        let corpus: serde_json::Value =
            serde_json::from_str(&fs::read_to_string(&path).unwrap_or_else(|e| {
                eprintln!("cannot read {path}: {e}");
                process::exit(2)
            }))
            .unwrap_or_else(|e| {
                eprintln!("bad corpus: {e}");
                process::exit(2)
            });
        let results: Vec<serde_json::Value> = corpus["cases"].as_array().unwrap_or(&Vec::new()).iter().map(|case| json!({"id": case["id"], "result": evaluate_raw(case["source"].as_str().unwrap_or(""))})).collect();
        println!("{}", json!({"implementation":"rust", "results":results}));
        return;
    }
    let path = args
        .get(1)
        .cloned()
        .unwrap_or_else(|| "../vectors.json".into());
    let source = fs::read_to_string(&path).unwrap_or_else(|e| {
        eprintln!("cannot read {path}: {e}");
        process::exit(2)
    });
    let vectors = strict_parse(&source).unwrap_or_else(|e| {
        eprintln!("fixture parse failed: {e}");
        process::exit(2)
    });
    match verify_vectors(&vectors) {
        Ok(count) => println!("Rust JCS verifier: {count} vectors verified"),
        Err(e) => {
            eprintln!("vector disagreement: {e}");
            process::exit(1)
        }
    }
}
