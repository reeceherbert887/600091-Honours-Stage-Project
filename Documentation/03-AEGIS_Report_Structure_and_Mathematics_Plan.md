# AEGIS Honours Stage Project --- Report Structure and Mathematics Plan

## Project

**AEGIS --- Anomaly Evaluation and Guard Intelligent System**

The report should tell a continuous technical story:

**robotics theory → Niryo robotic arm → telemetry → data collection →
anomaly detection → digital twin/dashboard → testing and evaluation**

The mathematics should not be included simply as a separate collection
of equations. It should explain how the robotic arm behaves, how its
behaviour can be measured, and how those measurements can be used by
AEGIS to identify abnormal operation.

------------------------------------------------------------------------

# 1. Proposed Report Structure

## 1. Introduction

Introduce the project and establish the problem being addressed.

Possible content:

-   Background to robotic condition monitoring
-   The problem AEGIS is intended to address
-   Project aim
-   Project objectives
-   Project scope
-   Why a Niryo robotic arm is being used
-   Overview of the proposed system
-   Limitations and optional extensions

The introduction should make it clear that AEGIS is primarily a
**condition-monitoring and anomaly-detection system**, rather than a
replacement robot controller.

------------------------------------------------------------------------

## 2. Background and Initial Research

This chapter should explain the technologies and research that informed
the design.

Possible sections:

### 2.1 Industrial and Educational Robotic Manipulators

Explain robotic manipulators, joints, links, actuators, controllers,
sensors and degrees of freedom.

### 2.2 The Niryo Robotic Arm

Research the particular Niryo model being used, including:

-   Number and type of joints
-   Degrees of freedom
-   Joint limits
-   Actuators
-   Encoders and position feedback
-   Coordinate frames
-   End effector
-   Robot controller
-   ROS/ROS 1 architecture where applicable
-   Available communication interfaces
-   Available telemetry
-   How motion commands are executed

Conceptually:

``` text
Target motion
      ↓
Robot controller
      ↓
Joint actuators
      ↓
Physical robot movement
```

AEGIS operates alongside this control system by observing the robot's
behaviour.

### 2.3 Condition Monitoring

Research methods of monitoring machinery and robots using measurements
such as:

-   Joint position
-   Position error
-   Velocity
-   Motor current
-   Motor temperature
-   Vibration
-   Execution time
-   Communication state

### 2.4 Telemetry and MQTT

Explain why telemetry is collected and why MQTT is suitable for
transmitting measurements between components.

### 2.5 Data Logging and SQLite

Explain why historical telemetry is needed and how SQLite can store
experimental runs and individual telemetry samples.

### 2.6 Digital Twins

Explain the concept of a digital twin and how the Node-RED interface
provides a digital representation of the condition and behaviour of the
robotic arm.

### 2.7 Artificial Intelligence and Anomaly Detection

Research suitable methods for identifying unusual behaviour from robot
telemetry.

------------------------------------------------------------------------

# 3. Mathematical and Robotic Foundations

This chapter establishes the mathematics needed to understand the robot
and the data used by AEGIS.

## 3.1 Joint Variables and Configuration Space

A robot's configuration can be represented using a vector:

\[ `\mathbf{q}`{=tex} =
```{=tex}
\begin{bmatrix}
q_1 \\
q_2 \\
\vdots \\
q_n
\end{bmatrix}
```
\]

Each (q_i) describes the state of one joint.

For a revolute joint, the joint variable is normally an angle:

\[ q_i = `\theta`{=tex}\_i \]

For a prismatic joint, it represents linear displacement:

\[ q_i = d_i \]

This is important to AEGIS because measured joint configurations form
part of the robot telemetry.

------------------------------------------------------------------------

## 3.2 Coordinate Frames and Transformations

A robotic arm contains multiple coordinate frames, such as:

-   World/base frame
-   Individual joint frames
-   Link frames
-   End-effector/tool frame

The report should explain:

-   Position vectors
-   Rotation matrices
-   Translation
-   Homogeneous transformation matrices
-   Transformation between coordinate frames

A homogeneous transformation can be represented as:

\[ T =
```{=tex}
\begin{bmatrix}
R & p \\
0 & 1
\end{bmatrix}
```
\]

where (R) describes rotation and (p) describes translation.

These transformations are fundamental to understanding how the positions
of the Niryo's joints determine the position and orientation of its end
effector.

------------------------------------------------------------------------

## 3.3 Forward Kinematics

Forward kinematics calculates the end-effector pose from known joint
variables.

Conceptually:

