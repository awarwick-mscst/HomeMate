from app import app, db
from flask import render_template, request, redirect, url_for, flash, jsonify, send_from_directory, send_file
from models import Appliance, Maintenance, Manual, Vehicle, VehicleMaintenance, HomeTask, HomeTaskHistory, Home, VehicleTelemetry
from datetime import datetime, date, timedelta
import os
from ai_helper import extract_text_from_pdf, query_ollama

UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# --- Dashboard ---
@app.route('/')
def index():
    home = Home.query.first()
    appliances = Appliance.query.all()
    vehicles = Vehicle.query.all()
    home_tasks = HomeTask.query.all()
    
    # Get upcoming tasks
    upcoming_tasks = HomeTask.query.filter(
        HomeTask.next_due <= date.today() + timedelta(days=7)
    ).order_by(HomeTask.next_due).all()
    
    # Get overdue
    overdue_tasks = HomeTask.query.filter(
        HomeTask.next_due < date.today()
    ).all()
    
    # Get predictions for appliances
    predictions = []
    for a in appliances:
        pred = a.get_prediction()
        if pred and pred['days_until'] <= 30:
            predictions.append({'item': a, 'type': 'appliance', **pred})
    
    for v in vehicles:
        pred = v.get_prediction()
        if pred and pred['days_until'] <= 30:
            predictions.append({'item': v, 'type': 'vehicle', **pred})
    
    return render_template('index.html', 
                         home=home,
                         appliances=appliances, 
                         vehicles=vehicles,
                         home_tasks=home_tasks,
                         upcoming_tasks=upcoming_tasks,
                         overdue_tasks=overdue_tasks,
                         predictions=predictions)

# --- Home Settings ---
@app.route('/home/update', methods=['POST'])
def update_home():
    home = Home.query.first()
    if not home:
        home = Home()
        db.session.add(home)
    home.address = request.form.get('address')
    db.session.commit()
    flash('Address saved!', 'success')
    return redirect(url_for('index'))

# --- Appliances ---
@app.route('/appliances')
def appliances():
    all_appliances = Appliance.query.all()
    return render_template('appliances.html', appliances=all_appliances)

@app.route('/appliance/add', methods=['GET', 'POST'])
def add_appliance():
    if request.method == 'POST':
        appliance = Appliance(
            name=request.form['name'],
            model=request.form.get('model'),
            serial_number=request.form.get('serial_number'),
            location=request.form.get('location'),
            purchase_date=datetime.strptime(request.form['purchase_date'], '%Y-%m-%d').date() if request.form.get('purchase_date') else None,
            warranty_expiry=datetime.strptime(request.form['warranty_expiry'], '%Y-%m-%d').date() if request.form.get('warranty_expiry') else None,
            manual_url=request.form.get('manual_url'),
            notes=request.form.get('notes')
        )
        db.session.add(appliance)
        db.session.commit()
        flash('Appliance added!', 'success')
        return redirect(url_for('appliances'))
    return render_template('appliance_form.html', appliance=None)

@app.route('/appliance/<int:id>')
def view_appliance(id):
    appliance = Appliance.query.get_or_404(id)
    prediction = appliance.get_prediction()
    return render_template('appliance_view.html', appliance=appliance, prediction=prediction)

@app.route('/appliance/<int:id>/edit', methods=['GET', 'POST'])
def edit_appliance(id):
    appliance = Appliance.query.get_or_404(id)
    if request.method == 'POST':
        appliance.name = request.form['name']
        appliance.model = request.form.get('model')
        appliance.serial_number = request.form.get('serial_number')
        appliance.location = request.form.get('location')
        appliance.purchase_date = datetime.strptime(request.form['purchase_date'], '%Y-%m-%d').date() if request.form.get('purchase_date') else None
        appliance.warranty_expiry = datetime.strptime(request.form['warranty_expiry'], '%Y-%m-%d').date() if request.form.get('warranty_expiry') else None
        appliance.manual_url = request.form.get('manual_url')
        appliance.notes = request.form.get('notes')
        db.session.commit()
        flash('Appliance updated!', 'success')
        return redirect(url_for('view_appliance', id=appliance.id))
    return render_template('appliance_form.html', appliance=appliance)

@app.route('/appliance/<int:id>/delete', methods=['POST'])
def delete_appliance(id):
    appliance = Appliance.query.get_or_404(id)
    for manual in appliance.manuals:
        try:
            os.remove(os.path.join(app.config['UPLOAD_FOLDER'], manual.filename))
        except:
            pass
    db.session.delete(appliance)
    db.session.commit()
    flash('Appliance deleted.', 'success')
    return redirect(url_for('appliances'))

