import argparse
import math
import random
import time
from pathlib import Path

import pybullet as p
import pybullet_data


# ============================================================
# Simulation_Configuration
# ============================================================

Simulation_Rate = 240
Time_Step = 1.0 / Simulation_Rate

Movement_Duration = 6.0
Settling_Duration = 1.0
Total_Duration = Movement_Duration + Settling_Duration

Telemetry_Rate = 20
Telemetry_Interval = 1.0 / Telemetry_Rate

Print_Rate = 4
Print_Interval = 1.0 / Print_Rate

Start_Angles = [
    0.0,
    0.0,
]

Target_Angles = [
    math.radians(70),
    math.radians(-95),
]

Motor_Torque = 0.45
Ambient_Temprature = 22.0

SCENARIOS = [
    "normal",
    "increased_friction",
    "blocked_joint",
]


# ============================================================
# COMMAND-LINE ARGUMENTS
# ============================================================

def parse_arguments():
    parser = argparse.ArgumentParser(
        description="AEGIS two-joint robotic-arm simulator"
    )

    parser.add_argument(
        "--scenario",
        choices=SCENARIOS,
        default="normal",
        help="Operating condition to simulate",
    )

    return parser.parse_args()


# ============================================================
# MOVEMENT GENERATION
# ============================================================

def smooth_trajectory(progress):
    """
    Convert linear progress into a smooth start-and-stop
    trajectory.

    A progress value of 0 produces 0.
    A progress value of 1 produces 1.
    """
    progress = max(0.0, min(1.0, progress))

    return 0.5 - 0.5 * math.cos(math.pi * progress)


def calculate_commanded_angles(elapsed_time):
    """
    Calculate the commanded position of both joints.
    """
    progress = elapsed_time / Movement_Duration
    smoothed_progress = smooth_trajectory(progress)

    commanded_angles = []

    for start_angle, target_angle in zip(
        Start_Angles,
        Target_Angles,
    ):
        angle = start_angle + (
            target_angle - start_angle
        ) * smoothed_progress

        commanded_angles.append(angle)

    return commanded_angles


# ============================================================
# SYNTHETIC SENSOR MODELS
# ============================================================

def estimate_current(
    torque,
    scenario,
    fault_active,
    joint_id,
):
    """
    Estimate motor current from simulated joint torque.

    This is synthetic data and is not a measurement from a
    physical motor.
    """
    base_current = 0.18
    electrical_noise = random.gauss(0.0, 0.015)

    estimated_current = (
        base_current
        + abs(torque) / Motor_Torque
        + electrical_noise
    )

    # The simulated fault only affects Joint 2.
    if (
        joint_id == 1
        and fault_active
        and scenario == "increased_friction"
    ):
        estimated_current += 0.45

    if (
        joint_id == 1
        and fault_active
        and scenario == "blocked_joint"
    ):
        # Simulate a motor drawing more current while attempting
        # to move a mechanically blocked joint.
        estimated_current += 2.20

    return max(0.0, estimated_current)


def update_temperature(
    current_temperature,
    motor_current,
    scenario,
    fault_active,
    joint_id,
):
    """
    Produce a simplified synthetic motor-temperature response.
    """
    heating_rate = 0.045 * motor_current**2

    cooling_rate = 0.025 * (
        current_temperature - Ambient_Temprature
    )

    # Apply additional heating only to Joint 2.
    if (
        joint_id == 1
        and fault_active
        and scenario == "increased_friction"
    ):
        heating_rate *= 1.35

    if (
        joint_id == 1
        and fault_active
        and scenario == "blocked_joint"
    ):
        heating_rate *= 1.75

    temperature_change = (
        heating_rate - cooling_rate
    ) * Telemetry_Interval

    sensor_noise = random.gauss(0.0, 0.015)

    return (
        current_temperature
        + temperature_change
        + sensor_noise
    )


