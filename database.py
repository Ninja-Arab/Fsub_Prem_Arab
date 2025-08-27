from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime, Text, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timedelta
import config

# Inisialisasi database
engine = create_engine(config.DATABASE_URL, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Model Database
class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, unique=True, index=True)
    username = Column(String, nullable=True)
    full_name = Column(String)
    joined_at = Column(DateTime, default=datetime.utcnow)
    subscription_end = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True)
    referred_by = Column(Integer, nullable=True)
    last_notified = Column(DateTime, nullable=True)

class Seller(Base):
    __tablename__ = "sellers"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, unique=True, index=True)
    name = Column(String)
    added_by = Column(Integer)
    added_at = Column(DateTime, default=datetime.utcnow)

class Button(Base):
    __tablename__ = "buttons"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True)
    text = Column(Text)
    url = Column(String)
    position = Column(Integer, default=0)

class SubscriptionLog(Base):
    __tablename__ = "subscription_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer)
    seller_id = Column(Integer, nullable=True)
    days_added = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)

class PurchaseLog(Base):
    __tablename__ = "purchase_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer)
    seller_id = Column(Integer)
    amount = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)

# Buat tabel
Base.metadata.create_all(bind=engine)

# Fungsi utilitas database
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_user(db, user_id: int):
    return db.query(User).filter(User.user_id == user_id).first()

def create_user(db, user_id: int, username: str, full_name: str):
    db_user = User(user_id=user_id, username=username, full_name=full_name)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def update_subscription(db, user_id: int, days: int):
    user = get_user(db, user_id)
    if user:
        if user.subscription_end and user.subscription_end > datetime.utcnow():
            # Perpanjang subscription
            user.subscription_end += timedelta(days=days)
        else:
            # Buat subscription baru
            user.subscription_end = datetime.utcnow() + timedelta(days=days)
        db.commit()
        return user
    return None

def get_sellers(db):
    return db.query(Seller).all()

def add_seller(db, user_id: int, name: str, added_by: int):
    seller = Seller(user_id=user_id, name=name, added_by=added_by)
    db.add(seller)
    db.commit()
    db.refresh(seller)
    return seller

def remove_seller(db, user_id: int):
    seller = db.query(Seller).filter(Seller.user_id == user_id).first()
    if seller:
        db.delete(seller)
        db.commit()
        return True
    return False

def get_buttons(db):
    return db.query(Button).order_by(Button.position).all()

def add_button(db, name: str, text: str, url: str, position: int = 0):
    button = Button(name=name, text=text, url=url, position=position)
    db.add(button)
    db.commit()
    db.refresh(button)
    return button

def remove_button(db, name: str):
    button = db.query(Button).filter(Button.name == name).first()
    if button:
        db.delete(button)
        db.commit()
        return True
    return False

def update_button(db, name: str, text: str = None, url: str = None, position: int = None):
    button = db.query(Button).filter(Button.name == name).first()
    if button:
        if text is not None:
            button.text = text
        if url is not None:
            button.url = url
        if position is not None:
            button.position = position
        db.commit()
        return True
    return False

def get_stats(db):
    total_users = db.query(User).count()
    active_subscriptions = db.query(User).filter(
        User.subscription_end > datetime.utcnow()
    ).count()
    expired_subscriptions = db.query(User).filter(
        User.subscription_end < datetime.utcnow()
    ).count()
    new_users_today = db.query(User).filter(
        func.date(User.joined_at) == datetime.utcnow().date()
    ).count()
    total_sellers = db.query(Seller).count()
    
    return {
        "total_users": total_users,
        "active_subscriptions": active_subscriptions,
        "expired_subscriptions": expired_subscriptions,
        "new_users_today": new_users_today,
        "total_sellers": total_sellers
    }

def log_purchase(db, user_id: int, seller_id: int, amount: int):
    log = PurchaseLog(user_id=user_id, seller_id=seller_id, amount=amount)
    db.add(log)
    db.commit()
    db.refresh(log)
    return log

def log_subscription(db, user_id: int, seller_id: int, days_added: int):
    log = SubscriptionLog(user_id=user_id, seller_id=seller_id, days_added=days_added)
    db.add(log)
    db.commit()
    db.refresh(log)
    return log

def get_users_expiring_soon(db, days: int = 3):
    """Dapatkan pengguna yang subscription-nya akan habis dalam X hari"""
    target_date = datetime.utcnow() + timedelta(days=days)
    return db.query(User).filter(
        User.subscription_end <= target_date,
        User.subscription_end > datetime.utcnow(),
        (User.last_notified.is_(None)) | (User.last_notified < datetime.utcnow() - timedelta(days=1))
    ).all()

def update_last_notified(db, user_id: int):
    """Update waktu notifikasi terakhir"""
    user = get_user(db, user_id)
    if user:
        user.last_notified = datetime.utcnow()
        db.commit()
