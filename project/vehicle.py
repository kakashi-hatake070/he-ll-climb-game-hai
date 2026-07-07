"""Vehicle, wheel, and drivetrain logic."""

from __future__ import annotations

from dataclasses import dataclass, field
from math import atan2, cos, pi, sin
from typing import Dict, List

import pygame

from physics import apply_force, body_point, body_velocity_at_point, clamp_angle, lerp_vector
from settings import (
    BASE_BRAKE_FORCE,
    BASE_ENGINE_POWER,
    BASE_FUEL_EFFICIENCY,
    BASE_GRIP,
    BASE_SUSPENSION,
    BASE_VEHICLE_MASS,
    BASE_WEIGHT,
    BOOST_FORCE,
    BOOST_FUEL_COST,
    GRAVITY,
    MAX_UPRIGHT_ANGLE,
    WHEEL_CONTACT_BAND,
    clamp,
)


@dataclass
class Wheel:
    """One suspension wheel with its own contact and spin state."""

    off_x: float
    off_y: float
    radius: float = 20.0
    x: float = 0.0
    y: float = 0.0
    vx: float = 0.0
    vy: float = 0.0
    spin: float = 0.0
    rotation: float = 0.0
    grounded: bool = False
    compression: float = 0.0
    air_time: float = 0.0


