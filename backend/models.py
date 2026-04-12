from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from .database import Base
import datetime

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True, nullable=True)
    hashed_password = Column(String)
    is_active = Column(Boolean, default=True)
    role = Column(String, default="student") # roles: "student", "club_admin", "super_admin"
    club_name = Column(String, nullable=True, index=True) # Only for club_admin
    is_admin = Column(Boolean, default=False) # Legacy field, can use for super_admin
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    # Relationships
    reminders = relationship("Reminder", back_populates="user")
    subscriptions = relationship("ClubSubscription", back_populates="user")
    notifications = relationship("Notification", back_populates="user")

class Notification(Base):
    __tablename__ = "notifications"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'))
    event_id = Column(Integer, ForeignKey('events.id', ondelete='CASCADE'))
    message = Column(String)
    type = Column(String) # e.g., "Reminder: 1 Day Before"
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    user = relationship("User", back_populates="notifications")

class Event(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    description = Column(Text)
    date_str = Column(String, nullable=True) # The raw extracted string
    event_date = Column(DateTime, nullable=True) # Actual parsed date for reminders
    time = Column(String, nullable=True)
    venue = Column(String, nullable=True)
    club_name = Column(String, index=True)
    profile_pic = Column(String, nullable=True)
    image_path = Column(String)
    source_url = Column(String, nullable=True)
    category = Column(String, nullable=True)
    registration_link = Column(String, nullable=True)
    last_register_date = Column(String, nullable=True)
    is_published = Column(Boolean, default=False)  # False = staging, True = visible on frontend
    source_type = Column(String, default="manual") # "manual" or "instagram"
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    # Relationships
    reminders = relationship("Reminder", back_populates="event")

class Feedback(Base):
    __tablename__ = "feedbacks"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, ForeignKey('events.id', ondelete='CASCADE'))
    user_name = Column(String)
    rating = Column(Integer)
    comment = Column(String, nullable=True)
    sentiment = Column(String, default="Pending")
    user_id = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class Reminder(Base):
    __tablename__ = "reminders"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'))
    event_id = Column(Integer, ForeignKey('events.id', ondelete='CASCADE'))
    reminder_type = Column(String) # "2h", "6h", "24h"
    reminder_time = Column(DateTime) # The exact time to notify
    is_sent = Column(Boolean, default=False) # Marked True when shown in app
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    user = relationship("User", back_populates="reminders")
    event = relationship("Event", back_populates="reminders")

class ClubSubscription(Base):
    __tablename__ = "club_subscriptions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'))
    club_name = Column(String, index=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    user = relationship("User", back_populates="subscriptions")
