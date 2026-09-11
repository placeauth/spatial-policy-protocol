//! Independent, experimental verifier for the SPP RFC 8785 admission profile.
//! It deliberately consumes only JSON fixtures and public keys.

use base64::{engine::general_purpose::STANDARD, Engine};
use chrono::{DateTime, NaiveDateTime, Utc};
use ed25519_dalek::{Signature, Verifier, VerifyingKey};
use serde::de::{Deserialize, Deserializer, MapAccess, SeqAccess, Visitor};
use serde_json::{json, Map, Number, Value};
use sha2::{Digest, Sha256};
use std::{collections::HashSet, fmt};

pub const PROFILE: &str = "rfc8785-jcs-v1-experimental";
const MAX_SAFE_INTEGER: u64 = 9_007_199_254_740_991;

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct ResultRecord {
    pub verified: bool,
    pub reason: Option<String>,
}

fn error(category: &str) -> ResultRecord {
    ResultRecord {
        verified: false,
        reason: Some(category.into()),
    }
}

/// Parses JSON while rejecting duplicate decoded keys and unpaired UTF-16
/// surrogate escapes before deserialization can erase that distinction.
pub fn strict_parse(source: &str) -> Result<Value, String> {
    reject_unpaired_surrogate_escapes(source)?;
    reject_negative_zero_lexeme(source)?;
    let mut de = serde_json::Deserializer::from_str(source);
    let value = NoDuplicateValue::deserialize(&mut de)
        .map_err(|e| e.to_string())?
        .0;
    de.end().map_err(|e| e.to_string())?;
    validate_portable_value(&value)?;
    Ok(value)
}

struct NoDuplicateValue(Value);

impl<'de> Deserialize<'de> for NoDuplicateValue {
    fn deserialize<D: Deserializer<'de>>(deserializer: D) -> Result<Self, D::Error> {
        struct V;
        impl<'de> Visitor<'de> for V {
            type Value = NoDuplicateValue;
            fn expecting(&self, f: &mut fmt::Formatter) -> fmt::Result {
                f.write_str("a JSON value")
            }
            fn visit_unit<E: serde::de::Error>(self) -> Result<Self::Value, E> {
                Ok(NoDuplicateValue(Value::Null))
            }
            fn visit_none<E: serde::de::Error>(self) -> Result<Self::Value, E> {
                Ok(NoDuplicateValue(Value::Null))
            }
            fn visit_bool<E: serde::de::Error>(self, v: bool) -> Result<Self::Value, E> {
                Ok(NoDuplicateValue(Value::Bool(v)))
            }
            fn visit_i64<E: serde::de::Error>(self, v: i64) -> Result<Self::Value, E> {
                Ok(NoDuplicateValue(Value::Number(v.into())))
            }
            fn visit_u64<E: serde::de::Error>(self, v: u64) -> Result<Self::Value, E> {
                Ok(NoDuplicateValue(Value::Number(v.into())))
            }
            fn visit_f64<E: serde::de::Error>(self, v: f64) -> Result<Self::Value, E> {
                Number::from_f64(v)
                    .map(|n| NoDuplicateValue(Value::Number(n)))
                    .ok_or_else(|| E::custom("non-finite JSON number"))
            }
            fn visit_str<E: serde::de::Error>(self, v: &str) -> Result<Self::Value, E> {
                Ok(NoDuplicateValue(Value::String(v.into())))
            }
            fn visit_string<E: serde::de::Error>(self, v: String) -> Result<Self::Value, E> {
                Ok(NoDuplicateValue(Value::String(v)))
            }
            fn visit_seq<A: SeqAccess<'de>>(self, mut seq: A) -> Result<Self::Value, A::Error> {
                let mut values = Vec::new();
                while let Some(v) = seq.next_element::<NoDuplicateValue>()? {
                    values.push(v.0);
                }
                Ok(NoDuplicateValue(Value::Array(values)))
            }
            fn visit_map<A: MapAccess<'de>>(self, mut map: A) -> Result<Self::Value, A::Error> {
                let mut values = Map::new();
                let mut seen = HashSet::new();
                while let Some(key) = map.next_key::<String>()? {
                    if !seen.insert(key.clone()) {
                        return Err(serde::de::Error::custom(format!(
                            "duplicate JSON key: {key}"
                        )));
                    }
                    values.insert(key, map.next_value::<NoDuplicateValue>()?.0);
                }
                Ok(NoDuplicateValue(Value::Object(values)))
            }
        }
        deserializer.deserialize_any(V)
    }
}

