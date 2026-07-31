import math

from sim_env.car_model import CarParams, CarState, step


def _still_car():
    return CarState(x=0.0, y=0.0, yaw=0.0, speed=0.0)


def test_full_throttle_accelerates_forward():
    params = CarParams()
    state = step(_still_car(), steering=0.0, throttle=1.0, brake=0.0, dt=0.1, params=params)
    assert state.speed > 0
    assert state.x > 0
    assert abs(state.y) < 1e-9


def test_brake_does_not_reverse_from_standstill():
    params = CarParams()
    state = step(_still_car(), steering=0.0, throttle=0.0, brake=1.0, dt=0.1, params=params)
    assert state.speed == 0.0


def test_speed_never_exceeds_max_speed():
    params = CarParams(max_speed=20.0, drag_coefficient=0.0)
    state = _still_car()
    for _ in range(1000):
        state = step(state, steering=0.0, throttle=1.0, brake=0.0, dt=0.1, params=params)
    assert state.speed <= params.max_speed


def test_positive_steering_turns_left():
    params = CarParams()
    moving = CarState(x=0.0, y=0.0, yaw=0.0, speed=10.0)
    state = step(moving, steering=1.0, throttle=0.0, brake=0.0, dt=0.1, params=params)
    assert state.yaw > 0


def test_negative_steering_turns_right():
    params = CarParams()
    moving = CarState(x=0.0, y=0.0, yaw=0.0, speed=10.0)
    state = step(moving, steering=-1.0, throttle=0.0, brake=0.0, dt=0.1, params=params)
    assert state.yaw < 0


def test_zero_steering_keeps_heading():
    params = CarParams()
    moving = CarState(x=0.0, y=0.0, yaw=math.pi / 4, speed=10.0)
    state = step(moving, steering=0.0, throttle=0.0, brake=0.0, dt=0.1, params=params)
    assert abs(state.yaw - math.pi / 4) < 1e-9