# --- Vehicles ---
@app.route('/vehicles')
def vehicles():
    all_vehicles = Vehicle.query.all()
    return render_template('vehicles.html', vehicles=all_vehicles)

@app.route('/vehicle/add', methods=['GET', 'POST'])
def add_vehicle():
    if request.method == 'POST':
        vehicle = Vehicle(
            name=request.form['name'],
            make=request.form.get('make'),
            model=request.form.get('model'),
            year=int(request.form['year']) if request.form.get('year') else None,
            vin=request.form.get('vin'),
            license_plate=request.form.get('license_plate'),
            purchase_date=datetime.strptime(request.form['purchase_date'], '%Y-%m-%d').date() if request.form.get('purchase_date') else None,
            current_mileage=int(request.form['current_mileage']) if request.form.get('current_mileage') else None,
            notes=request.form.get('notes')
        )
        db.session.add(vehicle)
        db.session.commit()
        flash('Vehicle added!', 'success')
        return redirect(url_for('vehicles'))
    return render_template('vehicle_form.html', vehicle=None)

@app.route('/vehicle/<int:id>')
def view_vehicle(id):
    vehicle = Vehicle.query.get_or_404(id)
    prediction = vehicle.get_prediction()
    manuals = Manual.query.filter_by(vehicle_id=id).all()
    telemetry = VehicleTelemetry.query.filter_by(vehicle_id=id).order_by(VehicleTelemetry.timestamp.desc()).first()
    return render_template('vehicle_view.html', vehicle=vehicle, prediction=prediction, manuals=manuals, telemetry=telemetry)

@app.route('/vehicle/<int:id>/edit', methods=['GET', 'POST'])
def edit_vehicle(id):
    vehicle = Vehicle.query.get_or_404(id)
    if request.method == 'POST':
        vehicle.name = request.form['name']
        vehicle.make = request.form.get('make')
        vehicle.model = request.form.get('model')
        vehicle.year = int(request.form['year']) if request.form.get('year') else None
        vehicle.vin = request.form.get('vin')
        vehicle.license_plate = request.form.get('license_plate')
        vehicle.purchase_date = datetime.strptime(request.form['purchase_date'], '%Y-%m-%d').date() if request.form.get('purchase_date') else None
        vehicle.current_mileage = int(request.form['current_mileage']) if request.form.get('current_mileage') else None
        vehicle.notes = request.form.get('notes')
        db.session.commit()
        flash('Vehicle updated!', 'success')
        return redirect(url_for('view_vehicle', id=vehicle.id))
    return render_template('vehicle_form.html', vehicle=vehicle)

@app.route('/vehicle/<int:id>/delete', methods=['POST'])
def delete_vehicle(id):
    vehicle = Vehicle.query.get_or_404(id)
    db.session.delete(vehicle)
    db.session.commit()
    flash('Vehicle deleted.', 'success')
    return redirect(url_for('vehicles'))

# --- Home Tasks ---
@app.route('/home-tasks')
def home_tasks():
    all_tasks = HomeTask.query.all()
    return render_template('home_tasks.html', tasks=all_tasks)

@app.route('/home-task/add', methods=['GET', 'POST'])
def add_home_task():
    if request.method == 'POST':
        frequency = request.form.get('frequency_days')
        task = HomeTask(
            name=request.form['name'],
            description=request.form.get('description'),
            location=request.form.get('location'),
            frequency_days=int(frequency) if frequency else None,
            last_completed=datetime.strptime(request.form['last_completed'], '%Y-%m-%d').date() if request.form.get('last_completed') else None,
            notes=request.form.get('notes')
        )
        task.update_next_due()
        db.session.add(task)
        db.session.commit()
        flash('Task added!', 'success')
        return redirect(url_for('home_tasks'))
    return render_template('home_task_form.html', task=None)

@app.route('/home-task/<int:id>')
def view_home_task(id):
    task = HomeTask.query.get_or_404(id)
    return render_template('home_task_view.html', task=task)