fn reject_negative_zero_lexeme(source: &str) -> Result<(), String> {
    let bytes = source.as_bytes();
    let mut i = 0;
    let mut quoted = false;
    while i < bytes.len() {
        if quoted {
            if bytes[i] == b'\\' {
                i += 2;
                continue;
            }
            if bytes[i] == b'"' {
                quoted = false;
            }
            i += 1;
            continue;
        }
        if bytes[i] == b'"' {
            quoted = true;
            i += 1;
            continue;
        }
        if i + 2 <= bytes.len() && &bytes[i..i + 2] == b"-0" {
            let next = bytes.get(i + 2).copied();
            if matches!(
                next,
                None | Some(b',')
                    | Some(b']')
                    | Some(b'}')
                    | Some(b' ')
                    | Some(b'\n')
                    | Some(b'\r')
                    | Some(b'\t')
            ) {
                return Err("negative zero is not permitted".into());
            }
        }
        i += 1;
    }
    Ok(())
}

fn hex4(bytes: &[u8]) -> Result<u16, String> {
    if bytes.len() != 4 {
        return Err("truncated Unicode escape".into());
    }
    let text = std::str::from_utf8(bytes).map_err(|_| "invalid Unicode escape")?;
    u16::from_str_radix(text, 16).map_err(|_| "invalid Unicode escape".into())
}

fn reject_unpaired_surrogate_escapes(source: &str) -> Result<(), String> {
    let bytes = source.as_bytes();
    let mut i = 0;
    let mut quoted = false;
    while i < bytes.len() {
        if !quoted {
            if bytes[i] == b'"' {
                quoted = true;
            }
            i += 1;
            continue;
        }
        if bytes[i] == b'"' {
            quoted = false;
            i += 1;
            continue;
        }
        if bytes[i] != b'\\' {
            i += 1;
            continue;
        }
        if bytes.get(i + 1) != Some(&b'u') {
            i += 2;
            continue;
        }
        let first = hex4(bytes.get(i + 2..i + 6).unwrap_or_default())?;
        if (0xD800..=0xDBFF).contains(&first) {
            if bytes.get(i + 6) != Some(&b'\\') || bytes.get(i + 7) != Some(&b'u') {
                return Err("malformed Unicode scalar value".into());
            }
            let second = hex4(bytes.get(i + 8..i + 12).unwrap_or_default())?;
            if !(0xDC00..=0xDFFF).contains(&second) {
                return Err("malformed Unicode scalar value".into());
            }
            i += 12;
        } else if (0xDC00..=0xDFFF).contains(&first) {
            return Err("malformed Unicode scalar value".into());
        } else {
            i += 6;
        }
    }
    if quoted {
        return Err("unterminated JSON string".into());
    }
    Ok(())
}

pub fn canonicalize(value: &Value) -> Result<Vec<u8>, String> {
    validate_portable_value(value)?;
    serde_jcs::to_vec(value).map_err(|e| e.to_string())
}

pub fn digest(value: &Value) -> Result<String, String> {
    let hash = Sha256::digest(canonicalize(value)?);
    Ok(format!("sha256:{hash:x}"))
}

fn validate_portable_value(value: &Value) -> Result<(), String> {
    match value {
        Value::Null | Value::Bool(_) | Value::String(_) => Ok(()),
        Value::Number(number) => {
            if let Some(v) = number.as_i64() {
                if v.unsigned_abs() > MAX_SAFE_INTEGER {
                    return Err("integer outside JavaScript safe range".into());
                }
            } else if let Some(v) = number.as_u64() {
                if v > MAX_SAFE_INTEGER {
                    return Err("integer outside JavaScript safe range".into());
                }
            } else if let Some(v) = number.as_f64() {
                if !v.is_finite() {
                    return Err("non-finite JSON number".into());
                }
                if v == 0.0 && v.is_sign_negative() {
                    return Err("negative zero is not permitted".into());
                }
                if v.fract() == 0.0 && v.abs() > MAX_SAFE_INTEGER as f64 {
                    return Err("integer outside JavaScript safe range".into());
                }
            }
            Ok(())
        }
        Value::Array(items) => items.iter().try_for_each(validate_portable_value),
        Value::Object(items) => items.values().try_for_each(validate_portable_value),
    }
}

fn string<'a>(map: &'a Map<String, Value>, key: &str) -> Result<&'a str, ResultRecord> {
    map.get(key)
        .and_then(Value::as_str)
        .filter(|v| !v.is_empty())
        .ok_or_else(|| error("malformed_envelope"))
}

