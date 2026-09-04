# Clinic demo

The demo has two modes:

1. Run `python demo/clinic/run_demo.py` for a zero-service command-line proof.
2. Start the policy server as shown in the root README, then serve this
   directory on port 8080:

   ```sh
   python -m http.server 8080 -d demo/clinic
   ```

Open <http://127.0.0.1:8080>. The browser sends the six included intents to the
reference server and exposes both the decision and raw protocol exchange.

This scaffold does not include Gazebo, Nav2, or Open-RMF. Its purpose is to make
the protocol behavior independently runnable before adding a heavyweight
simulation.