def estimate_vibration(
    velocity,
    previous_velocity,
    scenario,
    fault_active,
    joint_id,
):
    """
    Generate a simplified synthetic vibration reading.
    """
    acceleration = (
        velocity - previous_velocity
    ) / Telemetry_Interval

    vibration = (
        0.02
        + 0.004 * abs(velocity)
        + 0.0005 * abs(acceleration)
    )

    # Apply fault vibration only to Joint 2.
    if (
        joint_id == 1
        and fault_active
        and scenario == "increased_friction"
    ):
        vibration += random.uniform(0.05, 0.10)

    elif (
        joint_id == 1
        and fault_active
        and scenario == "blocked_joint"
    ):
        vibration += random.uniform(0.12, 0.20)

    vibration += random.gauss(0.0, 0.005)

    return max(0.0, vibration)


# ============================================================
# ROBOT CONFIGURATION AND CONTROL
# ============================================================

def configure_robot_for_scenario(robot_id, scenario):
    """
    Configure the simulated dynamics for the selected scenario.
    """
    if scenario == "normal":
        for joint_id in [0, 1]:
            p.changeDynamics(
                robot_id,
                joint_id,
                jointDamping=0.15,
            )

    elif scenario == "increased_friction":
        # Joint 1 remains normal.
        p.changeDynamics(
            robot_id,
            0,
            jointDamping=0.15,
        )

        # Joint 2 experiences increased resistance.
        p.changeDynamics(
            robot_id,
            1,
            jointDamping=4.0,
        )

    elif scenario == "blocked_joint":
        for joint_id in [0, 1]:
            p.changeDynamics(
                robot_id,
                joint_id,
                jointDamping=0.15,
            )


def apply_joint_control(
    robot_id,
    commanded_angles,
    scenario,
    elapsed_time,
    blocked_angle,
):
    """
    Apply position-control commands to both robot joints.
    """
    forces = [
        45.0,
        35.0,
    ]

    position_gains = [
        0.30,
        0.30,
    ]

    if scenario == "increased_friction":
        # Joint 2 receives less usable control force and responds
        # more slowly because of the simulated friction.
        forces[1] = 2.0
        position_gains[1] = 0.06

    for joint_id in [0, 1]:
        target_angle = commanded_angles[joint_id]

        # Joint 2 becomes locked after 40% of the movement.
        if (
            scenario == "blocked_joint"
            and joint_id == 1
            and elapsed_time >= Movement_Duration * 0.40
            and blocked_angle is not None
        ):
            target_angle = blocked_angle
            forces[joint_id] = 80.0
            position_gains[joint_id] = 0.80

        p.setJointMotorControl2(
            bodyUniqueId=robot_id,
            jointIndex=joint_id,
            controlMode=p.POSITION_CONTROL,
            targetPosition=target_angle,
            force=forces[joint_id],
            positionGain=position_gains[joint_id],
            velocityGain=0.80,
        )


# ============================================================
# TERMINAL DISPLAY
# ============================================================

def print_heading(scenario):
    print()
    print("=" * 130)
    print("AEGIS TWO-JOINT ROBOTIC-ARM SIMULATION")
    print(f"Scenario: {scenario}")
    print("=" * 130)

    print(
        f"{'Time':>6} | "
        f"{'J1 angle':>9} | "
        f"{'J1 error':>8} | "
        f"{'J1 current':>10} | "
        f"{'J1 temp':>8} | "
        f"{'J2 angle':>9} | "
        f"{'J2 error':>8} | "
        f"{'J2 current':>10} | "
        f"{'J2 temp':>8} | "
        f"{'Vibration':>9}"
    )

    print("-" * 130)


# ============================================================
# MAIN SIMULATION
# ============================================================