@app.route('/home-task/<int:id>/complete', methods=['POST'])
def complete_home_task(id):
    task = HomeTask.query.get_or_404(id)
    task.last_completed = date.today()
    task.update_next_due()
    
    # Add to history
    history = HomeTaskHistory(
        task_id=task.id,
        completed_date=date.today(),
        notes=request.form.get('notes', '')
    )
    db.session.add(history)
    db.session.commit()
    
    flash('Task completed!', 'success')
    return redirect(url_for('home_tasks'))

@app.route('/home-task/<int:id>/edit', methods=['GET', 'POST'])
def edit_home_task(id):
    task = HomeTask.query.get_or_404(id)
    if request.method == 'POST':
        task.name = request.form['name']
        task.description = request.form.get('description')
        task.location = request.form.get('location')
        frequency = request.form.get('frequency_days')
        task.frequency_days = int(frequency) if frequency else None
        task.last_completed = datetime.strptime(request.form['last_completed'], '%Y-%m-%d').date() if request.form.get('last_completed') else None
        task.notes = request.form.get('notes')
        task.update_next_due()
        db.session.commit()
        flash('Task updated!', 'success')
        return redirect(url_for('view_home_task', id=task.id))
    return render_template('home_task_form.html', task=task)

@app.route('/home-task/<int:id>/delete', methods=['POST'])
def delete_home_task(id):
    task = HomeTask.query.get_or_404(id)
    db.session.delete(task)
    db.session.commit()
    flash('Task deleted.', 'success')
    return redirect(url_for('home_tasks'))

# --- Maintenance ---
@app.route('/appliance/<int:id>/maintenance/add', methods=['GET', 'POST'])
def add_maintenance(id):
    appliance = Appliance.query.get_or_404(id)
    if request.method == 'POST':
        maintenance = Maintenance(
            appliance_id=appliance.id,
            date=datetime.strptime(request.form['date'], '%Y-%m-%d').date() if request.form.get('date') else datetime.utcnow().date(),
            description=request.form['description'],
            cost=float(request.form.get('cost', 0)),
            parts=request.form.get('parts'),
            performed_by=request.form.get('performed_by')
        )
        db.session.add(maintenance)
        db.session.commit()
        flash('Maintenance logged!', 'success')
        return redirect(url_for('view_appliance', id=appliance.id))
    return render_template('maintenance_form.html', appliance=appliance, maintenance=None, type='appliance')

@app.route('/vehicle/<int:id>/maintenance/add', methods=['GET', 'POST'])
def add_vehicle_maintenance(id):
    vehicle = Vehicle.query.get_or_404(id)
    if request.method == 'POST':
        maintenance = VehicleMaintenance(
            vehicle_id=vehicle.id,
            date=datetime.strptime(request.form['date'], '%Y-%m-%d').date() if request.form.get('date') else datetime.utcnow().date(),
            mileage=int(request.form['mileage']) if request.form.get('mileage') else None,
            description=request.form['description'],
            cost=float(request.form.get('cost', 0)),
            parts=request.form.get('parts'),
            performed_by=request.form.get('performed_by')
        )
        db.session.add(maintenance)
        db.session.commit()
        flash('Maintenance logged!', 'success')
        return redirect(url_for('view_vehicle', id=vehicle.id))
    return render_template('maintenance_form.html', appliance=vehicle, maintenance=None, type='vehicle')

@app.route('/maintenance/<int:id>/edit', methods=['GET', 'POST'])
def edit_maintenance(id):
    maintenance = Maintenance.query.get_or_404(id)
    if request.method == 'POST':
        maintenance.date = datetime.strptime(request.form['date'], '%Y-%m-%d').date() if request.form.get('date') else maintenance.date
        maintenance.description = request.form['description']
        maintenance.cost = float(request.form.get('cost', 0))
        maintenance.parts = request.form.get('parts')
        maintenance.performed_by = request.form.get('performed_by')
        db.session.commit()
        flash('Maintenance updated!', 'success')
        return redirect(url_for('view_appliance', id=maintenance.appliance_id))
    return render_template('maintenance_form.html', appliance=maintenance.appliance, maintenance=maintenance, type='appliance')

@app.route('/vehicle-maintenance/<int:id>/edit', methods=['GET', 'POST'])
def edit_vehicle_maintenance(id):
    maintenance = VehicleMaintenance.query.get_or_404(id)
    if request.method == 'POST':
        maintenance.date = datetime.strptime(request.form['date'], '%Y-%m-%d').date() if request.form.get('date') else maintenance.date
        maintenance.mileage = int(request.form['mileage']) if request.form.get('mileage') else None
        maintenance.description = request.form['description']
        maintenance.cost = float(request.form.get('cost', 0))
        maintenance.parts = request.form.get('parts')
        maintenance.performed_by = request.form.get('performed_by')
        db.session.commit()
        flash('Maintenance updated!', 'success')
        return redirect(url_for('view_vehicle', id=maintenance.vehicle_id))
    return render_template('maintenance_form.html', appliance=maintenance.vehicle, maintenance=maintenance, type='vehicle')

