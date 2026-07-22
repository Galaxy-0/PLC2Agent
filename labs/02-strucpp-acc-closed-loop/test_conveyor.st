TEST 'start edge runs forward'
  VAR uut : ConveyorControl; END_VAR
  uut(Start := FALSE, StopHealthy := TRUE, EmergencyStopHealthy := TRUE, Reset := FALSE, LeftSensor := TRUE, RightSensor := FALSE);
  uut(Start := TRUE, StopHealthy := TRUE, EmergencyStopHealthy := TRUE, Reset := FALSE, LeftSensor := TRUE, RightSensor := FALSE);
  ASSERT_TRUE(uut.Motor);
  ASSERT_FALSE(uut.Reverse);
END_TEST

TEST 'right sensor reverses and left sensor completes cycle'
  VAR uut : ConveyorControl; END_VAR
  uut(Start := TRUE, StopHealthy := TRUE, EmergencyStopHealthy := TRUE, Reset := FALSE, LeftSensor := TRUE, RightSensor := FALSE);
  uut(Start := FALSE, StopHealthy := TRUE, EmergencyStopHealthy := TRUE, Reset := FALSE, LeftSensor := FALSE, RightSensor := TRUE);
  ASSERT_TRUE(uut.Motor);
  ASSERT_TRUE(uut.Reverse);
  ASSERT_FALSE(uut.CycleComplete);

  uut(Start := FALSE, StopHealthy := TRUE, EmergencyStopHealthy := TRUE, Reset := FALSE, LeftSensor := TRUE, RightSensor := FALSE);
  ASSERT_FALSE(uut.Motor);
  ASSERT_FALSE(uut.Reverse);
  ASSERT_TRUE(uut.CycleComplete);
END_TEST

TEST 'open stop circuit deenergizes both outputs'
  VAR uut : ConveyorControl; END_VAR
  uut(Start := TRUE, StopHealthy := TRUE, EmergencyStopHealthy := TRUE, Reset := FALSE, LeftSensor := FALSE, RightSensor := FALSE);
  ASSERT_TRUE(uut.Motor);
  uut(Start := FALSE, StopHealthy := FALSE, EmergencyStopHealthy := TRUE, Reset := FALSE, LeftSensor := FALSE, RightSensor := FALSE);
  ASSERT_FALSE(uut.Motor);
  ASSERT_FALSE(uut.Reverse);
  ASSERT_FALSE(uut.FaultLatched);
END_TEST

TEST 'held start does not restart after a completed cycle'
  VAR uut : ConveyorControl; END_VAR
  uut(Start := TRUE, StopHealthy := TRUE, EmergencyStopHealthy := TRUE, Reset := FALSE, LeftSensor := TRUE, RightSensor := FALSE);
  uut(Start := TRUE, StopHealthy := TRUE, EmergencyStopHealthy := TRUE, Reset := FALSE, LeftSensor := FALSE, RightSensor := TRUE);
  uut(Start := TRUE, StopHealthy := TRUE, EmergencyStopHealthy := TRUE, Reset := FALSE, LeftSensor := TRUE, RightSensor := FALSE);
  ASSERT_TRUE(uut.CycleComplete);
  ASSERT_FALSE(uut.Motor);

  uut(Start := TRUE, StopHealthy := TRUE, EmergencyStopHealthy := TRUE, Reset := FALSE, LeftSensor := TRUE, RightSensor := FALSE);
  ASSERT_FALSE(uut.Motor);
END_TEST

TEST 'emergency stop latches fault and deenergizes outputs'
  VAR uut : ConveyorControl; END_VAR
  uut(Start := TRUE, StopHealthy := TRUE, EmergencyStopHealthy := TRUE, Reset := FALSE, LeftSensor := FALSE, RightSensor := FALSE);
  ASSERT_TRUE(uut.Motor);

  uut(Start := FALSE, StopHealthy := TRUE, EmergencyStopHealthy := FALSE, Reset := FALSE, LeftSensor := FALSE, RightSensor := FALSE);
  ASSERT_FALSE(uut.Motor);
  ASSERT_FALSE(uut.Reverse);
  ASSERT_TRUE(uut.FaultLatched);

  uut(Start := FALSE, StopHealthy := TRUE, EmergencyStopHealthy := TRUE, Reset := FALSE, LeftSensor := FALSE, RightSensor := FALSE);
  ASSERT_FALSE(uut.Motor);
  ASSERT_TRUE(uut.FaultLatched);
END_TEST

TEST 'reset is rejected until safety circuit is healthy'
  VAR uut : ConveyorControl; END_VAR
  uut(Start := FALSE, StopHealthy := TRUE, EmergencyStopHealthy := FALSE, Reset := FALSE, LeftSensor := FALSE, RightSensor := FALSE);
  uut(Start := FALSE, StopHealthy := TRUE, EmergencyStopHealthy := FALSE, Reset := TRUE, LeftSensor := FALSE, RightSensor := FALSE);
  ASSERT_TRUE(uut.FaultLatched);

  uut(Start := FALSE, StopHealthy := TRUE, EmergencyStopHealthy := TRUE, Reset := TRUE, LeftSensor := FALSE, RightSensor := FALSE);
  ASSERT_FALSE(uut.FaultLatched);
  ASSERT_FALSE(uut.Motor);
END_TEST

TEST 'reset never causes automatic restart'
  VAR uut : ConveyorControl; END_VAR
  uut(Start := TRUE, StopHealthy := TRUE, EmergencyStopHealthy := TRUE, Reset := FALSE, LeftSensor := FALSE, RightSensor := FALSE);
  uut(Start := TRUE, StopHealthy := TRUE, EmergencyStopHealthy := FALSE, Reset := FALSE, LeftSensor := FALSE, RightSensor := FALSE);
  uut(Start := TRUE, StopHealthy := TRUE, EmergencyStopHealthy := TRUE, Reset := TRUE, LeftSensor := FALSE, RightSensor := FALSE);
  ASSERT_FALSE(uut.FaultLatched);
  ASSERT_FALSE(uut.Motor);

  uut(Start := TRUE, StopHealthy := TRUE, EmergencyStopHealthy := TRUE, Reset := FALSE, LeftSensor := FALSE, RightSensor := FALSE);
  ASSERT_FALSE(uut.Motor);

  uut(Start := FALSE, StopHealthy := TRUE, EmergencyStopHealthy := TRUE, Reset := FALSE, LeftSensor := FALSE, RightSensor := FALSE);
  uut(Start := TRUE, StopHealthy := TRUE, EmergencyStopHealthy := TRUE, Reset := FALSE, LeftSensor := FALSE, RightSensor := FALSE);
  ASSERT_TRUE(uut.Motor);
END_TEST
