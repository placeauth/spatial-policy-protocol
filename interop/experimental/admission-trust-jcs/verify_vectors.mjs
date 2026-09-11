#!/usr/bin/env node
/* Dependency-free independent RFC 8785 verifier for experimental vectors. */
import { createHash, createPublicKey, verify as ed25519Verify } from "node:crypto";
import { readFileSync } from "node:fs";

const PROFILE = "rfc8785-jcs-v1-experimental";
const MAX_SAFE_INTEGER = Number.MAX_SAFE_INTEGER;
const TIMESTAMP = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$/;

function strictJsonParse(source) {
  let i = 0;
  const skip = () => { while (/[\x20\x09\x0a\x0d]/.test(source[i] ?? "")) i += 1; };
  const fail = message => { throw new Error(`invalid JSON at ${i}: ${message}`); };
  const string = () => {
    if (source[i] !== '"') fail("string expected");
    const start = i++;
    while (i < source.length) {
      const c = source[i++];
      if (c === '"') return JSON.parse(source.slice(start, i));
      if (c === "\\") { if (i >= source.length) fail("unfinished escape"); if (source[i++] === "u") i += 4; }
      else if (c < " ") fail("unescaped control character");
    }
    fail("unterminated string");
  };
  const value = () => {
    skip(); const c = source[i];
    if (c === "{") {
      i += 1; skip(); const object = {}; const keys = new Set();
      if (source[i] === "}") { i += 1; return object; }
      while (true) {
        skip(); const key = string();
        if (keys.has(key)) fail(`duplicate key ${JSON.stringify(key)}`);
        keys.add(key); skip(); if (source[i++] !== ":") fail("colon expected");
        object[key] = value(); skip();
        if (source[i] === "}") { i += 1; return object; }
        if (source[i++] !== ",") fail("comma expected");
      }
    }
    if (c === "[") {
      i += 1; skip(); const array = [];
      if (source[i] === "]") { i += 1; return array; }
      while (true) {
        array.push(value()); skip();
        if (source[i] === "]") { i += 1; return array; }
        if (source[i++] !== ",") fail("comma expected");
      }
    }
    if (c === '"') return string();
    for (const [token, result] of [["true", true], ["false", false], ["null", null]]) {
      if (source.startsWith(token, i)) { i += token.length; return result; }
    }
    const token = source.slice(i).match(/^-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?/);
    if (!token) fail("value expected");
    i += token[0].length; return Number(token[0]);
  };
  const result = value(); skip(); if (i !== source.length) fail("trailing data"); return result;
}

function rejectUnsupported(value) {
  if (value === null || typeof value === "boolean") return;
  if (typeof value === "string") {
    for (let i = 0; i < value.length; i += 1) {
      const code = value.charCodeAt(i);
      if (code >= 0xd800 && code <= 0xdfff) {
        const paired = code <= 0xdbff && i + 1 < value.length && value.charCodeAt(i + 1) >= 0xdc00 && value.charCodeAt(i + 1) <= 0xdfff;
        if (!paired) throw new Error("malformed Unicode scalar value");
        i += 1;
      }
    }
    return;
  }
  if (typeof value === "number") {
    if (!Number.isFinite(value)) throw new Error("non-finite JSON number");
    if (Object.is(value, -0)) throw new Error("negative zero is not permitted");
    if (Number.isInteger(value) && Math.abs(value) > MAX_SAFE_INTEGER) throw new Error("integer outside JavaScript safe range");
    return;
  }
  if (Array.isArray(value)) { value.forEach(rejectUnsupported); return; }
  if (typeof value === "object") { Object.entries(value).forEach(([key, nested]) => { rejectUnsupported(key); rejectUnsupported(nested); }); return; }
  throw new Error("unsupported JCS value");
}

function jcs(value) {
  rejectUnsupported(value);
  if (value === null || typeof value === "boolean" || typeof value === "number" || typeof value === "string") return JSON.stringify(value);
  if (Array.isArray(value)) return `[${value.map(jcs).join(",")}]`;
  return `{${Object.keys(value).sort().map(key => `${JSON.stringify(key)}:${jcs(value[key])}`).join(",")}}`;
}

function digest(value) { return `sha256:${createHash("sha256").update(jcs(value), "utf8").digest("hex")}`; }
function timestamp(value) { return typeof value === "string" && TIMESTAMP.test(value) && !Number.isNaN(Date.parse(value)) ? Date.parse(value) : null; }
function spki(raw) { return Buffer.concat([Buffer.from("302a300506032b6570032100", "hex"), raw]); }

function signatureInput(envelope) {
  return jcs({
    issuer_id: envelope.issuer_id, algorithm: envelope.algorithm, envelope_type: envelope.envelope_type,
    envelope_version: envelope.envelope_version, canonicalization_profile: envelope.canonicalization_profile,
    subject_id: envelope.subject_id, place: envelope.place, space: envelope.space, scope: envelope.scope,
    issued_at: envelope.issued_at, expires_at: envelope.expires_at, signed_payload_digest: envelope.signed_payload_digest,
  });
}

