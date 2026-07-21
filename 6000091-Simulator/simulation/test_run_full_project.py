import argparse
import math
import os
import random
import sqlite3
import tempfile
import time
import unittest
from pathlib import Path

import pybullet as p
import pybullet_data


Simulation_Rate = 240
Time_Step = 1.0 / Simulation_Rate
Movement_Duration = 6.0
Settling_Duration = 1.0
Total_Duration = Movement_Duration + Settling_Duration
Telemetry_Rate = 20
Telemetry_Interval = 1.0 / Telemetry_Rate
Print_Rate = 4
Print_Interval = 1.0 / Print_Rate
Start_Angles = [0.0, 0.0]
Target_Angles = [math.radians(70), math.radians(-95)]
Motor_Torque = 0.45
Ambient_Temperature = 22.0
SCENARIOS = ["normal", "increased_friction", "blocked_joint"]


def smooth_trajectory(progress):
    progress = max(0.0, min(1.0, progress))
    return 0.5 - 0.5 * math.cos(math.pi * progress)


def calculate_commanded_angles(elapsed_time):
    progress = elapsed_time / Movement_Duration
    smoothed_progress = smooth_trajectory(progress)
    return [
        start + (target - start) * smoothed_progress
        for start, target in zip(Start_Angles, Target_Angles)
    ]


def estimate_current(torque, scenario, fault_active, joint_id):
    base_current = 0.18
    electrical_noise = random.gauss(0.0, 0.015)
    estimated_current = base_current + abs(torque) / Motor_Torque + electrical_noise

    if joint_id == 1 and fault_active and scenario == "increased_friction":
        estimated_current += 0.45

    if joint_id == 1 and fault_active and scenario == "blocked_joint":
        estimated_current += 2.20

    return max(0.0, estimated_current)


def update_temperature(current_temperature, motor_current, scenario, fault_active, joint_id):
    heating_rate = 0.045 * motor_current**2
    cooling_rate = 0.025 * (current_temperature - Ambient_Temperature)

    if joint_id == 1 and fault_active and scenario == "increased_friction":
        heating_rate *= 1.35

    if joint_id == 1 and fault_active and scenario == "blocked_joint":
        heating_rate *= 1.75

    temperature_change = (heating_rate - cooling_rate) * Telemetry_Interval
    sensor_noise = random.gauss(0.0, 0.015)
    return current_temperature + temperature_change + sensor_noise


def estimate_vibration(velocity, previous_velocity):
    acceleration = (velocity - previous_velocity) / Telemetry_Interval
    vibration = 0.02 + 0.004 * abs(velocity) + 0.0005 * abs(acceleration)
    vibration += random.gauss(0.0, 0.005)
    return max(0.0, vibration)


def configure_robot_for_scenario(robot_id, scenario):
    if scenario == "normal":
        for joint_id in [0, 1]:
            p.changeDynamics(robot_id, joint_id, jointDamping=0.15)
    elif scenario == "increased_friction":
        p.changeDynamics(robot_id, 0, jointDamping=0.15)
        p.changeDynamics(robot_id, 1, jointDamping=4.0)
    elif scenario == "blocked_joint":
        for joint_id in [0, 1]:
            p.changeDynamics(robot_id, joint_id, jointDamping=0.15)


def apply_joint_control(robot_id, commanded_angles, scenario, elapsed_time, blocked_angle):
    forces = [45.0, 35.0]
    position_gains = [0.30, 0.30]

    if scenario == "increased_friction":
        forces[1] = 2.0
        position_gains[1] = 0.06

    for joint_id in [0, 1]:
        target_angle = commanded_angles[joint_id]
        if scenario == "blocked_joint" and joint_id == 1 and elapsed_time >= Movement_Duration * 0.40 and blocked_angle is not None:
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


