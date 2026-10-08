(* Transactional two-station transfer. Deterministic scan = 20 ms.
   This is a simulation reference, NOT a safety PLC program. *)
FUNCTION_BLOCK CellControl
VAR_INPUT
  StartPb : BOOL;
  StopPb : BOOL;
  ResetPb : BOOL;
  EStopOk : BOOL := TRUE;
  CommFresh : BOOL := TRUE;
  AutoMode : BOOL := TRUE;
  DownstreamReady : BOOL := TRUE;
  ReqValid : BOOL;
  ReqSeq : DINT;
  AckValid : BOOL;
  AckSeq : DINT;
  Extended : BOOL;
  Retracted : BOOL := TRUE;
  RecipeCommit : BOOL;
  RecipeVersion : DINT;
  RecipeTimeoutTicks : INT := 30;
  RecipeDelayTicks : INT := 2;
END_VAR
VAR_OUTPUT
  ExtendCmd : BOOL;
  RetractCmd : BOOL;
  FeedPermit : BOOL;
  Busy : BOOL;
  FaultLatched : BOOL;
  FaultCode : INT;
  State : INT;
  AcceptedSeq : DINT;
  DoneSeq : DINT;
  CompletedCount : DINT;
  ActiveRecipeVersion : DINT;
  ActiveTimeoutTicks : INT := 30;
  ActiveDelayTicks : INT := 2;
  CycleTimeoutTicks : INT := 30;
  CycleDelayTicks : INT := 2;
  RecipeRejected : BOOL;
END_VAR
VAR
  PrevStart : BOOL;
  PrevReset : BOOL;
  PrevRecipe : BOOL;
  Drain : BOOL;
  StateTicks : INT;
  LastAccepted : DINT;
END_VAR

(* Preserve the first fault. Reset requires a new edge and reconciled home. *)
IF NOT FaultLatched THEN
  IF NOT EStopOk THEN
    FaultCode := 101;
  ELSIF NOT CommFresh THEN
    FaultCode := 102;
  ELSIF Extended AND Retracted THEN
    FaultCode := 103;
  ELSIF (State >= 20) AND (State <= 40) AND NOT AutoMode THEN
    FaultCode := 104;
  END_IF;
  IF FaultCode <> 0 THEN
    FaultLatched := TRUE;
    State := 90;
  END_IF;
END_IF;

IF FaultLatched AND ResetPb AND NOT PrevReset AND EStopOk AND CommFresh
  AND AutoMode AND Retracted AND NOT Extended AND NOT StartPb AND NOT ReqValid THEN
  FaultLatched := FALSE;
  FaultCode := 0;
  State := 0;
  StateTicks := 0;
  Drain := FALSE;
END_IF;

RecipeRejected := FALSE;
IF RecipeCommit AND NOT PrevRecipe THEN
  IF NOT FaultLatched AND ((State = 0) OR (State = 10))
    AND (RecipeVersion > ActiveRecipeVersion)
    AND (RecipeTimeoutTicks >= 5) AND (RecipeTimeoutTicks <= 200)
    AND (RecipeDelayTicks >= 0) AND (RecipeDelayTicks < RecipeTimeoutTicks) THEN
    ActiveRecipeVersion := RecipeVersion;
    ActiveTimeoutTicks := RecipeTimeoutTicks;
    ActiveDelayTicks := RecipeDelayTicks;
  ELSE
    RecipeRejected := TRUE;
  END_IF;
END_IF;

IF NOT FaultLatched THEN
  IF StopPb THEN
    Drain := TRUE;
  END_IF;
  IF (State = 0) AND StartPb AND NOT PrevStart AND AutoMode
    AND NOT ResetPb AND NOT StopPb AND Retracted AND NOT Extended THEN
    State := 10;
    Drain := FALSE;
  END_IF;

  CASE State OF
    10:
      IF Drain OR NOT AutoMode THEN
        State := 0;
      ELSIF ReqValid AND (ReqSeq > LastAccepted) AND (ReqSeq > 0)
        AND (ReqSeq <= 2147483000) AND DownstreamReady
        AND Retracted AND NOT Extended THEN
        AcceptedSeq := ReqSeq;
        LastAccepted := ReqSeq;
        CycleTimeoutTicks := ActiveTimeoutTicks;
        CycleDelayTicks := ActiveDelayTicks;
        State := 20;
        StateTicks := 0;
      END_IF;
    20:
      StateTicks := StateTicks + 1;
      IF Extended AND NOT Retracted THEN
        State := 30;
        StateTicks := 0;
      ELSIF StateTicks >= CycleTimeoutTicks THEN
        FaultCode := 201;
      END_IF;
    30:
      StateTicks := StateTicks + 1;
      IF AckValid AND (AckSeq = AcceptedSeq) AND (StateTicks >= CycleDelayTicks) THEN
        State := 40;
        StateTicks := 0;
      ELSIF StateTicks >= CycleTimeoutTicks THEN
        FaultCode := 202;
      END_IF;
    40:
      StateTicks := StateTicks + 1;
      IF Retracted AND NOT Extended THEN
        DoneSeq := AcceptedSeq;
        CompletedCount := CompletedCount + 1;
        IF Drain THEN State := 0; ELSE State := 10; END_IF;
        StateTicks := 0;
      ELSIF StateTicks >= CycleTimeoutTicks THEN
        FaultCode := 203;
      END_IF;
  END_CASE;
  IF FaultCode <> 0 THEN
    FaultLatched := TRUE;
    State := 90;
  END_IF;
END_IF;

(* Outputs are computed after all guards and transitions. *)
ExtendCmd := NOT FaultLatched AND ((State = 20) OR (State = 30));
RetractCmd := NOT FaultLatched AND (State = 40);
FeedPermit := NOT FaultLatched AND (State = 10) AND NOT Drain AND AutoMode;
Busy := (State >= 20) AND (State <= 40);
PrevStart := StartPb;
PrevReset := ResetPb;
PrevRecipe := RecipeCommit;
END_FUNCTION_BLOCK