``` text
Joint configuration
        ↓
Forward kinematics
        ↓
End-effector pose
```

or:

\[ `\mathbf{x}`{=tex}=f(`\mathbf{q}`{=tex}) \]

This is particularly relevant to the AEGIS digital twin because measured
joint positions can be used to reproduce the physical robot's
configuration in a simulated or visual representation.

------------------------------------------------------------------------

## 3.4 Inverse Kinematics

Inverse kinematics performs the opposite operation.

``` text
Desired end-effector pose
          ↓
Inverse kinematics
          ↓
Required joint configuration
```

Conceptually:

\[ `\mathbf{q}`{=tex}=f\^{-1}(`\mathbf{x}`{=tex}) \]

AEGIS does not necessarily need to implement its own complete
inverse-kinematics solver, but understanding inverse kinematics is
important for explaining how robotic manipulators such as the Niryo
execute Cartesian motion commands.

------------------------------------------------------------------------

## 3.5 Joint Velocity and Acceleration

Joint velocity is:

\[ `\dot{q}`{=tex}=`\frac{dq}{dt}`{=tex} \]

and joint acceleration is:

\[ `\ddot{q}`{=tex}=`\frac{d^2q}{dt^2}`{=tex} \]

These quantities can provide useful information about how a joint is
behaving rather than only where the joint is located.

Unexpected velocity or acceleration behaviour could potentially
contribute to anomaly detection.

------------------------------------------------------------------------

## 3.6 Position and Tracking Error

Position error is one of the most directly useful mathematical
quantities for AEGIS.

For joint (i):

\[
e_i(t)=q\_{i,`\text{desired}`{=tex}}(t)-q\_{i,`\text{actual}`{=tex}}(t)
\]

For example, if:

\[ q\_{`\text{desired}`{=tex}}=1.20`\text{ rad}`{=tex} \]

and:

\[ q\_{`\text{actual}`{=tex}}=1.16`\text{ rad}`{=tex} \]

then:

\[ e=1.20-1.16=0.04`\text{ rad}`{=tex} \]

The important point is that this is not only a robotics equation. The
resulting error value can become an **AEGIS telemetry feature**.

Increasing position error could indicate that the physical robot is
having difficulty following its commanded trajectory.

------------------------------------------------------------------------

## 3.7 Jacobians

Once the earlier kinematic concepts are understood, the Jacobian can be
introduced.

A common relationship is:

\[ `\dot{x}`{=tex}=J(q)`\dot{q}`{=tex} \]

where:

-   (`\dot{x}`{=tex}) represents end-effector velocity;
-   (J(q)) is the robot Jacobian;
-   (`\dot{q}`{=tex}) represents joint velocities.

Jacobians are useful for understanding the relationship between
individual joint movement and Cartesian end-effector movement.

They are useful to AEGIS, but are a lower priority than configuration
space, transformations, forward kinematics and tracking error.

------------------------------------------------------------------------

## 3.8 Telemetry Mathematics

Robot measurements should be analysed mathematically rather than treated
only as raw numbers.

Useful quantities include:

-   Mean
-   Minimum and maximum
-   Variance
-   Standard deviation
-   Moving averages
-   Root Mean Square (RMS)
-   Rate of change
-   Correlation
-   Normalisation/standardisation

For a collection of (N) measurements:

\[ `\bar`{=tex}{x}=`\frac{1}{N}`{=tex}`\sum`{=tex}\_{i=1}\^{N}x_i \]

Standard deviation can be used to quantify variation in measurements.

For vibration data, RMS may be useful:

\[ x\_{`\mathrm{RMS}`{=tex}}=
`\sqrt{\frac{1}{N}\sum_{i=1}^{N}x_i^2}`{=tex} \]

These techniques can turn raw sensor measurements into more meaningful
condition-monitoring features.

------------------------------------------------------------------------

## 3.9 Relationship Between Mathematics and AEGIS

The mathematical foundation should eventually connect directly to
condition monitoring.

For example, abnormal operation might produce:

\[ e `\uparrow`{=tex},`\qquad`{=tex} I `\uparrow`{=tex},`\qquad`{=tex} T
`\uparrow`{=tex},`\qquad`{=tex}
a\_{`\text{vibration}`{=tex}}`\uparrow`{=tex} \]

where:

-   \(e\) = position/tracking error
-   \(I\) = motor current
-   \(T\) = motor temperature
-   (a\_{`\text{vibration}`{=tex}}) = measured vibration

A single unusual measurement may not necessarily indicate a fault.