def initialize_database(db_path):
    connection = sqlite3.connect(db_path)
    cursor = connection.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS experiment_runs (
            run_id INTEGER PRIMARY KEY AUTOINCREMENT,
            scenario TEXT NOT NULL,
            run_number INTEGER NOT NULL,
            total_duration REAL NOT NULL,
            status TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS experiment_telemetry (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id INTEGER NOT NULL,
            sample_time REAL NOT NULL,
            joint_1_angle REAL NOT NULL,
            joint_1_error REAL NOT NULL,
            joint_1_current REAL NOT NULL,
            joint_1_temperature REAL NOT NULL,
            joint_2_angle REAL NOT NULL,
            joint_2_error REAL NOT NULL,
            joint_2_current REAL NOT NULL,
            joint_2_temperature REAL NOT NULL,
            vibration REAL NOT NULL,
            FOREIGN KEY(run_id) REFERENCES experiment_runs(run_id)
        )
        """
    )
    connection.commit()
    connection.close()
    return db_path


def insert_run_summary(db_path, scenario, run_number, total_duration, status):
    connection = sqlite3.connect(db_path)
    cursor = connection.cursor()
    cursor.execute(
        """
        INSERT INTO experiment_runs (scenario, run_number, total_duration, status, created_at)
        VALUES (?, ?, ?, ?, datetime('now'))
        """,
        (scenario, run_number, total_duration, status),
    )
    run_id = cursor.lastrowid
    connection.commit()
    connection.close()
    return run_id


def insert_run_telemetry(db_path, run_id, telemetry_rows):
    if not telemetry_rows:
        return 0

    connection = sqlite3.connect(db_path)
    cursor = connection.cursor()
    cursor.executemany(
        """
        INSERT INTO experiment_telemetry (
            run_id, sample_time, joint_1_angle, joint_1_error, joint_1_current,
            joint_1_temperature, joint_2_angle, joint_2_error, joint_2_current,
            joint_2_temperature, vibration
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                run_id,
                row["sample_time"],
                row["joint_1_angle"],
                row["joint_1_error"],
                row["joint_1_current"],
                row["joint_1_temperature"],
                row["joint_2_angle"],
                row["joint_2_error"],
                row["joint_2_current"],
                row["joint_2_temperature"],
                row["vibration"],
            )
            for row in telemetry_rows
        ],
    )
    connection.commit()
    connection.close()
    return len(telemetry_rows)


def collect_single_run(robot_id, scenario, run_number, db_path):
    random.seed(600091 + run_number)
    temperatures = [Ambient_Temperature, Ambient_Temperature]
    previous_velocities = [0.0, 0.0]
    blocked_angle = None
    simulation_time = 0.0
    last_telemetry_time = -Telemetry_Interval

    telemetry_rows = []
    maximum_errors = [0.0, 0.0]
    final_errors = [0.0, 0.0]

    while simulation_time <= Total_Duration and p.isConnected():
        commanded_angles = calculate_commanded_angles(min(simulation_time, Movement_Duration))

        if scenario == "blocked_joint" and blocked_angle is None and simulation_time >= Movement_Duration * 0.40:
            blocked_angle = p.getJointState(robot_id, 1)[0]

        fault_active = scenario == "increased_friction" or (scenario == "blocked_joint" and blocked_angle is not None)

        apply_joint_control(robot_id, commanded_angles, scenario, simulation_time, blocked_angle)
        p.stepSimulation()

        if simulation_time - last_telemetry_time >= Telemetry_Interval:
            joint_states = [p.getJointState(robot_id, 0), p.getJointState(robot_id, 1)]
            actual_angles = [state[0] for state in joint_states]
            velocities = [state[1] for state in joint_states]
            torques = [state[3] for state in joint_states]
            errors = [commanded - actual for commanded, actual in zip(commanded_angles, actual_angles)]
            currents = [
                estimate_current(torque=torques[joint_id], scenario=scenario, fault_active=fault_active, joint_id=joint_id)
                for joint_id in [0, 1]
            ]

            for joint_id in [0, 1]:
                temperatures[joint_id] = update_temperature(
                    current_temperature=temperatures[joint_id],
                    motor_current=currents[joint_id],
                    scenario=scenario,
                    fault_active=fault_active,
                    joint_id=joint_id,
                )

            vibrations = [estimate_vibration(velocity=velocities[joint_id], previous_velocity=previous_velocities[joint_id]) for joint_id in [0, 1]]
            total_vibration = sum(vibrations) / 2.0

            for joint_id in [0, 1]:
                error_degrees = abs(math.degrees(errors[joint_id]))
                maximum_errors[joint_id] = max(maximum_errors[joint_id], error_degrees)
                final_errors[joint_id] = error_degrees

            telemetry_rows.append(
                {
                    "sample_time": simulation_time,
                    "joint_1_angle": math.degrees(actual_angles[0]),
                    "joint_1_error": math.degrees(errors[0]),
                    "joint_1_current": currents[0],
                    "joint_1_temperature": temperatures[0],
                    "joint_2_angle": math.degrees(actual_angles[1]),
                    "joint_2_error": math.degrees(errors[1]),
                    "joint_2_current": currents[1],
                    "joint_2_temperature": temperatures[1],
                    "vibration": total_vibration,
                }
            )
            previous_velocities = velocities
            last_telemetry_time = simulation_time

        simulation_time += Time_Step
        time.sleep(Time_Step)

    status = "SUCCESS" if all(error < 3.0 for error in final_errors) else "FAILED"
    run_id = insert_run_summary(db_path, scenario, run_number, simulation_time, status)
    insert_run_telemetry(db_path, run_id, telemetry_rows)
    return run_id, status