fn timestamp(value: &str) -> Result<DateTime<Utc>, ResultRecord> {
    if value.len() != 20 || !value.ends_with('Z') {
        return Err(error("jcs_profile_value_invalid"));
    }
    NaiveDateTime::parse_from_str(value, "%Y-%m-%dT%H:%M:%SZ")
        .map(|v| v.and_utc())
        .map_err(|_| error("jcs_profile_value_invalid"))
}

fn signature_input(envelope: &Map<String, Value>) -> Result<Vec<u8>, ResultRecord> {
    let mut input = Map::new();
    for key in [
        "issuer_id",
        "algorithm",
        "envelope_type",
        "envelope_version",
        "canonicalization_profile",
        "subject_id",
        "place",
        "space",
        "scope",
        "issued_at",
        "expires_at",
        "signed_payload_digest",
    ] {
        input.insert(key.into(), Value::String(string(envelope, key)?.into()));
    }
    canonicalize(&Value::Object(input)).map_err(|_| error("jcs_profile_value_invalid"))
}

pub fn verify_envelope(vector: &Value) -> ResultRecord {
    let object = match vector.as_object() {
        Some(v) => v,
        None => return error("malformed_envelope"),
    };
    let envelope = match object.get("envelope").and_then(Value::as_object) {
        Some(v) => v,
        None => return error("malformed_envelope"),
    };
    let issuer = match object.get("trusted_issuer").and_then(Value::as_object) {
        Some(v) => v,
        None => return error("malformed_envelope"),
    };
    let check = match object.get("verification").and_then(Value::as_object) {
        Some(v) => v,
        None => return error("malformed_envelope"),
    };
    if string(envelope, "canonicalization_profile").unwrap_or("") != PROFILE {
        return error("unsupported_canonicalization_profile");
    }
    if string(envelope, "envelope_version").unwrap_or("") != "0.1-experimental" {
        return error("unsupported_envelope_version");
    }
    if string(envelope, "envelope_type").unwrap_or("") != "spp:admission-envelope"
        || string(envelope, "algorithm").unwrap_or("") != "Ed25519"
    {
        return error("unsupported_signature_algorithm");
    }
    let profile = match envelope.get("profile").and_then(Value::as_object) {
        Some(v) => v,
        None => return error("malformed_envelope"),
    };
    let subject = match string(envelope, "subject_id") {
        Ok(v) => v,
        Err(e) => return e,
    };
    let place = match string(envelope, "place") {
        Ok(v) => v,
        Err(e) => return e,
    };
    let space = match string(envelope, "space") {
        Ok(v) => v,
        Err(e) => return e,
    };
    if profile.get("actor_id").and_then(Value::as_str) != Some(subject)
        || profile.get("place").and_then(Value::as_str) != Some(place)
        || profile.get("space").and_then(Value::as_str) != Some(space)
        || string(envelope, "scope").unwrap_or("") != format!("{place}::{space}")
    {
        return error("malformed_envelope");
    }
    let issued = match string(envelope, "issued_at").and_then(timestamp) {
        Ok(v) => v,
        Err(e) => return e,
    };
    let expires = match string(envelope, "expires_at").and_then(timestamp) {
        Ok(v) => v,
        Err(e) => return e,
    };
    let now = match check
        .get("now")
        .and_then(Value::as_str)
        .ok_or_else(|| error("jcs_profile_value_invalid"))
        .and_then(timestamp)
    {
        Ok(v) => v,
        Err(e) => return e,
    };
    if expires <= issued {
        return error("invalid_envelope_time_range");
    }
    if issued > now {
        return error("envelope_issued_in_future");
    }
    if expires <= now {
        return error("envelope_expired");
    }
    let profile_digest = match digest(&Value::Object(profile.clone())) {
        Ok(v) => v,
        Err(_) => return error("jcs_profile_value_invalid"),
    };
    if string(envelope, "signed_payload_digest").unwrap_or("") != profile_digest {
        return error("signed_payload_digest_mismatch");
    }
    if string(issuer, "issuer_id").unwrap_or("") != string(envelope, "issuer_id").unwrap_or("") {
        return error("unknown_issuer");
    }
    if issuer.get("enabled").and_then(Value::as_bool) != Some(true) {
        return error("issuer_disabled");
    }
    let etype = string(envelope, "envelope_type").unwrap_or("");
    let scope = string(envelope, "scope").unwrap_or("");
    if !issuer
        .get("allowed_envelope_types")
        .and_then(Value::as_array)
        .map(|a| a.iter().any(|v| v.as_str() == Some(etype)))
        .unwrap_or(false)
    {
        return error("issuer_unauthorized_envelope_type");
    }
    if !issuer
        .get("allowed_scopes")
        .and_then(Value::as_array)
        .map(|a| a.iter().any(|v| v.as_str() == Some(scope)))
        .unwrap_or(false)
    {
        return error("issuer_unauthorized_scope");
    }
    let public = match string(issuer, "public_key_base64").and_then(|v| {
        STANDARD
            .decode(v)
            .map_err(|_| error("invalid_envelope_signature"))
    }) {
        Ok(v) => v,
        Err(e) => return e,
    };
    let key = match <[u8; 32]>::try_from(public.as_slice())
        .ok()
        .and_then(|v| VerifyingKey::from_bytes(&v).ok())
    {
        Some(v) => v,
        None => return error("invalid_envelope_signature"),
    };
    let signature = match string(envelope, "signature")
        .and_then(|v| {
            STANDARD
                .decode(v)
                .map_err(|_| error("invalid_envelope_signature"))
        })
        .and_then(|v| Signature::from_slice(&v).map_err(|_| error("invalid_envelope_signature")))
    {
        Ok(v) => v,
        Err(e) => return e,
    };
    let input = match signature_input(envelope) {
        Ok(v) => v,
        Err(e) => return e,
    };
    if key.verify(&input, &signature).is_err() {
        return error("invalid_envelope_signature");
    }
    if check.get("expected_subject_id").and_then(Value::as_str) != Some(subject) {
        return error("envelope_subject_mismatch");
    }
    if check.get("expected_place").and_then(Value::as_str) != Some(place)
        || check.get("expected_space").and_then(Value::as_str) != Some(space)
    {
        return error("envelope_place_mismatch");
    }
    ResultRecord {
        verified: true,
        reason: None,
    }
}