However, several measurements changing together can provide stronger
evidence that the robotic arm is operating abnormally.

The overall relationship is:

``` text
Robot mathematics
       ↓
Physical behaviour
       ↓
Sensor measurements
       ↓
Telemetry
       ↓
Feature extraction / processing
       ↓
Anomaly detection
       ↓
Normal / Warning / Fault
```

------------------------------------------------------------------------

# 4. System Design and Architecture

This chapter should explain how the complete AEGIS system was designed
before discussing its implementation.

A high-level architecture is:

``` text
                     NIRYO ROBOT
                          │
              ┌───────────┴───────────┐
              │                       │
         Robot motion            Sensors/state
              │                       │
      joint positions       current/temp/vibration
              │                       │
              └───────────┬───────────┘
                          │
                       Telemetry
                          │
                         MQTT
                          │
               ┌──────────┴──────────┐
               │                     │
             SQLite               Node-RED
               │                     │
        Historical data        Live monitoring
               │
          Python / ML
               │
          Anomaly score
               │
               └───────────────→ Node-RED
                                     │
                           NORMAL/WARNING/FAULT
```

Possible sections include:

-   Requirements
-   Overall architecture
-   Robot interface
-   Telemetry design
-   MQTT topic structure
-   Database design
-   Node-RED dashboard design
-   Anomaly-detection pipeline
-   Digital-twin design
-   Safety considerations
-   Optional robot response

------------------------------------------------------------------------

# 5. Implementation

This chapter explains what was actually built.

Possible sections:

-   Niryo communication
-   Robot motion experiments
-   Telemetry collection
-   MQTT implementation
-   SQLite implementation
-   Node-RED implementation
-   Digital twin implementation
-   Python data-processing system
-   Fault injection
-   Machine-learning/anomaly-detection implementation
-   Integration of all components

The implementation chapter should describe **how the design became a
working system**, rather than repeating the theory from the earlier
chapters.

------------------------------------------------------------------------

# 6. Software and Algorithm Implementation

This is a more appropriate title than "Code Report".

The report should not contain large amounts of complete source code.

Instead, discuss:

-   Important algorithms
-   Key software components
-   Important functions/classes
-   Data structures
-   MQTT message format
-   Database operations
-   Telemetry processing
-   Feature extraction
-   Anomaly calculations
-   Error handling
-   Integration between programs

Small code extracts can be included where they help explain an important
implementation decision.

Complete source code can remain in the project repository and/or
appendix where required.

------------------------------------------------------------------------

# 7. Testing, Results and Evaluation

This chapter demonstrates whether AEGIS actually works.

Possible experiments include:

-   Normal operation
-   Increased friction
-   Blocked joint
-   Added payload/overload
-   Position error or miscalibration
-   Loose joint/vibration if practical

Measurements could include:

-   Joint position
-   Position error
-   Joint velocity
-   Motor current
-   Temperature
-   Vibration
-   Movement duration
-   Anomaly score

Results should be presented using suitable:

-   Tables
-   Graphs
-   Statistical summaries
-   Comparisons between normal and abnormal runs

The evaluation should determine whether the system can reliably
distinguish normal behaviour from abnormal behaviour.

------------------------------------------------------------------------

# 8. Discussion

Discuss what the results mean rather than simply repeating them.

Possible topics:

-   Why particular faults produced particular telemetry changes
-   Which telemetry signals were most useful
-   False positives and false negatives
-   Reliability of the anomaly-detection method
-   Simulation versus physical robot behaviour
-   Limitations of sensors
-   Limitations of the Niryo platform
-   MQTT/network limitations
-   Digital-twin accuracy
-   Whether the original design objectives were achieved
-   Comparison with findings from academic research

------------------------------------------------------------------------

# 9. Conclusion and Future Work

Summarise:

-   What AEGIS was designed to do
-   What was implemented
-   Main findings
-   Whether the objectives were achieved
-   Major limitations

Potential future work could include:

-   More physical sensors
-   Additional fault types
-   Larger training datasets
-   Improved machine-learning models
-   More advanced digital twin
-   Predictive maintenance
-   Automatic slow/stop responses
-   Testing on other robotic manipulators

------------------------------------------------------------------------

# Mathematics Priority for AEGIS

Not every area of robotics mathematics is equally important for this
project.

## Priority 1 --- Essential

### Joint Variables and Configuration Space

Understand:

-   Degrees of freedom
-   Revolute joints
-   Prismatic joints
-   Joint variables
-   Configuration vectors
-   Joint limits

This provides the mathematical representation of the robot's state.