function verifyEnvelope(vector) {
  const { envelope, trusted_issuer: issuer, verification } = vector;
  if (envelope.canonicalization_profile !== PROFILE) return "unsupported_canonicalization_profile";
  if (envelope.envelope_version !== "0.1-experimental") return "unsupported_envelope_version";
  if (envelope.envelope_type !== "spp:admission-envelope" || envelope.algorithm !== "Ed25519") return "unsupported_signature_algorithm";
  if (envelope.subject_id !== envelope.profile.actor_id || envelope.place !== envelope.profile.place || envelope.space !== envelope.profile.space || envelope.scope !== `${envelope.profile.place}::${envelope.profile.space}`) return "malformed_envelope";
  let issued, expires, now;
  try { issued = timestamp(envelope.issued_at); expires = timestamp(envelope.expires_at); now = timestamp(verification.now); } catch { return "jcs_profile_value_invalid"; }
  if (issued === null || expires === null || now === null) return "jcs_profile_value_invalid";
  if (expires <= issued) return "invalid_envelope_time_range";
  if (issued > now) return "envelope_issued_in_future";
  if (expires <= now) return "envelope_expired";
  if (issuer.issuer_id !== envelope.issuer_id) return "unknown_issuer";
  if (!issuer.enabled) return "issuer_disabled";
  if (!issuer.allowed_envelope_types.includes(envelope.envelope_type)) return "issuer_unauthorized_envelope_type";
  if (!issuer.allowed_scopes.includes(envelope.scope)) return "issuer_unauthorized_scope";
  try {
    const canonical = jcs(envelope.profile);
    if (canonical !== vector.canonical_profile_jcs || Buffer.from(canonical, "utf8").toString("base64") !== vector.canonical_profile_utf8_base64) throw new Error("canonical bytes diverged");
    if (digest(envelope.profile) !== envelope.signed_payload_digest) return "signed_payload_digest_mismatch";
    const input = Buffer.from(signatureInput(envelope), "utf8");
    if (input.toString("base64") !== vector.signature_input_utf8_base64) throw new Error("signature bytes diverged");
    const key = createPublicKey({ key: spki(Buffer.from(issuer.public_key_base64, "base64")), format: "der", type: "spki" });
    if (!ed25519Verify(null, input, key, Buffer.from(envelope.signature, "base64"))) return "invalid_envelope_signature";
  } catch (error) { if (error.message.includes("diverged")) throw error; return "jcs_profile_value_invalid"; }
  if (envelope.subject_id !== verification.expected_subject_id) return "envelope_subject_mismatch";
  if (envelope.place !== verification.expected_place || envelope.space !== verification.expected_space) return "envelope_place_mismatch";
  return null;
}

function restrictionDigest(restriction) { return digest({ restriction }); }
function verifyAcknowledgement(vector) {
  const profile = vector.profile;
  const restrictions = [...new Set([...profile.restrictions, ...profile.operating_profile.restrictions])].sort();
  const operatingProfile = { ...profile.operating_profile }; delete operatingProfile.restrictions;
  const bindingInput = {
    status: profile.status, actor_id: profile.actor_id, place: profile.place, space: profile.space,
    policy_version: profile.policy_version, evidence_digest: profile.evidence_digest, binding: profile.binding,
    operating_profile: operatingProfile, effective_restrictions: restrictions,
    unresolved: profile.unresolved, reason_codes: profile.reason_codes,
  };
  const binding = `urn:spp:jcs-restriction-profile:${digest(bindingInput).slice(7)}`;
  if (binding !== vector.profile_binding) throw new Error("restriction profile binding diverged");
  for (const restriction of restrictions) {
    const d = restrictionDigest(restriction);
    if (d !== vector.restriction_digests[restriction]) throw new Error("restriction digest diverged");
    const acknowledgements = vector.acknowledgements.filter(item => item.restriction === restriction);
    const mappings = vector.enforcement_mappings.filter(item => item.restriction === restriction);
    if (acknowledgements.length !== 1 || mappings.length !== 1 || acknowledgements[0].profile_id !== binding || acknowledgements[0].restriction_digest !== d || mappings[0].restriction_digest !== d || !acknowledgements[0].enforcement_handler || acknowledgements[0].enforcement_handler !== mappings[0].enforcement_handler) return { outcome: "BLOCKED", may_rely: false };
  }
  return { outcome: "ACKNOWLEDGED", may_rely: true };
}

function main() {
  const vectors = strictJsonParse(readFileSync(process.argv[2] ?? new URL("./vectors.json", import.meta.url), "utf8"));
  let count = 0;
  for (const vector of vectors.vectors) {
    if (vector.kind === "jcs_admission_envelope") {
      const reason = verifyEnvelope(vector);
      if (vector.expected.verified !== (reason === null) || vector.expected.reason !== reason) throw new Error(`${vector.id}: expected ${JSON.stringify(vector.expected)}, got ${reason}`);
    } else if (vector.kind === "jcs_restriction_acknowledgement") {
      const result = verifyAcknowledgement(vector);
      if (result.outcome !== vector.expected.outcome || result.may_rely !== vector.expected.may_rely) throw new Error(`${vector.id}: acknowledgement mismatch`);
    } else throw new Error(`unknown vector kind ${vector.kind}`);
    count += 1;
  }
  for (const source of ['{"a":1,"\\u0061":2}', '{"value":NaN}', '{"value":-0}', '{"value":"\\ud800"}']) {
    let rejected = false; try { rejectUnsupported(strictJsonParse(source)); } catch { rejected = true; }
    if (!rejected) throw new Error(`fail-open raw JSON parser: ${source}`);
  }
  console.log(`JavaScript JCS verifier: ${count} vectors verified; duplicate, non-finite, and negative-zero JSON rejected`);
}

if (process.argv[1]?.endsWith("verify_vectors.mjs")) main();

export { strictJsonParse, rejectUnsupported, jcs };
