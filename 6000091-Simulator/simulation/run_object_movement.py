import math
import time
from pathlib import Path

import pybullet as p
import pybullet_data


Simulation_Rate = 240
Time_Step = 1.0 / Simulation_Rate

Controlled_Joints = [0, 1, 2]
End_Effector_Link = 3

Home_Angles = [
    math.radians(0),
    math.radians(0),
    math.radians(0),
]

Pick_Angles = [
    math.radians(25),
    math.radians(-55),
    math.radians(35),
]

Place_Angles = [
    math.radians(100),
    math.radians(-45),
    math.radians(-20),
]

Retreat_Angles = [
    math.radians(70),
    math.radians(-20),
    math.radians(10),
]

Move_To_Pick = 3.0
Pick_Pause_Duration = 1.0
Move_To_Place = 4.0
Place_Pause_Duration = 1.0
Retreat_Duration = 2.0

Pick_End_Time = Move_To_Pick

Place_Start_Time = (
    Pick_End_Time
    + Pick_Pause_Duration
)

Place_End_Time = (
    Place_Start_Time
    + Move_To_Place
)

Retreat_Start_Time = (
    Place_End_Time
    + Place_Pause_Duration
)

Total_Duration = (
    Retreat_Start_Time
    + Retreat_Duration
)


def smooth_progress(progress):
    """Create smooth acceleration and deceleration."""
    progress = max(0.0, min(1.0, progress))

    return 0.5 - 0.5 * math.cos(
        math.pi * progress
    )


def interpolate_angles(
    starting_angles,
    target_angles,
    progress,
):
    """Interpolate between two joint configurations."""
    progress = smooth_progress(progress)

    return [
        start + (target - start) * progress
        for start, target in zip(
            starting_angles,
            target_angles,
        )
    ]


def calculate_commanded_angles(elapsed_time):
    """
    Select the correct movement phase and calculate the
    commanded joint angles.
    """

    # Phase 1: move from home to the object.
    if elapsed_time < Pick_End_Time:
        progress = (
            elapsed_time
            / Move_To_Pick
        )

        return interpolate_angles(
            Home_Angles,
            Pick_Angles,
            progress,
        )

    # Phase 2: pause while gripping the object.
    if elapsed_time < Place_Start_Time:
        return Pick_Angles

    # Phase 3: carry the object to the placement position.
    if elapsed_time < Place_End_Time:
        progress = (
            elapsed_time - Place_Start_Time
        ) / Move_To_Place

        return interpolate_angles(
            Pick_Angles,
            Place_Angles,
            progress,
        )

    # Phase 4: pause while releasing the object.
    if elapsed_time < Retreat_Start_Time:
        return Place_Angles

    # Phase 5: move away from the released object.
    progress = (
        elapsed_time - Retreat_Start_Time
    ) / Retreat_Duration

    return interpolate_angles(
        Place_Angles,
        Retreat_Angles,
        progress,
    )


def set_joint_positions(
    robot_id,
    target_angles,
):
    """Send position commands to all three joints."""
    forces = [
        70.0,
        55.0,
        40.0,
    ]

    for list_index, joint_id in enumerate(
        Controlled_Joints
    ):
        p.setJointMotorControl2(
            bodyUniqueId=robot_id,
            jointIndex=joint_id,
            controlMode=p.POSITION_CONTROL,
            targetPosition=target_angles[list_index],
            force=forces[list_index],
            positionGain=0.25,
            velocityGain=0.80,
        )


def reset_robot_position(
    robot_id,
    target_angles,
):
    """Immediately place the arm into a configuration."""
    for list_index, joint_id in enumerate(
        Controlled_Joints
    ):
        p.resetJointState(
            robot_id,
            joint_id,
            targetValue=target_angles[list_index],
            targetVelocity=0.0,
        )


def calculate_object_position(robot_id):
    """
    Calculate where the object should be placed so that it is
    directly in front of the end effector at the pick position.
    """
    reset_robot_position(
        robot_id,
        Pick_Angles,
    )

    p.stepSimulation()

    end_effector_state = p.getLinkState(
        robot_id,
        End_Effector_Link,
        computeForwardKinematics=True,
    )

    end_effector_position = end_effector_state[4]
    end_effector_orientation = end_effector_state[5]

    object_position, object_orientation = (
        p.multiplyTransforms(
            end_effector_position,
            end_effector_orientation,
            [0.12, 0, 0],
            [0, 0, 0, 1],
        )
    )

    reset_robot_position(
        robot_id,
        Home_Angles,
    )

    return object_position, object_orientation


def create_table():
    """Create a simple table underneath the arm and object."""
    table_collision = p.createCollisionShape(
        p.GEOM_BOX,
        halfExtents=[1.2, 1.2, 0.05],
    )

    table_visual = p.createVisualShape(
        p.GEOM_BOX,
        halfExtents=[1.2, 1.2, 0.05],
        rgbaColor=[0.45, 0.32, 0.20, 1],
    )

    return p.createMultiBody(
        baseMass=0,
        baseCollisionShapeIndex=table_collision,
        baseVisualShapeIndex=table_visual,
        basePosition=[0, 0, 0.26],
    )


def create_object(
    object_position,
    object_orientation,
):
    """Create the cube that the robot will move."""
    cube_size = 0.10

    collision_shape = p.createCollisionShape(
        p.GEOM_BOX,
        halfExtents=[
            cube_size / 2,
            cube_size / 2,
            cube_size / 2,
        ],
    )

    visual_shape = p.createVisualShape(
        p.GEOM_BOX,
        halfExtents=[
            cube_size / 2,
            cube_size / 2,
            cube_size / 2,
        ],
        rgbaColor=[0.85, 0.12, 0.15, 1],
    )

    return p.createMultiBody(
        baseMass=0.25,
        baseCollisionShapeIndex=collision_shape,
        baseVisualShapeIndex=visual_shape,
        basePosition=object_position,
        baseOrientation=object_orientation,
    )


