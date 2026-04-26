# Recommended Sources

These are good starting references for your project report and implementation.

## Official SUMO Documentation

- SUMO documentation:
  [https://eclipse.dev/sumo/docs/](https://eclipse.dev/sumo/docs/)
- TraCI overview:
  [https://eclipse.dev/sumo/docs/TraCI/index.html](https://eclipse.dev/sumo/docs/TraCI/index.html)
- Interfacing TraCI from Python:
  [https://eclipse.dev/sumo/docs/TraCI/Interfacing_TraCI_from_Python.html](https://eclipse.dev/sumo/docs/TraCI/Interfacing_TraCI_from_Python.html)
- Lane value retrieval, including lane max speed:
  [https://eclipse.dev/sumo/docs/TraCI/Lane_Value_Retrieval.html](https://eclipse.dev/sumo/docs/TraCI/Lane_Value_Retrieval.html)
- Vehicle state changes:
  [https://eclipse.dev/sumo/docs/TraCI/Change_Vehicle_State.html](https://eclipse.dev/sumo/docs/TraCI/Change_Vehicle_State.html)

## Foundational TraCI / VANET References

- Wegener et al., "TraCI: An Interface for Coupling Road Traffic and Network Simulators":
  [https://doi.org/10.1145/1400713.1400740](https://doi.org/10.1145/1400713.1400740)
- Wegener et al., "VANET Simulation Environment with Feedback Loop and its Application to Traffic Light Assistance":
  [https://doi.org/10.1109/GLOCOMW.2008.ECP.67](https://doi.org/10.1109/GLOCOMW.2008.ECP.67)

## Why These Sources Matter

- The SUMO docs explain the exact APIs used in this project.
- The TraCI paper motivates online coupling between traffic behavior and communication logic.
- The VANET feedback-loop paper is useful when you justify why traffic and communication should influence each other during runtime.