@app.route('/maintenance/<int:id>/delete', methods=['POST'])
def delete_maintenance(id):
    maintenance = Maintenance.query.get_or_404(id)
    appliance_id = maintenance.appliance_id
    db.session.delete(maintenance)
    db.session.commit()
    flash('Maintenance record deleted.', 'success')
    return redirect(url_for('view_appliance', id=appliance_id))

@app.route('/vehicle-maintenance/<int:id>/delete', methods=['POST'])
def delete_vehicle_maintenance(id):
    maintenance = VehicleMaintenance.query.get_or_404(id)
    vehicle_id = maintenance.vehicle_id
    db.session.delete(maintenance)
    db.session.commit()
    flash('Maintenance record deleted.', 'success')
    return redirect(url_for('view_vehicle', id=vehicle_id))

@app.route('/maintenance')
def all_maintenance():
    app_records = Maintenance.query.all()
    veh_records = VehicleMaintenance.query.all()
    return render_template('maintenance_all.html', app_records=app_records, veh_records=veh_records)

# --- Manual Upload ---
@app.route('/appliance/<int:id>/manual/upload', methods=['POST'])
def upload_manual(id):
    appliance = Appliance.query.get_or_404(id)
    if 'file' not in request.files:
        flash('No file selected', 'danger')
        return redirect(url_for('view_appliance', id=id))
    
    file = request.files['file']
    if file.filename == '' or not file.filename.lower().endswith('.pdf'):
        flash('Only PDF files are supported.', 'danger')
        return redirect(url_for('view_appliance', id=id))
    
    filename = f"{datetime.utcnow().timestamp()}_{file.filename}"
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)
    
    extracted_text = extract_text_from_pdf(filepath)
    
    manual = Manual(
        appliance_id=appliance.id,
        filename=filename,
        original_name=file.filename,
        extracted_text=extracted_text
    )
    db.session.add(manual)
    db.session.commit()
    
    flash('Manual uploaded!', 'success')
    return redirect(url_for('view_appliance', id=id))

@app.route('/appliance/<int:id>/manual/<int:manual_id>/delete', methods=['POST'])
def delete_manual(id, manual_id):
    manual = Manual.query.get_or_404(manual_id)
    try:
        os.remove(os.path.join(app.config['UPLOAD_FOLDER'], manual.filename))
    except:
        pass
    db.session.delete(manual)
    db.session.commit()
    flash('Manual deleted.', 'success')
    return redirect(url_for('view_appliance', id=id))

# --- Vehicle Manual Upload ---
@app.route('/vehicle/<int:id>/manual/upload', methods=['POST'])
def upload_vehicle_manual(id):
    vehicle = Vehicle.query.get_or_404(id)
    if 'file' not in request.files:
        flash('No file selected', 'danger')
        return redirect(url_for('view_vehicle', id=id))
    
    file = request.files['file']
    if file.filename == '' or not file.filename.lower().endswith('.pdf'):
        flash('Only PDF files are supported.', 'danger')
        return redirect(url_for('view_vehicle', id=id))
    
    filename = f"{datetime.utcnow().timestamp()}_{file.filename}"
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)
    
    extracted_text = extract_text_from_pdf(filepath)
    
    manual = Manual(
        vehicle_id=vehicle.id,
        filename=filename,
        original_name=file.filename,
        extracted_text=extracted_text
    )
    db.session.add(manual)
    db.session.commit()
    
    flash('Manual uploaded!', 'success')
    return redirect(url_for('view_vehicle', id=id))

@app.route('/vehicle/<int:id>/manual/<int:manual_id>/delete', methods=['POST'])
def delete_vehicle_manual(id, manual_id):
    manual = Manual.query.get_or_404(manual_id)
    try:
        os.remove(os.path.join(app.config['UPLOAD_FOLDER'], manual.filename))
    except:
        pass
    db.session.delete(manual)
    db.session.commit()
    flash('Manual deleted.', 'success')
    return redirect(url_for('view_vehicle', id=id))

