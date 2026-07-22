(*
 * ACC conveyor controller.
 *
 * The control decisions in this lab live here, in IEC 61131-3 Structured
 * Text. The external adapter only copies Modbus inputs into this program and
 * copies this program's outputs back to Modbus.
 *)

FUNCTION_BLOCK ConveyorControl
  VAR_INPUT
    Start : BOOL;
    StopHealthy : BOOL;
    EmergencyStopHealthy : BOOL;
    Reset : BOOL;
    LeftSensor : BOOL;
    RightSensor : BOOL;
  END_VAR
  VAR_OUTPUT
    Motor : BOOL;
    Reverse : BOOL;
    CycleComplete : BOOL;
    FaultLatched : BOOL;
  END_VAR
  VAR
    StartPrevious : BOOL;
  END_VAR

  CycleComplete := FALSE;

  IF NOT EmergencyStopHealthy THEN
    FaultLatched := TRUE;
  END_IF;

  IF Reset AND EmergencyStopHealthy AND StopHealthy AND NOT Motor THEN
    FaultLatched := FALSE;
  END_IF;

  IF NOT StopHealthy OR NOT EmergencyStopHealthy OR FaultLatched THEN
    Motor := FALSE;
    Reverse := FALSE;
  ELSE
    IF Start AND NOT StartPrevious AND NOT Reset THEN
      Motor := TRUE;
      Reverse := FALSE;
    END_IF;

    IF Motor AND NOT Reverse AND RightSensor THEN
      Reverse := TRUE;
    END_IF;

    IF Motor AND Reverse AND LeftSensor THEN
      Motor := FALSE;
      Reverse := FALSE;
      CycleComplete := TRUE;
    END_IF;
  END_IF;

  StartPrevious := Start;
END_FUNCTION_BLOCK

PROGRAM Conveyor
  VAR
    Start AT %IX0.0 : BOOL;
    StopHealthy AT %IX0.1 : BOOL;
    LeftSensor AT %IX0.2 : BOOL;
    RightSensor AT %IX0.3 : BOOL;

    (* ACC has no physical X5/X6. These remain Runtime variables until the
       scene or a remote-I/O adapter exposes dedicated E-stop and Reset. *)
    EmergencyStopHealthy : BOOL := TRUE;
    Reset : BOOL;

    Motor AT %QX0.0 : BOOL;
    Reverse AT %QX0.1 : BOOL;
    CycleComplete : BOOL;
    FaultLatched : BOOL;

    Control : ConveyorControl;
  END_VAR

  Control(
    Start := Start,
    StopHealthy := StopHealthy,
    EmergencyStopHealthy := EmergencyStopHealthy,
    Reset := Reset,
    LeftSensor := LeftSensor,
    RightSensor := RightSensor
  );

  Motor := Control.Motor;
  Reverse := Control.Reverse;
  CycleComplete := Control.CycleComplete;
  FaultLatched := Control.FaultLatched;
END_PROGRAM