pub fn verify_vectors(root: &Value) -> Result<usize, String> {
    let vectors = root
        .get("vectors")
        .and_then(Value::as_array)
        .ok_or("vectors missing")?;
    let mut count = 0;
    for vector in vectors {
        if vector.get("kind").and_then(Value::as_str) == Some("jcs_admission_envelope") {
            let actual = verify_envelope(vector);
            let expected = vector
                .get("expected")
                .and_then(Value::as_object)
                .ok_or("expected missing")?;
            if expected.get("verified").and_then(Value::as_bool) != Some(actual.verified)
                || expected.get("reason")
                    != Some(
                        &actual
                            .reason
                            .clone()
                            .map(Value::String)
                            .unwrap_or(Value::Null),
                    )
            {
                return Err(format!(
                    "vector {:?} disagreed: {:?}",
                    vector.get("id"),
                    actual
                ));
            }
        } else if vector.get("kind").and_then(Value::as_str)
            == Some("jcs_restriction_acknowledgement")
        {
            if !verify_acknowledgement(vector)? {
                return Err(format!(
                    "acknowledgement vector {:?} disagreed",
                    vector.get("id")
                ));
            }
        } else {
            return Err(format!("unknown vector kind {:?}", vector.get("kind")));
        }
        count += 1;
    }
    Ok(count)
}