@app.route('/uploads/<filename>')
def serve_manual(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# --- AI Q&A ---
@app.route('/appliance/<int:id>/ask', methods=['POST'])
def ask_about_appliance(id):
    appliance = Appliance.query.get_or_404(id)
    question = request.form.get('question', '').strip()
    
    if not question:
        return jsonify({'error': 'No question provided'}), 400
    
    context = f"""Appliance: {appliance.name}
Model: {appliance.model or 'N/A'}
Serial Number: {appliance.serial_number or 'N/A'}
Location: {appliance.location or 'N/A'}
Notes: {appliance.notes or 'N/A'}

Maintenance History:
"""
    for record in appliance.maintenance_records:
        context += f"- {record.date}: {record.description} (${record.cost})"
        if record.parts:
            context += f", Parts: {record.parts}"
        context += "\n"

    context += "\nManuals:\n"
    for manual in appliance.manuals:
        context += f"\n--- {manual.original_name} ---\n"
        context += manual.extracted_text or "(No text extracted)"
        context += "\n"

    answer = query_ollama(question, context)
    
    return jsonify({
        'question': question,
        'answer': answer
    })

@app.route('/vehicle/<int:id>/ask', methods=['POST'])
def ask_about_vehicle(id):
    vehicle = Vehicle.query.get_or_404(id)
    question = request.form.get('question', '').strip()
    
    if not question:
        return jsonify({'error': 'No question provided'}), 400
    
    context = f"""Vehicle: {vehicle.name}
Make: {vehicle.make or 'N/A'}
Model: {vehicle.model or 'N/A'}
Year: {vehicle.year or 'N/A'}
VIN: {vehicle.vin or 'N/A'}
License Plate: {vehicle.license_plate or 'N/A'}
Current Mileage: {vehicle.current_mileage or 'N/A'}
Notes: {vehicle.notes or 'N/A'}

Maintenance History:
"""
    for record in vehicle.maintenance_records:
        context += f"- {record.date} ({record.mileage} miles): {record.description} (${record.cost})"
        if record.parts:
            context += f", Parts: {record.parts}"
        context += "\n"

    # Add manuals to context
    manuals = Manual.query.filter_by(vehicle_id=id).all()
    if manuals:
        context += "\nManuals:\n"
        for manual in manuals:
            context += f"\n--- {manual.original_name} ---\n"
            context += manual.extracted_text or "(No text extracted)"
            context += "\n"

    answer = query_ollama(question, context)
    
    return jsonify({
        'question': question,
        'answer': answer
    })

# --- OBD2 Telemetry API ---
@app.route('/api/vehicle/<int:id>/telemetry', methods=['POST'])
def receive_telemetry(id):
    """Receive OBD2 telemetry from phone app"""
    vehicle = Vehicle.query.get_or_404(id)
    data = request.get_json()
    
    telemetry = VehicleTelemetry(
        vehicle_id=id,
        rpm=data.get('rpm'),
        speed=data.get('speed'),
        coolant_temp=data.get('coolant_temp'),
        throttle=data.get('throttle'),
        fuel_level=data.get('fuel_level'),
        battery_voltage=data.get('battery_voltage'),
        dtc_codes=data.get('dtc_codes', ''),
        mileage=data.get('mileage')
    )
    db.session.add(telemetry)
    db.session.commit()
    
    return jsonify({'status': 'ok', 'id': telemetry.id})

@app.route('/api/vehicle/<int:id>/telemetry/latest')
def get_latest_telemetry(id):
    """Get latest telemetry for a vehicle"""
    telemetry = VehicleTelemetry.query.filter_by(vehicle_id=id).order_by(VehicleTelemetry.timestamp.desc()).first()
    if not telemetry:
        return jsonify({'error': 'No data'}), 404
    
    return jsonify({
        'rpm': telemetry.rpm,
        'speed': telemetry.speed,
        'coolant_temp': telemetry.coolant_temp,
        'throttle': telemetry.throttle,
        'fuel_level': telemetry.fuel_level,
        'battery_voltage': telemetry.battery_voltage,
        'dtc_codes': telemetry.dtc_codes,
        'mileage': telemetry.mileage,
        'timestamp': telemetry.timestamp.isoformat()
    })

# --- OBD2 App ---
@app.route('/obd2-app/')
def obd2_app():
    return send_file('static/obd2-app/index.html')

@app.route('/obd2-app/<path:filename>')
def obd2_static(filename):
    return send_from_directory('static/obd2-app', filename)