def attach_object(
    robot_id,
    object_id,
):
    """
    Attach the object to the end effector.

    This fixed constraint represents a successful grip.
    """
    return p.createConstraint(
        parentBodyUniqueId=robot_id,
        parentLinkIndex=End_Effector_Link,
        childBodyUniqueId=object_id,
        childLinkIndex=-1,
        jointType=p.JOINT_FIXED,
        jointAxis=[0, 0, 0],
        parentFramePosition=[0.12, 0, 0],
        childFramePosition=[0, 0, 0],
    )


def print_joint_telemetry(
    robot_id,
    elapsed_time,
    phase,
):
    """Display the current angles and errors."""
    actual_angles = []
    commanded_angles = calculate_commanded_angles(
        elapsed_time
    )

    for joint_id in Controlled_Joints:
        joint_state = p.getJointState(
            robot_id,
            joint_id,
        )

        actual_angles.append(joint_state[0])

    errors = [
        commanded - actual
        for commanded, actual in zip(
            commanded_angles,
            actual_angles,
        )
    ]

    print(
        f"{elapsed_time:6.2f}s | "
        f"{phase:<16} | "
        f"J1 {math.degrees(actual_angles[0]):7.2f}° "
        f"({math.degrees(errors[0]):6.2f}° error) | "
        f"J2 {math.degrees(actual_angles[1]):7.2f}° "
        f"({math.degrees(errors[1]):6.2f}° error) | "
        f"J3 {math.degrees(actual_angles[2]):7.2f}° "
        f"({math.degrees(errors[2]):6.2f}° error)"
    )


def get_phase(elapsed_time):
    if elapsed_time < Pick_End_Time:
        return "MOVING TO PICK"

    if elapsed_time < Place_Start_Time:
        return "GRIPPING"

    if elapsed_time < Place_End_Time:
        return "MOVING OBJECT"

    if elapsed_time < Retreat_Start_Time:
        return "RELEASING"

    return "RETREATING"


def main():
    simulation_directory = Path(__file__).resolve().parent
    project_directory = simulation_directory.parent

    robot_model = (
        project_directory
        / "models"
        / "three_joint_arm.urdf"
    )

    if not robot_model.exists():
        raise FileNotFoundError(
            f"Robot model was not found: {robot_model}"
        )

    physics_client = p.connect(p.GUI)

    if physics_client < 0:
        raise RuntimeError(
            "PyBullet could not open the simulation."
        )

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

    p.loadURDF("plane.urdf")

    create_table()

    robot_id = p.loadURDF(
        str(robot_model),
        basePosition=[0, 0, 0],
        useFixedBase=True,
    )

    reset_robot_position(
        robot_id,
        Home_Angles,
    )

    object_position, object_orientation = (
        calculate_object_position(robot_id)
    )

    object_id = create_object(
        object_position,
        object_orientation,
    )

    p.changeDynamics(
        object_id,
        -1,
        lateralFriction=0.8,
    )

    p.resetDebugVisualizerCamera(
        cameraDistance=2.5,
        cameraYaw=40,
        cameraPitch=-55,
        cameraTargetPosition=[0.25, 0.20, 0.25],
    )

    grip_constraint = None
    object_attached = False
    object_released = False

    simulation_time = 0.0
    last_print_time = -0.25

    print()
    print("=" * 92)
    print("AEGIS THREE-JOINT OBJECT-MOVEMENT SIMULATION")
    print("=" * 92)
    print("The arm will approach, grip, move and release the red cube.")
    print()

    try:
        while (
            simulation_time <= Total_Duration
            and p.isConnected()
        ):
            target_angles = calculate_commanded_angles(
                simulation_time
            )

            set_joint_positions(
                robot_id,
                target_angles,
            )

            # Attach the object when the arm reaches the
            # gripping phase.
            if (
                simulation_time >= Pick_End_Time
                and not object_attached
            ):
                grip_constraint = attach_object(
                    robot_id,
                    object_id,
                )

                object_attached = True

                print()
                print(
                    "OBJECT GRIPPED: The cube is attached "
                    "to the end effector."
                )

            # Release the object after reaching the destination.
            if (
                simulation_time >= Place_End_Time
                and object_attached
                and not object_released
            ):
                p.removeConstraint(
                    grip_constraint
                )

                object_released = True

                print()
                print(
                    "OBJECT RELEASED: The cube has been "
                    "placed at its destination."
                )

            p.stepSimulation()

            if (
                simulation_time - last_print_time
                >= 0.25
            ):
                phase = get_phase(
                    simulation_time
                )

                print_joint_telemetry(
                    robot_id,
                    simulation_time,
                    phase,
                )

                last_print_time = simulation_time

            simulation_time += Time_Step
            time.sleep(Time_Step)

    except KeyboardInterrupt:
        print()
        print("Simulation stopped by user.")

    finally:
        if p.isConnected():
            p.disconnect()

    print()
    print("=" * 56)
    print("OBJECT-MOVEMENT RUN COMPLETE")
    print("=" * 56)
    print(f"Time taken: {simulation_time:.2f} seconds")
    print("Outcome: SUCCESS")
    print("=" * 56)


if __name__ == "__main__":
    main()