def parse_arguments():
    parser = argparse.ArgumentParser(description="Collect repeated robotic-arm telemetry into SQLite")
    parser.add_argument("--scenario", choices=SCENARIOS, default="normal", help="Scenario to run")
    parser.add_argument("--runs", type=int, default=5, help="How many repeated runs to collect")
    parser.add_argument("--db-path", default=str(Path(__file__).resolve().parent / "robot_data_collection.db"), help="Location of the SQLite database file")
    parser.add_argument("--headless", action="store_true", help="Run the physics engine in headless mode")
    return parser.parse_args()


def create_simulation_environment(scenario, headless=False):
    physics_client = p.connect(p.DIRECT if headless else p.GUI)
    if physics_client < 0:
        raise RuntimeError("PyBullet could not open the simulation.")

    p.configureDebugVisualizer(p.COV_ENABLE_GUI, 0)
    p.configureDebugVisualizer(p.COV_ENABLE_SHADOWS, 1)
    p.setAdditionalSearchPath(pybullet_data.getDataPath())
    p.setGravity(0, 0, -9.81)
    p.setTimeStep(Time_Step)
    p.loadURDF("plane.urdf")

    simulation_directory = Path(__file__).resolve().parent
    project_directory = simulation_directory.parent
    robot_model = project_directory / "models" / "two_joint_arm.urdf"
    if not robot_model.exists():
        raise FileNotFoundError(f"Robot model was not found: {robot_model}")

    robot_id = p.loadURDF(str(robot_model), basePosition=[0, 0, 0], useFixedBase=True)
    for joint_id, start_angle in enumerate(Start_Angles):
        p.resetJointState(robot_id, joint_id, targetValue=start_angle, targetVelocity=0.0)

    configure_robot_for_scenario(robot_id, scenario)
    return robot_id


def run_experiment(scenario="normal", runs=5, db_path=None, headless=False):
    db_path = db_path or str(Path(__file__).resolve().parent / "robot_data_collection.db")
    db_path = initialize_database(db_path)
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    for run_number in range(1, runs + 1):
        robot_id = create_simulation_environment(scenario, headless=headless)
        try:
            collect_single_run(robot_id, scenario, run_number, db_path)
        finally:
            if p.isConnected():
                p.disconnect()

    return db_path


def main():
    args = parse_arguments()
    db_path = run_experiment(
        scenario=args.scenario,
        runs=args.runs,
        db_path=args.db_path,
        headless=args.headless,
    )
    print(f"SQLite data collection complete. Database: {db_path}")


class TestDataCollectionWorkflow(unittest.TestCase):
    def test_initialize_database_creates_schema(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, "test_data.db")
            initialize_database(db_path)
            connection = sqlite3.connect(db_path)
            cursor = connection.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='experiment_runs'")
            self.assertTrue(cursor.fetchone())
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='experiment_telemetry'")
            self.assertTrue(cursor.fetchone())
            connection.close()

    def test_insert_run_summary_and_telemetry(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, "test_data.db")
            initialize_database(db_path)
            run_id = insert_run_summary(db_path, "normal", 1, 6.0, "SUCCESS")
            inserted_rows = insert_run_telemetry(
                db_path,
                run_id,
                [
                    {
                        "sample_time": 0.1,
                        "joint_1_angle": 10.0,
                        "joint_1_error": 1.0,
                        "joint_1_current": 0.2,
                        "joint_1_temperature": 22.1,
                        "joint_2_angle": 20.0,
                        "joint_2_error": 2.0,
                        "joint_2_current": 0.3,
                        "joint_2_temperature": 22.2,
                        "vibration": 0.05,
                    }
                ],
            )
            self.assertEqual(inserted_rows, 1)
            connection = sqlite3.connect(db_path)
            cursor = connection.cursor()
            cursor.execute("SELECT COUNT(*) FROM experiment_runs")
            self.assertEqual(cursor.fetchone()[0], 1)
            cursor.execute("SELECT COUNT(*) FROM experiment_telemetry")
            self.assertEqual(cursor.fetchone()[0], 1)
            connection.close()


if __name__ == "__main__":
    main()
