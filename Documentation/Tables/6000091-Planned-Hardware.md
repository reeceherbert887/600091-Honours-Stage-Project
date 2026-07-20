| Component                       | Purpose                                 |        Priority |
| ------------------------------- | --------------------------------------- | --------------: |
| Existing desktop robotic arm    | Experimental platform                   |       Essential |
| ESP32 development board         | Sensor collection and MQTT transmission |       Essential |
| Suitable current/voltage sensor | Detect load and electrical changes      |       Essential |
| One temperature sensor          | Detect gradual motor heating            |       Essential |
| Emergency-stop system           | Safe testing                            |       Essential |
| Correct regulated power supply  | Stable and safe operation               |       Essential |
| IMU/accelerometer               | Detect abnormal vibration               |     Recommended |
| Joint feedback/encoder          | Compare actual and commanded motion     |  Depends on arm |
| RTC module                      | Offline timestamps                      |        Optional |
| Multiple sensors per joint      | Detailed fault localisation             | Later extension |