@dataclass
class Vehicle:
    """Physics approximation for the player's car."""

    save_data: Dict[str, int | float | bool]
    x: float = 160.0
    y: float = 0.0
    vx: float = 0.0
    vy: float = 0.0
    angle: float = 0.0
    angular_velocity: float = 0.0
    mass: float = BASE_VEHICLE_MASS
    width: float = 126.0
    height: float = 38.0
    fuel: float = 100.0
    engine_power: float = BASE_ENGINE_POWER
    brake_force: float = BASE_BRAKE_FORCE
    grip: float = BASE_GRIP
    suspension_strength: float = BASE_SUSPENSION
    fuel_efficiency: float = BASE_FUEL_EFFICIENCY
    weight_factor: float = BASE_WEIGHT
    boost_level: int = 0
    torque_buffer: float = 0.0
    flip_timer: int = 0
    stunt_bonus: int = 0
    boost_cooldown: float = 0.0
    wheels: List[Wheel] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.wheels:
            self.wheels = [Wheel(-38.0, 18.0), Wheel(38.0, 18.0)]

    def reset(self, spawn_y: float) -> None:
        """Reset all kinematic state and place the car on the starting hill."""

        self.x = 160.0
        self.y = spawn_y
        self.vx = 0.0
        self.vy = 0.0
        self.angle = 0.0
        self.angular_velocity = 0.0
        self.fuel = 100.0
        self.torque_buffer = 0.0
        self.flip_timer = 0
        self.stunt_bonus = 0
        self.boost_cooldown = 0.0
        for wheel in self.wheels:
            wheel.x = self.x + wheel.off_x
            wheel.y = spawn_y + 18.0
            wheel.vx = 0.0
            wheel.vy = 0.0
            wheel.spin = 0.0
            wheel.rotation = 0.0
            wheel.grounded = False
            wheel.compression = 0.0
            wheel.air_time = 0.0

    def apply_upgrades(self, upgrades) -> None:
        """Pull the latest upgrade stats into the vehicle tuning values."""

        self.engine_power = BASE_ENGINE_POWER * upgrades.engine_multiplier
        self.brake_force = BASE_BRAKE_FORCE * upgrades.brake_multiplier
        self.grip = BASE_GRIP * upgrades.grip_multiplier
        self.suspension_strength = BASE_SUSPENSION * upgrades.suspension_multiplier
        self.fuel_efficiency = BASE_FUEL_EFFICIENCY * upgrades.fuel_efficiency_multiplier
        self.weight_factor = BASE_WEIGHT * upgrades.weight_multiplier
        self.boost_level = upgrades.boost_level

    def update(self, dt: float, terrain, sound_manager, is_crashing: bool = False) -> None:
        """Advance the vehicle simulation one frame."""

        keys = pygame.key.get_pressed()
        if is_crashing:
            throttle = 0
            tilt = 0
            boost = False
        else:
            drive_right = keys[pygame.K_RIGHT] or keys[pygame.K_d] or keys[pygame.K_w]
            drive_left = keys[pygame.K_LEFT] or keys[pygame.K_a] or keys[pygame.K_s]
            throttle = int(drive_right) - int(drive_left)
            tilt = throttle
            boost = keys[pygame.K_SPACE]

        self.consume_fuel(dt, throttle, boost)
        self.update_wheels(dt, terrain, throttle, boost)
        self.integrate_body(dt, terrain, tilt)
        self.update_stunts(dt)
        self.boost_cooldown = max(0.0, self.boost_cooldown - dt)

        if boost and self.fuel > 0.0 and self.boost_cooldown <= 0.0:
            self.vx += BOOST_FORCE * dt
            self.vy -= BOOST_FORCE * 0.18 * dt
            self.fuel = max(0.0, self.fuel - BOOST_FUEL_COST * dt)
            self.boost_cooldown = 0.18
            sound_manager.play_boost()

    def consume_fuel(self, dt: float, throttle: int, boost: bool) -> None:
        """Drain fuel using throttle, distance, and boost usage."""

        speed_cost = abs(self.vx) * 0.00009 + abs(self.vy) * 0.00005
        climb_cost = max(0.0, self.angle) * 0.015
        input_cost = abs(throttle) * 0.13
        boost_cost = 0.25 if boost else 0.0
        self.fuel -= dt * (0.72 + speed_cost + climb_cost + input_cost + boost_cost) / max(0.2, self.fuel_efficiency)
        self.fuel = clamp(self.fuel, 0.0, 100.0)

    def update_wheels(self, dt: float, terrain, throttle: int, boost: bool) -> None:
        """Update wheel contact, spin, and suspension compression."""

        for wheel in self.wheels:
            anchor = body_point(self.x, self.y, self.angle, wheel.off_x, wheel.off_y)

            # Lock wheel X to chassis anchor so it can't drift horizontally
            wheel.x = anchor[0]

            # Apply gravity to wheel vertically
            wheel.vy += GRAVITY * dt

            # Find ground beneath this wheel
            ground_y = terrain.height_at(wheel.x)
            target_y = ground_y - wheel.radius

            # Grounded if wheel is at or below ground surface
            wheel.grounded = wheel.y >= target_y - WHEEL_CONTACT_BAND

            if wheel.grounded:
                # Snap wheel firmly to ground — no bounce, no drift
                wheel.y = target_y
                wheel.vy = 0.0
                wheel.compression = clamp((wheel.y - anchor[1]) / 26.0, 0.0, 1.0)

                traction = terrain.slope_factor(wheel.x) * self.grip
                engine_force = throttle * self.engine_power * traction * dt
                self.vx += engine_force / max(0.45, self.weight_factor)
                self.angular_velocity += throttle * 0.14 * traction * dt
                wheel.spin = lerp_vector(wheel.spin, self.vx / wheel.radius, 0.30)
                wheel.air_time = 0.0
            else:
                # Airborne: let gravity pull wheel down naturally
                wheel.y += wheel.vy * dt
                wheel.compression = lerp_vector(wheel.compression, 0.0, 0.25)
                wheel.air_time += dt
                wheel.spin *= 0.992
                self.angular_velocity += tilt_boost(throttle, dt)

                # Clamp wheel so it doesn't stretch too far from anchor
                max_drop = anchor[1] + 26.0
                if wheel.y > max_drop:
                    wheel.y = max_drop
                    wheel.vy = 0.0

            wheel.rotation += wheel.spin * dt

        # Ground friction / air drag on horizontal speed
        if self.on_ground():
            self.vx *= 1.0 - self.brake_force * 0.35 * dt
            self.angular_velocity *= 0.96
        else:
            self.vx *= 0.999
            self.angular_velocity *= 0.997

        self.vx = clamp(self.vx, -340.0, 1100.0)

    def integrate_body(self, dt: float, terrain, tilt: int) -> None:
        """Integrate the chassis position and apply stabilizing forces."""

        self.x += self.vx * dt
        self.angle += self.angular_velocity * dt

        front, rear = self.wheels[1], self.wheels[0]
        wheel_center_y = (front.y + rear.y) * 0.5

        if self.on_ground():
            # Grounded: body Y is DIRECTLY pinned to the wheel midpoint
            # No vy accumulation — this is what keeps the car on the ground
            self.y = lerp_vector(self.y, wheel_center_y - 44.0, 0.75)
            self.vy = 0.0
        else:
            # Truly airborne: apply gravity to body and integrate freely
            self.vy += GRAVITY * dt
            self.y += self.vy * dt

            # Once wheels touch ground, body snaps back down
            if self.y > wheel_center_y - 44.0:
                self.y = wheel_center_y - 44.0
                self.vy = 0.0

        # Slope alignment torque (spring model)
        if self.on_ground():
            slope_front = terrain.slope_at(self.x + 28.0)
            slope_back  = terrain.slope_at(self.x - 28.0)
            desired_angle = clamp_angle(atan2(slope_front + slope_back, 2.0))
            angle_error = desired_angle - self.angle
            while angle_error >  pi: angle_error -= 2 * pi
            while angle_error < -pi: angle_error += 2 * pi
            self.angular_velocity += angle_error * 5.5 * dt

        self.angular_velocity += tilt * 1.8 * dt
        self.angular_velocity *= 0.945
        self.angle = clamp_angle(self.angle)


    def update_stunts(self, dt: float) -> None:
        """Track rotation and award stunt style bonuses."""

        if abs(self.angle) > 3.0:
            self.stunt_bonus += 1
        if abs(self.angle) > MAX_UPRIGHT_ANGLE:
            self.flip_timer += 1

    def on_ground(self) -> bool:
        """Return True if any wheel is grounded."""

        return any(wheel.grounded for wheel in self.wheels)

    def head_point(self) -> tuple[float, float]:
        """Return the driver head position for crash detection."""

        return body_point(self.x, self.y, self.angle, 8.0, -self.height / 2 - 20.0)

    def head_hit_ground(self, terrain) -> bool:
        """Detect a hard head collision with the terrain."""

        head_x, head_y = self.head_point()
        return head_y + 8.0 >= terrain.height_at(head_x)

    def render(self, screen: pygame.Surface, camera) -> None:
        """Draw the vehicle body and wheels using the current transform."""

        body_x = camera.world_to_screen_x(self.x)
        body_y = camera.world_to_screen_y(self.y)
        body_w = self.width
        body_h = self.height

        # Create drawing canvas for vehicle body and driver
        surface = pygame.Surface((260, 180), pygame.SRCALPHA)
        cx, cy = 130, 90

        # Draw a subtle drop shadow
        pygame.draw.ellipse(surface, (0, 0, 0, 55), (cx - 72, cy - 8, 144, 56))

        # --- JEEP BODY (Red Open-Top Jeep) ---
        # Draw the classic Hill Climb Racing Jeep shape using a polygon
        jeep_points = [
            (cx - 55, cy + 18),   # Rear bottom
            (cx + 55, cy + 18),   # Front bottom
            (cx + 55, cy - 2),    # Front bumper/fender
            (cx + 38, cy - 5),    # Front hood starts
            (cx + 12, cy - 8),    # Windshield base
            (cx - 22, cy - 8),    # Cabin seat floor
            (cx - 32, cy - 18),   # Seat backrest top
            (cx - 55, cy - 12),   # Rear trunk top
        ]
        # Main red body fill
        pygame.draw.polygon(surface, (200, 16, 46), jeep_points)
        # Black structural outlines
        pygame.draw.polygon(surface, (15, 23, 42), jeep_points, 3)

        # Draw a dark gray interior / floor board inside the cabin
        pygame.draw.polygon(surface, (50, 55, 60), [
            (cx + 10, cy - 6),
            (cx - 20, cy - 6),
            (cx - 28, cy - 14),
            (cx - 10, cy - 14)
        ])

        # Draw black roll cage bar at the back (behind the seat)
        pygame.draw.line(surface, (15, 23, 42), (cx - 30, cy - 16), (cx - 50, cy + 12), 4)

        # Draw black windshield strut/bar
        pygame.draw.line(surface, (15, 23, 42), (cx + 12, cy - 8), (cx + 8, cy - 28), 4)

        # Draw a curved rear antenna (pointing backward)
        antenna_pts = [
            (cx - 48, cy - 10),
            (cx - 52, cy - 22),
            (cx - 58, cy - 34),
            (cx - 66, cy - 44)
        ]
        pygame.draw.lines(surface, (15, 23, 42), False, antenna_pts, 3)

        # --- DRIVER BILL ---
        # Bill sits inside the open cabin
        # Torso: Red shirt
        pygame.draw.ellipse(surface, (200, 16, 46), (cx - 18, cy - 16, 24, 18))
        pygame.draw.ellipse(surface, (15, 23, 42), (cx - 18, cy - 16, 24, 18), 2)

        # Arm & steering wheel
        # Arm reaching forward
        pygame.draw.line(surface, (200, 16, 46), (cx - 8, cy - 8), (cx + 8, cy - 6), 4)
        pygame.draw.line(surface, (15, 23, 42), (cx - 8, cy - 8), (cx + 8, cy - 6), 1)
        # Steering wheel
        pygame.draw.circle(surface, (30, 35, 40), (cx + 10, cy - 6), 8, 2)

        # Neck (flesh color)
        pygame.draw.rect(surface, (253, 186, 116), (cx - 12, cy - 26, 6, 12))
        pygame.draw.rect(surface, (15, 23, 42), (cx - 12, cy - 26, 6, 12), 1)

        # Head / Face (flesh color)
        pygame.draw.circle(surface, (253, 186, 116), (cx - 7, cy - 28), 9)
        pygame.draw.circle(surface, (15, 23, 42), (cx - 7, cy - 28), 9, 2)
        # Big nose (classic Bill style)
        pygame.draw.ellipse(surface, (253, 186, 116), (cx - 2, cy - 30, 8, 6))
        pygame.draw.ellipse(surface, (15, 23, 42), (cx - 2, cy - 30, 8, 6), 1)

        # Brown Hair and Beard
        # Hair at the back
        pygame.draw.circle(surface, (120, 80, 50), (cx - 13, cy - 28), 6)
        pygame.draw.circle(surface, (15, 23, 42), (cx - 13, cy - 28), 6, 1)
        # Beard at bottom of face
        pygame.draw.ellipse(surface, (120, 80, 50), (cx - 12, cy - 24, 14, 8))
        pygame.draw.ellipse(surface, (15, 23, 42), (cx - 12, cy - 24, 14, 8), 1)

        # Red Cap pointing backward
        pygame.draw.circle(surface, (200, 16, 46), (cx - 8, cy - 34), 9)
        pygame.draw.circle(surface, (15, 23, 42), (cx - 8, cy - 34), 9, 2)
        # Cap visor (bill) pointing backward to the left
        pygame.draw.polygon(surface, (200, 16, 46), [
            (cx - 16, cy - 37),
            (cx - 24, cy - 34),
            (cx - 15, cy - 31)
        ])
        pygame.draw.polygon(surface, (15, 23, 42), [
            (cx - 16, cy - 37),
            (cx - 24, cy - 34),
            (cx - 15, cy - 31)
        ], 2)

        # Draw vehicle rotated to match alignment angle
        rotated_surface = pygame.transform.rotozoom(surface, -self.angle * 57.2958, 1.0)
        rotated_rect = rotated_surface.get_rect(center=(body_x, body_y))
        screen.blit(rotated_surface, rotated_rect.topleft)

        # Draw wheels
        for wheel in self.wheels:
            wheel_screen_x = camera.world_to_screen_x(wheel.x)
            wheel_screen_y = camera.world_to_screen_y(wheel.y)
            self.draw_wheel(screen, wheel_screen_x, wheel_screen_y, wheel.rotation, wheel.radius)
            # suspension line
            anchor = body_point(self.x, self.y, self.angle, wheel.off_x, wheel.off_y)
            ax = camera.world_to_screen_x(anchor[0])
            ay = camera.world_to_screen_y(anchor[1])
            pygame.draw.line(screen, (24, 32, 47), (ax, ay), (wheel_screen_x, wheel_screen_y), 4)

    def draw_wheel(self, screen: pygame.Surface, x: float, y: float, rotation: float, radius: float) -> None:
        """Draw a styled wheel with a 4-segment cross hub (like the original game)."""

        wheel_surface = pygame.Surface((int(radius * 4), int(radius * 4)), pygame.SRCALPHA)
        center = wheel_surface.get_width() // 2
        
        # Draw outer tyre (dark gray)
        pygame.draw.circle(wheel_surface, (60, 64, 67), (center, center), int(radius))
        pygame.draw.circle(wheel_surface, (32, 33, 36), (center, center), int(radius), 3) # Outer border
        
        # Draw inner hub (silver/light blue)
        hub_radius = radius - 5
        pygame.draw.circle(wheel_surface, (186, 207, 222), (center, center), int(hub_radius))
        
        # Draw 4-segment cross (gray/black lines dividing the hub)
        for index in range(4):
            angle = rotation + index * (6.28318 / 4.0)
            spoke_end = (center + cos(angle) * hub_radius, center + sin(angle) * hub_radius)
            pygame.draw.line(wheel_surface, (50, 60, 70), (center, center), spoke_end, 3)
            
        # Draw small center cap
        pygame.draw.circle(wheel_surface, (137, 162, 180), (center, center), 4)
        
        rect = wheel_surface.get_rect(center=(x, y))
        screen.blit(wheel_surface, rect.topleft)


def tilt_boost(throttle: int, dt: float) -> float:
    """Tiny airborne torque impulse from driver input."""

    return throttle * 0.25 * dt
