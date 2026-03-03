from app import db
from datetime import datetime, date
from sqlalchemy import func

class Appliance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    model = db.Column(db.String(100))
    serial_number = db.Column(db.String(100))
    location = db.Column(db.String(100))
    purchase_date = db.Column(db.Date)
    warranty_expiry = db.Column(db.Date)
    manual_url = db.Column(db.String(500))
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    maintenance_records = db.relationship('Maintenance', backref='appliance', lazy=True, cascade='all, delete-orphan')
    manuals = db.relationship('Manual', backref='appliance', lazy=True, cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Appliance {self.name}>'
    
    def get_prediction(self):
        """Predict next maintenance based on history."""
        if len(self.maintenance_records) < 2:
            return None
        
        # Get intervals between maintenance
        sorted_records = sorted(self.maintenance_records, key=lambda x: x.date)
        intervals = []
        for i in range(1, len(sorted_records)):
            delta = (sorted_records[i].date - sorted_records[i-1].date).days
            intervals.append(delta)
        
        if not intervals:
            return None
        
        avg_interval = sum(intervals) / len(intervals)
        last_maintenance = sorted_records[-1].date
        next_predicted = last_maintenance + timedelta(days=int(avg_interval))
        
        days_until = (next_predicted - date.today()).days
        
        return {
            'avg_interval_days': int(avg_interval),
            'last_maintenance': last_maintenance,
            'next_predicted': next_predicted,
            'days_until': days_until
        }

class Vehicle(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)  # e.g., "2020 Honda Civic"
    make = db.Column(db.String(50))
    model = db.Column(db.String(50))
    year = db.Column(db.Integer)
    vin = db.Column(db.String(20))
    license_plate = db.Column(db.String(20))
    purchase_date = db.Column(db.Date)
    current_mileage = db.Column(db.Integer)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    maintenance_records = db.relationship('VehicleMaintenance', backref='vehicle', lazy=True, cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Vehicle {self.name}>'
    
    def get_prediction(self):
        """Predict next maintenance based on history."""
        if len(self.maintenance_records) < 2:
            return None
        
        sorted_records = sorted(self.maintenance_records, key=lambda x: x.date)
        intervals = []
        for i in range(1, len(sorted_records)):
            delta = (sorted_records[i].date - sorted_records[i-1].date).days
            intervals.append(delta)
        
        if not intervals:
            return None
        
        avg_interval = sum(intervals) / len(intervals)
        last_maintenance = sorted_records[-1].date
        next_predicted = last_maintenance + timedelta(days=int(avg_interval))
        
        days_until = (next_predicted - date.today()).days
        
        return {
            'avg_interval_days': int(avg_interval),
            'last_maintenance': last_maintenance,
            'next_predicted': next_predicted,
            'days_until': days_until
        }

class Maintenance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    appliance_id = db.Column(db.Integer, db.ForeignKey('appliance.id'), nullable=False)
    date = db.Column(db.Date, default=datetime.utcnow)
    description = db.Column(db.Text, nullable=False)
    cost = db.Column(db.Float, default=0)
    parts = db.Column(db.String(200))
    performed_by = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Maintenance {self.id} for {self.appliance_id}>'

class VehicleMaintenance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    vehicle_id = db.Column(db.Integer, db.ForeignKey('vehicle.id'), nullable=False)
    date = db.Column(db.Date, default=datetime.utcnow)
    mileage = db.Column(db.Integer)
    description = db.Column(db.Text, nullable=False)
    cost = db.Column(db.Float, default=0)
    parts = db.Column(db.String(200))
    performed_by = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<VehicleMaintenance {self.id} for {self.vehicle_id}>'

class Manual(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    appliance_id = db.Column(db.Integer, db.ForeignKey('appliance.id'), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    original_name = db.Column(db.String(255), nullable=False)
    extracted_text = db.Column(db.Text)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Manual {self.original_name}>'

class HomeTask(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    location = db.Column(db.String(100))
    frequency_days = db.Column(db.Integer)  # NULL = one-time, otherwise recurring
    last_completed = db.Column(db.Date)
    next_due = db.Column(db.Date)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    history = db.relationship('HomeTaskHistory', backref='task', lazy=True, cascade='all, delete-orphan')

    def __repr__(self):
        return f'<HomeTask {self.name}>'
    
    def update_next_due(self):
        if self.frequency_days and self.last_completed:
            self.next_due = self.last_completed + timedelta(days=self.frequency_days)

class HomeTaskHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.Integer, db.ForeignKey('home_task.id'), nullable=False)
    completed_date = db.Column(db.Date, default=datetime.utcnow)
    notes = db.Column(db.Text)

    def __repr__(self):
        return f'<HomeTaskHistory {self.id}>'

class Home(db.Model):
    """Single home/address for the household."""
    id = db.Column(db.Integer, primary_key=True)
    address = db.Column(db.Text)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

from datetime import timedelta