def main():
    args = parse_arguments()
    scenario = args.scenario

    # The fixed seed makes the generated sensor noise repeatable.
    random.seed(600091)

    simulation_directory = Path(__file__).resolve().parent
    project_directory = simulation_directory.parent

    robot_model = (
        project_directory
        / "models"
        / "two_joint_arm.urdf"
    )

    if not robot_model.exists():
        raise FileNotFoundError(
            f"Robot model was not found: {robot_model}"
        )

    physics_client = p.connect(p.GUI)

    if physics_client < 0:
        raise RuntimeError(
            "PyBullet could not open the graphical simulation."
        )

    # Remove PyBullet's large diagnostic panels.
    p.configureDebugVisualizer(
        p.COV_ENABLE_GUI,
        0,
    )

    p.configureDebugVisualizer(
        p.COV_ENABLE_SHADOWS,
        1,
    )

    p.setAdditionalSearchPath(
        pybullet_data.getDataPath()
    )

    p.setGravity(0, 0, -9.81)
    p.setTimeStep(Time_Step)

    # Load the floor.
    p.loadURDF("plane.urdf")

    # Load the custom two-joint arm.
    robot_id = p.loadURDF(
        str(robot_model),
        basePosition=[0, 0, 0],
        useFixedBase=True,
    )

    p.resetDebugVisualizerCamera(
        cameraDistance=1.8,
        cameraYaw=40,
        cameraPitch=-55,
        cameraTargetPosition=[0.35, 0, 0.25],
    )

    # Place both joints at their starting angles.
    for joint_id, start_angle in enumerate(Start_Angles):
        p.resetJointState(
            robot_id,
            joint_id,
            targetValue=start_angle,
            targetVelocity=0.0,
        )

    configure_robot_for_scenario(
        robot_id,
        scenario,
    )

    temperatures = [
        Ambient_Temprature,
        Ambient_Temprature,
    ]

    previous_velocities = [
        0.0,
        0.0,
    ]

    blocked_angle = None

    simulation_time = 0.0
    last_telemetry_time = -Telemetry_Interval
    last_print_time = -Print_Interval

    maximum_errors = [
        0.0,
        0.0,
    ]

    final_errors = [
        0.0,
        0.0,
    ]

    final_currents = [
        0.0,
        0.0,
    ]

    maximum_currents = [
        0.0,
        0.0,
    ]

    maximum_vibration = 0.0

    print_heading(scenario)

    try:
        while (
            simulation_time <= Total_Duration
            and p.isConnected()
        ):
            commanded_angles = calculate_commanded_angles(
                min(
                    simulation_time,
                    Movement_Duration,
                )
            )

            # Activate the blocked-joint fault at 40% of the
            # commanded movement.
            if (
                scenario == "blocked_joint"
                and blocked_angle is None
                and simulation_time
                >= Movement_Duration * 0.40
            ):
                blocked_angle = p.getJointState(
                    robot_id,
                    1,
                )[0]

                print()
                print(
                    "FAULT INJECTED: Joint 2 has been blocked."
                )

            fault_active = (
                scenario == "increased_friction"
                or (
                    scenario == "blocked_joint"
                    and blocked_angle is not None
                )
            )

            apply_joint_control(
                robot_id,
                commanded_angles,
                scenario,
                simulation_time,
                blocked_angle,
            )

            p.stepSimulation()

            if (
                simulation_time - last_telemetry_time
                >= Telemetry_Interval
            ):
                joint_states = [
                    p.getJointState(robot_id, 0),
                    p.getJointState(robot_id, 1),
                ]

                actual_angles = [
                    state[0]
                    for state in joint_states
                ]

                velocities = [
                    state[1]
                    for state in joint_states
                ]

                torques = [
                    state[3]
                    for state in joint_states
                ]

                errors = [
                    commanded - actual
                    for commanded, actual in zip(
                        commanded_angles,
                        actual_angles,
                    )
                ]

                currents = [
                    estimate_current(
                        torque=torques[joint_id],
                        scenario=scenario,
                        fault_active=fault_active,
                        joint_id=joint_id,
                    )
                    for joint_id in [0, 1]
                ]

                for joint_id in [0, 1]:
                    temperatures[joint_id] = (
                        update_temperature(
                            current_temperature=(
                                temperatures[joint_id]
                            ),
                            motor_current=currents[joint_id],
                            scenario=scenario,
                            fault_active=fault_active,
                            joint_id=joint_id,
                        )
                    )

                vibrations = [
                    estimate_vibration(
                        velocity=velocities[joint_id],
                        previous_velocity=(
                            previous_velocities[joint_id]
                        ),
                        scenario=scenario,
                        fault_active=fault_active,
                        joint_id=joint_id,
                    )
                    for joint_id in [0, 1]
                ]

                total_vibration = sum(vibrations) / 2.0

                maximum_vibration = max(
                    maximum_vibration,
                    total_vibration,
                )

                for joint_id in [0, 1]:
                    error_degrees = abs(
                        math.degrees(errors[joint_id])
                    )

                    maximum_errors[joint_id] = max(
                        maximum_errors[joint_id],
                        error_degrees,
                    )

                    final_errors[joint_id] = error_degrees
                    final_currents[joint_id] = currents[joint_id]

                    maximum_currents[joint_id] = max(
                        maximum_currents[joint_id],
                        currents[joint_id],
                    )

                if (
                    simulation_time - last_print_time
                    >= Print_Interval
                ):
                    print(
                        f"{simulation_time:6.2f} | "
                        f"{math.degrees(actual_angles[0]):9.2f} | "
                        f"{math.degrees(errors[0]):8.2f} | "
                        f"{currents[0]:10.2f} | "
                        f"{temperatures[0]:8.2f} | "
                        f"{math.degrees(actual_angles[1]):9.2f} | "
                        f"{math.degrees(errors[1]):8.2f} | "
                        f"{currents[1]:10.2f} | "
                        f"{temperatures[1]:8.2f} | "
                        f"{total_vibration:9.3f}"
                    )

                    last_print_time = simulation_time

                previous_velocities = velocities
                last_telemetry_time = simulation_time

            simulation_time += Time_Step
            time.sleep(Time_Step)

    except KeyboardInterrupt:
        print()
        print("Simulation stopped by user.")

    finally:
        if p.isConnected():
            p.disconnect()

    run_completed = all(
        error < 3.0
        for error in final_errors
    )

    if scenario == "blocked_joint":
        run_completed = False

    if scenario == "normal" and run_completed:
        operating_status = "NORMAL"

    elif scenario == "increased_friction" and run_completed:
        operating_status = "WARNING"

    else:
        operating_status = "FAILED"

    print()
    print("=" * 66)
    print("RUN SUMMARY")
    print("=" * 66)
    print(f"Scenario:                {scenario}")
    print(f"Operating status:        {operating_status}")
    print(f"Time taken:              {simulation_time:.2f} seconds")
    print(
        f"Joint 1 maximum error:   "
        f"{maximum_errors[0]:.2f} degrees"
    )
    print(
        f"Joint 2 maximum error:   "
        f"{maximum_errors[1]:.2f} degrees"
    )
    print(
        f"Joint 1 maximum current: "
        f"{maximum_currents[0]:.2f} A"
    )
    print(
        f"Joint 2 maximum current: "
        f"{maximum_currents[1]:.2f} A"
    )
    print(
        f"Joint 1 temperature:     "
        f"{temperatures[0]:.2f} °C"
    )
    print(
        f"Joint 2 temperature:     "
        f"{temperatures[1]:.2f} °C"
    )
    print(
        f"Maximum vibration:       "
        f"{maximum_vibration:.3f}"
    )
    print(
        "Outcome:                 "
        + ("SUCCESS" if run_completed else "FAILED")
    )
    print("=" * 66)


if __name__ == "__main__":
    main()