### Coordinate Frames and Transformations

Understand:

-   Coordinate systems
-   Rotation
-   Translation
-   Rotation matrices
-   Homogeneous transformation matrices

These concepts explain how individual links and joints relate spatially.

### Forward Kinematics

Understand how:

\[ q_1,q_2,`\ldots`{=tex},q_n \]

produce an end-effector pose.

This is particularly important for understanding and constructing the
digital twin.

### Position and Tracking Error

Understand:

\[ e_i=q\_{i,`\text{desired}`{=tex}}-q\_{i,`\text{actual}`{=tex}} \]

This is one of the strongest mathematical links between conventional
robotics and the AEGIS condition-monitoring system.

------------------------------------------------------------------------

# Priority 2 --- Very Important

## Velocity and Acceleration

Understand:

\[ `\dot `{=tex}q=`\frac{dq}{dt}`{=tex} \]

and:

\[ `\ddot `{=tex}q=`\frac{d^2q}{dt^2}`{=tex} \]

These describe how robot motion changes over time and can provide
additional anomaly-detection features.

## Statistics

Important topics include:

-   Mean
-   Median
-   Variance
-   Standard deviation
-   Minimum/maximum
-   Moving averages
-   RMS
-   Correlation
-   Normalisation
-   Z-scores

This mathematics is extremely important when converting collected
telemetry into information suitable for anomaly detection.

## Signal Processing

Particularly useful for vibration measurements.

Possible areas include:

-   Sampling frequency
-   Noise
-   Filtering
-   Moving-average filters
-   RMS vibration
-   Frequency
-   Fast Fourier Transform (FFT), if justified by the project

------------------------------------------------------------------------

# Priority 3 --- Important Robotics Knowledge

## Inverse Kinematics

Understand what inverse kinematics does and how it relates Cartesian
targets to required joint configurations.

It is useful for understanding how the Niryo works, although AEGIS may
not need to implement a complete inverse-kinematics solver itself.

## Jacobians

Understand the basic relationship:

\[ `\dot{x}`{=tex}=J(q)`\dot{q}`{=tex} \]

This connects joint velocity with end-effector velocity.

It becomes more useful if AEGIS compares expected Cartesian motion
against measured joint behaviour.

------------------------------------------------------------------------

# Priority 4 --- Machine-Learning Mathematics

The exact mathematics will depend on the final anomaly-detection
algorithm.

Useful foundations include:

-   Feature scaling
-   Normalisation
-   Standardisation
-   Euclidean distance
-   Probability distributions
-   Correlation
-   Covariance
-   Principal Component Analysis (PCA)
-   Anomaly scores
-   Threshold selection
-   Precision
-   Recall
-   F1 score
-   Confusion matrices

More specialised mathematics should be added once the final model has
been selected.

------------------------------------------------------------------------

# Lower Priority

Topics such as full rigid-body dynamics, Lagrangian mechanics and
detailed torque derivations are useful robotics knowledge, but they
should not initially receive as much attention as:

``` text
Configuration space
        ↓
Transformations
        ↓
Forward kinematics
        ↓
Position / trajectory error
        ↓
Velocity and acceleration
        ↓
Telemetry statistics
        ↓
Signal processing
        ↓
Anomaly detection
```

AEGIS is primarily a **condition-monitoring and anomaly-detection
project**, not a project to design a new robotic manipulator or
low-level motion controller.

Therefore, the most valuable mathematical knowledge is the mathematics
that connects **robot motion to measurable behaviour and measurable
behaviour to fault detection**.

------------------------------------------------------------------------

# Central AEGIS Mathematical Idea

The key relationship to maintain throughout the project and report is:

\[ `\boxed{
\text{Robot State}
\rightarrow
\text{Expected Behaviour}
\rightarrow
\text{Measured Behaviour}
\rightarrow
\text{Difference / Features}
\rightarrow
\text{Anomaly Detection}
}`{=tex} \]

For example:

``` text
Commanded joint angle ─┐
                       ├──> Position error ──────┐
Measured joint angle ──┘                         │
                                                 │
Motor current ───────────────────────────────────┤
                                                 │
Motor temperature ───────────────────────────────┤
                                                 ├──> Feature set
Vibration ───────────────────────────────────────┤         │
                                                 │         ↓
Joint velocity/acceleration ─────────────────────┘   Anomaly model
                                                           │
                                                           ↓
                                              Normal / Warning / Fault
```

This provides a direct connection between the robotics mathematics,
Niryo arm, telemetry system, database, machine-learning component and
Node-RED digital twin.