fn verify_acknowledgement(vector: &Value) -> Result<bool, String> {
    let profile = vector
        .get("profile")
        .and_then(Value::as_object)
        .ok_or("profile missing")?;
    let operating = profile
        .get("operating_profile")
        .and_then(Value::as_object)
        .ok_or("operating profile missing")?;
    let mut restrictions: Vec<String> = profile
        .get("restrictions")
        .and_then(Value::as_array)
        .into_iter()
        .flatten()
        .chain(
            operating
                .get("restrictions")
                .and_then(Value::as_array)
                .into_iter()
                .flatten(),
        )
        .map(|v| {
            v.as_str()
                .ok_or("restriction not string")
                .map(str::to_owned)
        })
        .collect::<Result<_, _>>()?;
    restrictions.sort_by_key(|v| v.encode_utf16().collect::<Vec<_>>());
    restrictions.dedup();
    if vector
        .get("effective_restrictions")
        .and_then(Value::as_array)
        != Some(&restrictions.iter().cloned().map(Value::String).collect())
    {
        return Ok(false);
    }
    let mut op = operating.clone();
    op.remove("restrictions");
    let payload = json!({"status":profile.get("status"), "actor_id":profile.get("actor_id"), "place":profile.get("place"), "space":profile.get("space"), "policy_version":profile.get("policy_version"), "evidence_digest":profile.get("evidence_digest"), "binding":profile.get("binding"), "operating_profile":op, "effective_restrictions":restrictions, "unresolved":profile.get("unresolved"), "reason_codes":profile.get("reason_codes")});
    let binding = format!(
        "urn:spp:jcs-restriction-profile:{}",
        digest(&payload)?.trim_start_matches("sha256:")
    );
    if vector.get("profile_binding").and_then(Value::as_str) != Some(&binding) {
        return Ok(false);
    }
    let acks = vector
        .get("acknowledgements")
        .and_then(Value::as_array)
        .ok_or("acks missing")?;
    let mappings = vector
        .get("enforcement_mappings")
        .and_then(Value::as_array)
        .ok_or("mappings missing")?;
    for restriction in restrictions {
        let rd = digest(&json!({"restriction":restriction}))?;
        if vector
            .get("restriction_digests")
            .and_then(Value::as_object)
            .and_then(|m| m.get(&restriction))
            .and_then(Value::as_str)
            != Some(&rd)
        {
            return Ok(false);
        }
        let ack: Vec<_> = acks
            .iter()
            .filter(|v| v.get("restriction").and_then(Value::as_str) == Some(&restriction))
            .collect();
        let map: Vec<_> = mappings
            .iter()
            .filter(|v| v.get("restriction").and_then(Value::as_str) == Some(&restriction))
            .collect();
        if ack.len() != 1 || map.len() != 1 {
            return Ok(false);
        }
        let handler = ack[0]
            .get("enforcement_handler")
            .and_then(Value::as_str)
            .filter(|v| !v.is_empty());
        if ack[0].get("profile_id").and_then(Value::as_str) != Some(&binding)
            || ack[0].get("restriction_digest").and_then(Value::as_str) != Some(&rd)
            || map[0].get("restriction_digest").and_then(Value::as_str) != Some(&rd)
            || map[0].get("enforcement_handler").and_then(Value::as_str) != handler
        {
            return Ok(false);
        }
    }
    Ok(vector
        .get("expected")
        .and_then(Value::as_object)
        .and_then(|v| v.get("outcome"))
        .and_then(Value::as_str)
        == Some("ACKNOWLEDGED"))
}

pub fn evaluate_raw(source: &str) -> Value {
    match strict_parse(source)
        .and_then(|value| canonicalize(&value).map(|canonical| (value, canonical)))
    {
        Ok((_, canonical)) => {
            json!({"category": "accepted", "canonical": String::from_utf8_lossy(&canonical)})
        }
        Err(detail) => json!({"category": "malformed", "detail": detail}),
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn vector(id: &str) -> Value {
        let root = strict_parse(include_str!("../../vectors.json")).unwrap();
        root["vectors"]
            .as_array()
            .unwrap()
            .iter()
            .find(|item| item["id"] == id)
            .unwrap()
            .clone()
    }
    #[test]
    fn rejects_duplicate_and_negative_zero() {
        assert!(strict_parse(r#"{"a":1,"\u0061":2}"#).is_err());
        assert!(strict_parse(r#"{"n":-0}"#).is_err());
    }
    #[test]
    fn canonicalizes_utf16_keys_and_unicode() {
        assert_eq!(
            canonicalize(&strict_parse(r#"{"😀":1,"\uE000":2,"label":"café 🚀"}"#).unwrap())
                .unwrap(),
            "{\"label\":\"café 🚀\",\"😀\":1,\"\":2}".as_bytes()
        );
    }
    #[test]
    fn rejects_unsafe_float_integer() {
        assert!(strict_parse(r#"{"n":1e20}"#).is_err());
    }

    #[test]
    fn rejects_signature_issuer_and_binding_mutations() {
        let mut invalid_signature = vector("jcs_admitted_valid");
        invalid_signature["envelope"]["signature"] = Value::String("AA==".into());
        assert_eq!(
            verify_envelope(&invalid_signature).reason.as_deref(),
            Some("invalid_envelope_signature")
        );

        let mut unknown_issuer = vector("jcs_admitted_valid");
        unknown_issuer["envelope"]["issuer_id"] = Value::String("unknown".into());
        assert_eq!(
            verify_envelope(&unknown_issuer).reason.as_deref(),
            Some("unknown_issuer")
        );

        let mut wrong_key = vector("jcs_admitted_valid");
        wrong_key["trusted_issuer"]["public_key_base64"] =
            Value::String("AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=".into());
        assert_eq!(
            verify_envelope(&wrong_key).reason.as_deref(),
            Some("invalid_envelope_signature")
        );

        let mut wrong_binding = vector("jcs_restriction_acknowledgement");
        wrong_binding["profile_binding"] =
            Value::String("urn:spp:jcs-restriction-profile:altered".into());
        assert!(!verify_acknowledgement(&wrong_binding).unwrap());
    }
}
