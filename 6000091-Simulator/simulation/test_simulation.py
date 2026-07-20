import time

import pybullet as p
import pybullet_data


def main():
    """Start the first visual robotic-arm simulation."""

    # Open PyBullet's visual simulation window.
    physics_client = p.connect(p.GUI)

    # Hide PyBullet's large diagnostic side panels.
    p.configureDebugVisualizer(p.COV_ENABLE_GUI, 0)

# Improve the visual appearance.
    p.configureDebugVisualizer(p.COV_ENABLE_SHADOWS, 1)


    if physics_client < 0:
        raise RuntimeError(
            "PyBullet could not open the simulation window."
        )

    # Allow access to PyBullet's included models.
    p.setAdditionalSearchPath(pybullet_data.getDataPath())

    # Configure the simulated environment.
    p.setGravity(0, 0, -9.81)
    p.setTimeStep(1.0 / 240.0)

    # Load the floor.
    p.loadURDF("plane.urdf")

    # Load a seven-joint KUKA iiwa robotic arm.
    robot_id = p.loadURDF(
        "kuka_iiwa/model.urdf",
        basePosition=[0, 0, 0],
        baseOrientation=p.getQuaternionFromEuler([0, 0, 0]),
        useFixedBase=True,
    )

    # Position the camera close to the robotic arm.
    p.resetDebugVisualizerCamera(
    cameraDistance=1.8,
    cameraYaw=45,
    cameraPitch=-30,
    cameraTargetPosition=[0, 0, 0.6],
    )

    number_of_joints = p.getNumJoints(robot_id)

    print("PyBullet simulation started successfully.")
    print(f"Robot ID: {robot_id}")
    print(f"Number of joints: {number_of_joints}")
    print("Close the simulation window or press Ctrl+C to stop.")

    try:
        while p.isConnected():
            p.stepSimulation()
            time.sleep(1.0 / 240.0)

    except KeyboardInterrupt:
        print("\nSimulation stopped by user.")

    finally:
        if p.isConnected():
            p.disconnect()

        print("PyBullet disconnected.")


if __name__ == "__main__":
    main()