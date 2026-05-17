"""SQLAlchemy ORM models for the Fleet & Truck Management subsystem.

These models share `Base` with database.models so that
`Base.metadata.create_all(engine)` provisions both legacy and fleet tables
in a single call. The fleet module is intentionally decoupled from the
computer-vision detection engine.
"""

from datetime import datetime

from sqlalchemy import (
    Column, Integer, String, Float, Boolean, Text, DateTime, Date,
    ForeignKey, Index, UniqueConstraint
)
from sqlalchemy.orm import relationship

from database.models import Base


# ---------------------------------------------------------------------------
# Truck
# ---------------------------------------------------------------------------
class Truck(Base):
    __tablename__ = "fleet_trucks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    truck_code = Column(String(30), unique=True, nullable=False, index=True)
    plate_number = Column(String(30), unique=True, nullable=False, index=True)
    capacity = Column(Float, nullable=False, default=0.0)        # in kilograms
    fuel_type = Column(String(20), nullable=False, default="diesel")
    status = Column(String(20), nullable=False, default="available", index=True)
    assigned_zone = Column(String(80), nullable=True)
    purchase_date = Column(Date, nullable=True)
    notes = Column(Text, nullable=True)

    # Soft delete + audit
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow,
                        onupdate=datetime.utcnow, nullable=False)

    # Relationships
    drivers = relationship("Driver", back_populates="truck",
                           foreign_keys="Driver.assigned_truck_id")
    trips = relationship("CollectionTrip", back_populates="truck",
                         cascade="save-update, merge")
    maintenance_records = relationship("MaintenanceRecord", back_populates="truck",
                                       cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Truck(id={self.id}, code='{self.truck_code}', status='{self.status}')>"


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------
class Driver(Base):
    __tablename__ = "fleet_drivers"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    phone = Column(String(30), nullable=True)
    email = Column(String(120), nullable=True)
    license_number = Column(String(50), unique=True, nullable=False, index=True)
    assigned_truck_id = Column(Integer, ForeignKey("fleet_trucks.id"),
                               nullable=True, index=True)
    status = Column(String(20), nullable=False, default="available", index=True)

    is_active = Column(Boolean, default=True, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow,
                        onupdate=datetime.utcnow, nullable=False)

    # Relationships
    truck = relationship("Truck", back_populates="drivers",
                         foreign_keys=[assigned_truck_id])
    trips = relationship("CollectionTrip", back_populates="driver")

    def __repr__(self):
        return f"<Driver(id={self.id}, name='{self.name}', license='{self.license_number}')>"


# ---------------------------------------------------------------------------
# Route
# ---------------------------------------------------------------------------
class Route(Base):
    __tablename__ = "fleet_routes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    route_name = Column(String(120), unique=True, nullable=False, index=True)
    zone = Column(String(80), nullable=False, index=True)
    estimated_distance = Column(Float, nullable=True)            # in kilometres
    estimated_duration = Column(Integer, nullable=True)          # in minutes
    status = Column(String(20), nullable=False, default="active", index=True)
    notes = Column(Text, nullable=True)

    is_active = Column(Boolean, default=True, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow,
                        onupdate=datetime.utcnow, nullable=False)

    trips = relationship("CollectionTrip", back_populates="route")

    def __repr__(self):
        return f"<Route(id={self.id}, name='{self.route_name}', zone='{self.zone}')>"


# ---------------------------------------------------------------------------
# Collection Trip
# ---------------------------------------------------------------------------
class CollectionTrip(Base):
    __tablename__ = "fleet_trips"

    id = Column(Integer, primary_key=True, autoincrement=True)
    truck_id = Column(Integer, ForeignKey("fleet_trucks.id"),
                      nullable=False, index=True)
    driver_id = Column(Integer, ForeignKey("fleet_drivers.id"),
                       nullable=False, index=True)
    route_id = Column(Integer, ForeignKey("fleet_routes.id"),
                      nullable=False, index=True)

    start_time = Column(DateTime, nullable=True)
    end_time = Column(DateTime, nullable=True)
    waste_weight = Column(Float, nullable=True, default=0.0)     # in kilograms
    trip_status = Column(String(20), nullable=False,
                         default="scheduled", index=True)
    notes = Column(Text, nullable=True)

    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow,
                        nullable=False, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow,
                        onupdate=datetime.utcnow, nullable=False)

    truck = relationship("Truck", back_populates="trips")
    driver = relationship("Driver", back_populates="trips")
    route = relationship("Route", back_populates="trips")

    __table_args__ = (
        Index("ix_trips_status_created", "trip_status", "created_at"),
    )

    def __repr__(self):
        return (f"<CollectionTrip(id={self.id}, truck={self.truck_id}, "
                f"driver={self.driver_id}, status='{self.trip_status}')>")


# ---------------------------------------------------------------------------
# Maintenance Record
# ---------------------------------------------------------------------------
class MaintenanceRecord(Base):
    __tablename__ = "fleet_maintenance"

    id = Column(Integer, primary_key=True, autoincrement=True)
    truck_id = Column(Integer, ForeignKey("fleet_trucks.id"),
                      nullable=False, index=True)
    service_type = Column(String(60), nullable=False)
    service_date = Column(Date, nullable=False, index=True)
    next_service_date = Column(Date, nullable=True, index=True)
    cost = Column(Float, nullable=True, default=0.0)
    notes = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow,
                        onupdate=datetime.utcnow, nullable=False)

    truck = relationship("Truck", back_populates="maintenance_records")

    def __repr__(self):
        return (f"<MaintenanceRecord(id={self.id}, truck={self.truck_id}, "
                f"type='{self.service_type}', date={self.service_date})>")
