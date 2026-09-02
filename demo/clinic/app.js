var endpoint = "http://127.0.0.1:8000";
var scenariosElement = document.querySelector("#scenarios");
var statusElement = document.querySelector("#status");

function valueOrDash(values) {
  return values && values.length ? values.join(", ") : "-";
}

function showDecision(scenario, result) {
  document.querySelector("#decision").textContent = result.decision.toUpperCase();
  document.querySelector("#reason").textContent = result.reason;
  document.querySelector("#matched-space").textContent = result.matched_space || "-";
  document.querySelector("#requires").textContent = valueOrDash(result.requires);

  var obligationText = "-";
  if (result.obligations && result.obligations.length) {
    obligationText = result.obligations.map(function (item) {
      return item.type + ": " + JSON.stringify(item.value);
    }).join("; ");
  }
  document.querySelector("#obligations").textContent = obligationText;
  document.querySelector("#decision-dot").className = "decision-dot " + result.decision;
  document.querySelector("#exchange").textContent = JSON.stringify(
    {request: scenario.request, response: result},
    null,
    2
  );
}

function runScenario(scenario) {
  fetch(endpoint + "/v1/decision", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify(scenario.request)
  })
    .then(function (response) {
      return response.json().then(function (body) {
        if (!response.ok) throw new Error(body.detail || response.statusText);
        return body;
      });
    })
    .then(function (body) {
      showDecision(scenario, body);
    })
    .catch(function (error) {
      document.querySelector("#decision").textContent = "SERVER UNAVAILABLE";
      document.querySelector("#reason").textContent = error.message;
      document.querySelector("#decision-dot").className = "decision-dot deny";
    });
}

function addScenario(scenario) {
  var button = document.createElement("button");
  var title = document.createElement("strong");
  var note = document.createElement("small");
  title.textContent = scenario.label;
  note.textContent = scenario.note;
  button.appendChild(title);
  button.appendChild(note);
  button.addEventListener("click", function () {
    runScenario(scenario);
  });
  scenariosElement.appendChild(button);
}

function start() {
  fetch("scenarios.json")
    .then(function (response) { return response.json(); })
    .then(function (scenarios) { scenarios.forEach(addScenario); })
    .catch(function (error) {
      statusElement.textContent = "Could not load scenarios: " + error.message;
      statusElement.classList.add("offline");
    });

  fetch(endpoint + "/health")
    .then(function (response) { return response.json(); })
    .then(function (health) {
      statusElement.textContent =
        "Policy server online / " + health.engine + " engine / policy v" +
        health.policy_version;
      statusElement.classList.add("online");
    })
    .catch(function () {
      statusElement.textContent = "Policy server offline / start the policy server";
      statusElement.classList.add("offline");
    });
}

start();
