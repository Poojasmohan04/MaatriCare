from flask import Flask, request, jsonify
from flask_cors import CORS
from models import get_db, init_db
import json
from datetime import datetime, date
from deep_translator import GoogleTranslator

app = Flask(__name__)
CORS(app)

# ──────────────────────────────────────────────
# RISK DETECTION ENGINE (Rule-based)
# ──────────────────────────────────────────────

SYMPTOM_RISK_MAP = {
    # High-risk symptoms
    'heavy bleeding': {'score': 9, 'level': 'HIGH', 'advice': 'Seek emergency medical help immediately. Apply firm pressure with clean cloth. Keep the patient lying down with legs elevated.'},
    'bleeding': {'score': 8, 'level': 'HIGH', 'advice': 'Any bleeding during pregnancy needs immediate medical attention. Contact your nearest health center now.'},
    'severe headache': {'score': 7, 'level': 'HIGH', 'advice': 'This could indicate preeclampsia. Check blood pressure if possible. Seek medical attention urgently.'},
    'blurred vision': {'score': 8, 'level': 'HIGH', 'advice': 'Vision changes may signal dangerously high blood pressure. Go to the hospital immediately.'},
    'convulsions': {'score': 10, 'level': 'CRITICAL', 'advice': 'EMERGENCY: Place the patient on their side, clear the airway, do NOT put anything in the mouth. Call emergency services immediately.'},
    'seizure': {'score': 10, 'level': 'CRITICAL', 'advice': 'EMERGENCY: Protect the patient from injury, place on side, call emergency services immediately.'},
    'unconscious': {'score': 10, 'level': 'CRITICAL', 'advice': 'EMERGENCY: Check breathing, place in recovery position, call emergency services immediately.'},
    'chest pain': {'score': 8, 'level': 'HIGH', 'advice': 'Chest pain during pregnancy requires immediate evaluation. Go to the nearest hospital.'},
    'difficulty breathing': {'score': 8, 'level': 'HIGH', 'advice': 'Sit upright, loosen clothing, and seek immediate medical attention.'},
    'high fever': {'score': 7, 'level': 'HIGH', 'advice': 'Fever above 100.4°F (38°C) needs medical attention. Cool the patient with damp cloths and give fluids.'},
    'fever': {'score': 6, 'level': 'MEDIUM', 'advice': 'Monitor temperature closely. Give fluids and rest. If fever persists beyond 24 hours, visit a health center.'},
    'no fetal movement': {'score': 8, 'level': 'HIGH', 'advice': 'Drink cold water, lie on your left side for 1 hour. If fewer than 10 movements in 2 hours, go to the hospital.'},
    'baby not moving': {'score': 8, 'level': 'HIGH', 'advice': 'Drink cold water, lie on your left side for 1 hour. If fewer than 10 movements in 2 hours, go to the hospital.'},
    'water breaking': {'score': 7, 'level': 'HIGH', 'advice': 'Note the time and color of the fluid. Go to the hospital. Do NOT insert anything. If fluid is green/brown, this is urgent.'},

    # Medium-risk symptoms
    'swelling': {'score': 5, 'level': 'MEDIUM', 'advice': 'Some swelling is normal except in face/hands. Elevate legs, reduce salt. If sudden or severe, consult a doctor.'},
    'headache': {'score': 5, 'level': 'MEDIUM', 'advice': 'Rest in a quiet dark room, drink water. If persistent or severe, check blood pressure and consult a doctor.'},
    'abdominal pain': {'score': 6, 'level': 'MEDIUM', 'advice': 'Note the location and intensity. If pain is regular, increasing, or accompanied by bleeding, seek medical help.'},
    'vomiting': {'score': 4, 'level': 'MEDIUM', 'advice': 'Stay hydrated with small sips. Eat bland foods. If unable to keep fluids down for 12+ hours, seek medical help.'},
    'nausea': {'score': 3, 'level': 'LOW', 'advice': 'Eat small frequent meals, avoid strong smells, try ginger tea. This is common but tell your doctor at next visit.'},
    'dizziness': {'score': 5, 'level': 'MEDIUM', 'advice': 'Sit or lie down immediately. Drink water. Avoid standing up quickly. If frequent, check blood pressure and hemoglobin.'},
    'back pain': {'score': 3, 'level': 'LOW', 'advice': 'Try warm compresses, gentle stretching, and proper posture. Avoid heavy lifting. Mention at next checkup.'},
    'fatigue': {'score': 2, 'level': 'LOW', 'advice': 'Rest when possible, eat iron-rich foods, stay hydrated. Some fatigue is normal but mention persistent exhaustion to your doctor.'},
    'itching': {'score': 4, 'level': 'MEDIUM', 'advice': 'Mild itching is normal. Severe itching especially on palms/soles could indicate a liver condition — see a doctor.'},
    'constipation': {'score': 2, 'level': 'LOW', 'advice': 'Increase fiber intake, drink plenty of water, and stay active. Prunes and leafy greens help.'},
    'frequent urination': {'score': 2, 'level': 'LOW', 'advice': 'This is common. If accompanied by burning or pain, it could be an infection — see a doctor.'},
    'burning urination': {'score': 5, 'level': 'MEDIUM', 'advice': 'This may indicate a urinary tract infection. Drink plenty of water and see a doctor for treatment.'},
}

NUTRITION_DATABASE = {
    'rice': {'calories': 130, 'iron_mg': 0.2, 'calcium_mg': 10, 'protein_g': 2.7, 'folic_acid_mcg': 3},
    'roti': {'calories': 120, 'iron_mg': 1.0, 'calcium_mg': 10, 'protein_g': 3.1, 'folic_acid_mcg': 10},
    'chapati': {'calories': 120, 'iron_mg': 1.0, 'calcium_mg': 10, 'protein_g': 3.1, 'folic_acid_mcg': 10},
    'dal': {'calories': 105, 'iron_mg': 1.9, 'calcium_mg': 19, 'protein_g': 7.0, 'folic_acid_mcg': 36},
    'lentils': {'calories': 116, 'iron_mg': 3.3, 'calcium_mg': 19, 'protein_g': 9.0, 'folic_acid_mcg': 181},
    'egg': {'calories': 78, 'iron_mg': 0.9, 'calcium_mg': 28, 'protein_g': 6.3, 'folic_acid_mcg': 24},
    'milk': {'calories': 61, 'iron_mg': 0.03, 'calcium_mg': 125, 'protein_g': 3.2, 'folic_acid_mcg': 5},
    'curd': {'calories': 61, 'iron_mg': 0.05, 'calcium_mg': 110, 'protein_g': 3.5, 'folic_acid_mcg': 7},
    'yogurt': {'calories': 61, 'iron_mg': 0.05, 'calcium_mg': 110, 'protein_g': 3.5, 'folic_acid_mcg': 7},
    'banana': {'calories': 89, 'iron_mg': 0.3, 'calcium_mg': 5, 'protein_g': 1.1, 'folic_acid_mcg': 20},
    'apple': {'calories': 52, 'iron_mg': 0.1, 'calcium_mg': 6, 'protein_g': 0.3, 'folic_acid_mcg': 3},
    'spinach': {'calories': 23, 'iron_mg': 2.7, 'calcium_mg': 99, 'protein_g': 2.9, 'folic_acid_mcg': 194},
    'palak': {'calories': 23, 'iron_mg': 2.7, 'calcium_mg': 99, 'protein_g': 2.9, 'folic_acid_mcg': 194},
    'chicken': {'calories': 165, 'iron_mg': 0.9, 'calcium_mg': 15, 'protein_g': 31.0, 'folic_acid_mcg': 4},
    'fish': {'calories': 136, 'iron_mg': 0.5, 'calcium_mg': 15, 'protein_g': 20.0, 'folic_acid_mcg': 7},
    'paneer': {'calories': 265, 'iron_mg': 0.2, 'calcium_mg': 208, 'protein_g': 18.3, 'folic_acid_mcg': 40},
    'beetroot': {'calories': 43, 'iron_mg': 0.8, 'calcium_mg': 16, 'protein_g': 1.6, 'folic_acid_mcg': 109},
    'carrot': {'calories': 41, 'iron_mg': 0.3, 'calcium_mg': 33, 'protein_g': 0.9, 'folic_acid_mcg': 19},
    'sweet potato': {'calories': 86, 'iron_mg': 0.6, 'calcium_mg': 30, 'protein_g': 1.6, 'folic_acid_mcg': 11},
    'dates': {'calories': 282, 'iron_mg': 1.0, 'calcium_mg': 39, 'protein_g': 2.5, 'folic_acid_mcg': 19},
    'jaggery': {'calories': 383, 'iron_mg': 11.0, 'calcium_mg': 80, 'protein_g': 0.4, 'folic_acid_mcg': 18},
    'ragi': {'calories': 328, 'iron_mg': 3.9, 'calcium_mg': 344, 'protein_g': 7.3, 'folic_acid_mcg': 18},
    'drumstick': {'calories': 37, 'iron_mg': 0.4, 'calcium_mg': 30, 'protein_g': 2.1, 'folic_acid_mcg': 44},
    'coconut': {'calories': 354, 'iron_mg': 2.4, 'calcium_mg': 14, 'protein_g': 3.3, 'folic_acid_mcg': 26},
    'peanuts': {'calories': 567, 'iron_mg': 4.6, 'calcium_mg': 92, 'protein_g': 25.8, 'folic_acid_mcg': 240},
    'almonds': {'calories': 579, 'iron_mg': 3.7, 'calcium_mg': 269, 'protein_g': 21.2, 'folic_acid_mcg': 44},
    'iron tablet': {'calories': 0, 'iron_mg': 60.0, 'calcium_mg': 0, 'protein_g': 0, 'folic_acid_mcg': 500},
    'calcium tablet': {'calories': 0, 'iron_mg': 0, 'calcium_mg': 500, 'protein_g': 0, 'folic_acid_mcg': 0},
    'prenatal vitamin': {'calories': 0, 'iron_mg': 27.0, 'calcium_mg': 200, 'protein_g': 0, 'folic_acid_mcg': 800},
}

# Daily Recommended Intake for pregnant women
DAILY_REQUIREMENTS = {
    'calories': 2500,
    'iron_mg': 27,
    'calcium_mg': 1000,
    'protein_g': 71,
    'folic_acid_mcg': 600,
}

# ──────────────────────────────────────────────
# AI CHAT ENGINE (Keyword-based NLP simulation)
# ──────────────────────────────────────────────

CHAT_KNOWLEDGE = {
    'diet': "During pregnancy, focus on iron-rich foods (spinach, lentils, jaggery), calcium (milk, ragi, paneer), protein (eggs, dal, fish), and folic acid (leafy greens, peanuts). Eat 5-6 small meals daily. Stay hydrated with 8-10 glasses of water.",
    'food': "During pregnancy, focus on iron-rich foods (spinach, lentils, jaggery), calcium (milk, ragi, paneer), protein (eggs, dal, fish), and folic acid (leafy greens, peanuts). Eat 5-6 small meals daily. Stay hydrated with 8-10 glasses of water.",
    'nutrition': "During pregnancy, focus on iron-rich foods (spinach, lentils, jaggery), calcium (milk, ragi, paneer), protein (eggs, dal, fish), and folic acid (leafy greens, peanuts). Eat 5-6 small meals daily. Stay hydrated with 8-10 glasses of water.",
    'exercise': "Light exercise like walking for 30 minutes daily is beneficial. Avoid heavy lifting and strenuous activities. Prenatal yoga and breathing exercises can help with labor preparation. Always consult your doctor before starting any exercise routine.",
    'sleep': "Sleep on your left side for better blood flow to the baby. Use pillows for support. Aim for 8-9 hours of sleep. Avoid sleeping on your back in the third trimester.",
    'checkup': "Regular antenatal checkups are crucial: Monthly visits until week 28, bi-weekly until week 36, then weekly until delivery. Each visit should include: weight, blood pressure, urine test, and fetal heartbeat check.",
    'vaccination': "Important vaccines during pregnancy: Tetanus Toxoid (TT) — two doses. Tdap vaccine between weeks 27-36. Flu vaccine is safe and recommended. COVID-19 vaccination is also recommended.",
    'emergency': "Go to the hospital IMMEDIATELY if you experience: heavy bleeding, severe headache with vision changes, convulsions, baby not moving, water breaking before 37 weeks, or high fever. Always keep your hospital bag ready after week 36.",
    'labor': "Signs of labor include: regular contractions getting closer together, water breaking, bloody mucus discharge, and lower back pain. Time your contractions. Go to hospital when contractions are 5 minutes apart, lasting 1 minute, for 1 hour.",
    'breastfeeding': "Start breastfeeding within 1 hour of birth. Feed exclusively for 6 months. Feed on demand, at least 8-12 times daily. Proper latching is key — the baby should take the entire areola, not just the nipple.",
    'mental health': "Mood changes are normal during pregnancy. Talk to someone you trust about how you feel. If you experience persistent sadness, anxiety, or loss of interest for more than 2 weeks, seek professional help. You are not alone.",
    'danger signs': "Danger signs to watch for: vaginal bleeding, severe headaches, blurred vision, swelling of face/hands, high fever, reduced fetal movement, convulsions, and severe abdominal pain. Seek immediate medical care for any of these.",
    'medicine': "Never take any medication without consulting your doctor. Continue iron and folic acid supplements as prescribed. Avoid self-medication including traditional/herbal remedies without medical advice.",
    'water': "Drink 8-10 glasses of water daily. Proper hydration helps prevent UTIs, constipation, and supports amniotic fluid levels. Increase intake in hot weather or if you're active.",
    'weight': "Normal weight gain during pregnancy: 11-16 kg total. First trimester: 1-2 kg. Second and third trimester: about 0.5 kg per week. Sudden weight gain could indicate preeclampsia — report to your doctor.",
    'baby development': "Your baby goes through amazing changes! Month 1-3: organs form. Month 4-6: baby kicks, hair grows, eyes open. Month 7-9: lungs mature, baby gains weight, prepares for birth. Regular checkups track healthy development.",
}


def get_chat_response(message, language='en'):
    # If not en, translate to English to check keywords
    if language != 'en':
        try:
            # We translate to English to map with our CHAT_KNOWLEDGE
            english_message = GoogleTranslator(source='auto', target='en').translate(message)
        except Exception:
            english_message = message
    else:
        english_message = message

    english_message_lower = english_message.lower()
    response_text = None
    
    for keyword, response in CHAT_KNOWLEDGE.items():
        if keyword in english_message_lower:
            response_text = response
            break

    if not response_text:
        response_text = ("Thank you for your question. For the best guidance, I recommend discussing this with your healthcare provider at your next visit. "
                         "In the meantime, you can ask me about: diet, exercise, sleep, checkups, vaccinations, danger signs, labor signs, breastfeeding, or mental health during pregnancy.")

    # Translate back to native language
    if language != 'en':
        try:
            # deep-translator maps 'ml-IN' to 'ml' or 'hi-IN' to 'hi' automatically or we can strip suffix
            lang_code = language.split('-')[0]
            native_response = GoogleTranslator(source='en', target=lang_code).translate(response_text)
            return native_response
        except Exception as e:
            print("Translation error:", e)
            return response_text
    return response_text


def assess_risk(symptoms_text):
    symptoms_lower = symptoms_text.lower()
    detected = []
    total_score = 0
    max_level = 'LOW'
    all_advice = []
    level_priority = {'LOW': 1, 'MEDIUM': 2, 'HIGH': 3, 'CRITICAL': 4}

    for symptom, data in SYMPTOM_RISK_MAP.items():
        if symptom in symptoms_lower:
            detected.append(symptom)
            total_score += data['score']
            all_advice.append(f"**{symptom.title()}**: {data['advice']}")
            if level_priority.get(data['level'], 0) > level_priority.get(max_level, 0):
                max_level = data['level']

    if not detected:
        return {
            'risk_level': 'LOW',
            'risk_score': 0,
            'detected_symptoms': [],
            'recommendations': 'No specific risk symptoms detected. Continue regular checkups and maintain a healthy routine. If you feel unwell, please describe your symptoms in more detail.',
        }

    return {
        'risk_level': max_level,
        'risk_score': min(total_score, 10),
        'detected_symptoms': detected,
        'recommendations': '\n\n'.join(all_advice),
    }


# ──────────────────────────────────────────────
# API ROUTES
# ──────────────────────────────────────────────

@app.route('/api/user', methods=['GET'])
def get_user():
    db = get_db()
    user = db.execute('SELECT * FROM users WHERE id = 1').fetchone()
    db.close()
    if user:
        return jsonify(dict(user))
    return jsonify({'error': 'No user found'}), 404


@app.route('/api/user', methods=['PUT'])
def update_user():
    data = request.json
    db = get_db()
    db.execute('''
        UPDATE users SET name=?, age=?, weeks_pregnant=?, blood_group=?, phone=?, village=?
        WHERE id = 1
    ''', (data.get('name'), data.get('age'), data.get('weeks_pregnant'),
          data.get('blood_group'), data.get('phone'), data.get('village')))
    db.commit()
    db.close()
    return jsonify({'success': True})


@app.route('/api/chat', methods=['POST'])
def chat():
    data = request.json
    message = data.get('message', '')
    language = data.get('language', 'en')
    response = get_chat_response(message, language)

    db = get_db()
    db.execute('INSERT INTO chat_history (message, response) VALUES (?, ?)', (message, response))
    db.commit()
    db.close()

    return jsonify({'message': message, 'response': response, 'language': language})


@app.route('/api/chat/history', methods=['GET'])
def chat_history():
    db = get_db()
    rows = db.execute('SELECT * FROM chat_history ORDER BY created_at DESC LIMIT 50').fetchall()
    db.close()
    return jsonify([dict(r) for r in rows])


@app.route('/api/assess-risk', methods=['POST'])
def risk_assessment():
    data = request.json
    symptoms = data.get('symptoms', '')
    result = assess_risk(symptoms)

    db = get_db()
    db.execute('''
        INSERT INTO health_logs (symptoms, risk_level, risk_score, recommendations)
        VALUES (?, ?, ?, ?)
    ''', (symptoms, result['risk_level'], result['risk_score'], result['recommendations']))
    db.commit()
    db.close()

    return jsonify(result)


@app.route('/api/risk-history', methods=['GET'])
def risk_history():
    db = get_db()
    rows = db.execute('SELECT * FROM health_logs ORDER BY created_at DESC LIMIT 20').fetchall()
    db.close()
    return jsonify([dict(r) for r in rows])


@app.route('/api/nutrition', methods=['GET'])
def get_nutrition():
    target_date = request.args.get('date', date.today().isoformat())
    db = get_db()
    rows = db.execute('SELECT * FROM nutrition_logs WHERE logged_date = ? ORDER BY created_at DESC', (target_date,)).fetchall()
    db.close()

    logs = [dict(r) for r in rows]
    totals = {'calories': 0, 'iron_mg': 0, 'calcium_mg': 0, 'protein_g': 0, 'folic_acid_mcg': 0}
    for log in logs:
        totals['calories'] += log.get('calories', 0)
        totals['iron_mg'] += log.get('iron_mg', 0)
        totals['calcium_mg'] += log.get('calcium_mg', 0)
        totals['protein_g'] += log.get('protein_g', 0)
        totals['folic_acid_mcg'] += log.get('folic_acid_mcg', 0)

    deficiencies = []
    for nutrient, required in DAILY_REQUIREMENTS.items():
        current = totals.get(nutrient, 0)
        pct = (current / required) * 100 if required > 0 else 0
        if pct < 50:
            deficiencies.append({'nutrient': nutrient, 'current': round(current, 1), 'required': required, 'percentage': round(pct, 1)})

    suggestions = []
    for d in deficiencies:
        n = d['nutrient']
        if n == 'iron_mg':
            suggestions.append('Add iron-rich foods: spinach (palak), lentils (dal), jaggery, beetroot, dates, or ragi porridge.')
        elif n == 'calcium_mg':
            suggestions.append('Add calcium-rich foods: milk, curd/yogurt, ragi, paneer, or drumstick leaves.')
        elif n == 'protein_g':
            suggestions.append('Add protein-rich foods: eggs, dal, chicken, fish, paneer, or peanuts.')
        elif n == 'folic_acid_mcg':
            suggestions.append('Add folate-rich foods: spinach, lentils, peanuts, beetroot, or take your prenatal vitamin.')
        elif n == 'calories':
            suggestions.append('You need more calories. Add an extra meal or snack: banana with peanut butter, ragi porridge, or a handful of nuts.')

    return jsonify({
        'logs': logs,
        'totals': totals,
        'requirements': DAILY_REQUIREMENTS,
        'deficiencies': deficiencies,
        'suggestions': suggestions,
    })


@app.route('/api/nutrition', methods=['POST'])
def add_nutrition():
    data = request.json
    food_item = data.get('food_item', '').lower().strip()
    meal_type = data.get('meal_type', 'other')

    # Look up nutrition data
    nutrition = NUTRITION_DATABASE.get(food_item, {
        'calories': 100, 'iron_mg': 0.5, 'calcium_mg': 20, 'protein_g': 2.0, 'folic_acid_mcg': 10
    })

    db = get_db()
    db.execute('''
        INSERT INTO nutrition_logs (food_item, meal_type, calories, iron_mg, calcium_mg, protein_g, folic_acid_mcg)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (food_item, meal_type, nutrition['calories'], nutrition['iron_mg'],
          nutrition['calcium_mg'], nutrition['protein_g'], nutrition['folic_acid_mcg']))
    db.commit()
    db.close()

    return jsonify({
        'success': True,
        'food_item': food_item,
        'nutrition': nutrition,
        'message': f'Logged {food_item} ({meal_type})'
    })


@app.route('/api/nutrition/search', methods=['GET'])
def search_nutrition():
    query = request.args.get('q', '').lower()
    results = {k: v for k, v in NUTRITION_DATABASE.items() if query in k}
    return jsonify(results)


@app.route('/api/reminders', methods=['GET'])
def get_reminders():
    db = get_db()
    rows = db.execute('SELECT * FROM reminders ORDER BY is_completed ASC, due_date ASC, due_time ASC').fetchall()
    db.close()
    return jsonify([dict(r) for r in rows])


@app.route('/api/reminders', methods=['POST'])
def add_reminder():
    data = request.json
    db = get_db()
    db.execute('''
        INSERT INTO reminders (title, description, reminder_type, due_date, due_time)
        VALUES (?, ?, ?, ?, ?)
    ''', (data.get('title'), data.get('description'), data.get('reminder_type', 'medication'),
          data.get('due_date'), data.get('due_time')))
    db.commit()
    db.close()
    return jsonify({'success': True})


@app.route('/api/reminders/<int:reminder_id>/complete', methods=['PUT'])
def complete_reminder(reminder_id):
    db = get_db()
    db.execute('UPDATE reminders SET is_completed = 1 WHERE id = ?', (reminder_id,))
    db.commit()
    db.close()
    return jsonify({'success': True})


@app.route('/api/reminders/<int:reminder_id>', methods=['DELETE'])
def delete_reminder(reminder_id):
    db = get_db()
    db.execute('DELETE FROM reminders WHERE id = ?', (reminder_id,))
    db.commit()
    db.close()
    return jsonify({'success': True})


@app.route('/api/dashboard', methods=['GET'])
def dashboard():
    db = get_db()
    user = db.execute('SELECT * FROM users WHERE id = 1').fetchone()
    upcoming_reminders = db.execute(
        'SELECT * FROM reminders WHERE is_completed = 0 ORDER BY due_date ASC LIMIT 5'
    ).fetchall()
    recent_risk = db.execute(
        'SELECT * FROM health_logs ORDER BY created_at DESC LIMIT 1'
    ).fetchone()
    today_nutrition = db.execute(
        'SELECT SUM(calories) as cal, SUM(iron_mg) as iron, SUM(calcium_mg) as calcium, '
        'SUM(protein_g) as protein, SUM(folic_acid_mcg) as folic '
        'FROM nutrition_logs WHERE logged_date = ?',
        (date.today().isoformat(),)
    ).fetchone()
    db.close()

    return jsonify({
        'user': dict(user) if user else None,
        'upcoming_reminders': [dict(r) for r in upcoming_reminders],
        'recent_risk': dict(recent_risk) if recent_risk else None,
        'today_nutrition': {
            'calories': today_nutrition['cal'] or 0,
            'iron_mg': today_nutrition['iron'] or 0,
            'calcium_mg': today_nutrition['calcium'] or 0,
            'protein_g': today_nutrition['protein'] or 0,
            'folic_acid_mcg': today_nutrition['folic'] or 0,
        } if today_nutrition else None,
        'requirements': DAILY_REQUIREMENTS,
    })


@app.route('/api/emergency-steps', methods=['GET'])
def emergency_steps():
    lang = request.args.get('lang', 'en')
    
    # Pre-built rural-focused emergency guidance scenarios
    scenarios = [
        {
            'id': 'bleeding',
            'title': 'Heavy Bleeding',
            'icon': '🩸',
            'severity': 'CRITICAL',
            'steps': [
                {'step': 1, 'instruction': 'Lay the mother flat on the floor', 'detail': 'Keep her calmly lying down. If possible, elevate her legs slightly on folded clothes or pillows.'},
                {'step': 2, 'instruction': 'Apply continuous firm pressure', 'detail': 'Use the cleanest available cotton cloths (boiled if possible, but immediate clean pads are priority). Press firmly on the bleeding source. Do not remove soaked cloths, just stack new ones.'},
                {'step': 3, 'instruction': 'Send someone to find an ASHA worker or vehicle', 'detail': 'Immediately dispatch a family member to bring the village ASHA worker or secure a local jeep/tempo. Do not wait for an ambulance if roads are poor.'},
                {'step': 4, 'instruction': 'Keep the mother warm and hydrated', 'detail': 'Cover her with a blanket to prevent shock. If she is fully conscious, offer small sips of clean water.'},
            ]
        },
        {
            'id': 'convulsions',
            'title': 'Fits / Convulsions',
            'icon': '⚡',
            'severity': 'CRITICAL',
            'steps': [
                {'step': 1, 'instruction': 'Clear the floor space safely', 'detail': 'Do not hold the mother down. Move pots, sharp objects, or fire sources away from her. Let the seizure pass naturally.'},
                {'step': 2, 'instruction': 'Turn her onto her LEFT side', 'detail': 'Gently roll her onto her left side as soon as it is safe to do so. This prevents choking and improves blood flow to the baby.'},
                {'step': 3, 'instruction': 'Nothing in the mouth', 'detail': 'Do NOT put spoons, herbs, or hands in her mouth. She will not swallow her tongue.'},
                {'step': 4, 'instruction': 'Arrange immediate transport', 'detail': 'This is eclampsia. Seek the fastest local transport to the nearest PHC (Primary Health Centre) immediately after the fit stops.'},
            ]
        },
        {
            'id': 'labor',
            'title': 'Unexpected Labor at Home',
            'icon': '👶',
            'severity': 'HIGH',
            'steps': [
                {'step': 1, 'instruction': 'Call ASHA or Midwife', 'detail': 'Send someone immediately to fetch the local birth attendant or ASHA worker.'},
                {'step': 2, 'instruction': 'Prepare a clean birth area', 'detail': 'Wash your hands thoroughly with soap. Lay clean sheets or large plastic/cloth on the floor.'},
                {'step': 3, 'instruction': 'Support the mother', 'detail': 'Help her into a squatting or semi-sitting position. Encourage her to take slow breaths.'},
                {'step': 4, 'instruction': 'Catch the baby gently', 'detail': 'When the head appears, support it gently. Do NOT pull the baby.'},
                {'step': 5, 'instruction': 'Keep baby skin-to-skin', 'detail': 'Place the baby immediately on the mother\'s bare chest and cover both with a warm cloth.'},
                {'step': 6, 'instruction': 'Do NOT cut the cord', 'detail': 'Wait for the placenta to naturally deliver. Leave the cord attached until the professional arrives or transport is secured.'},
            ]
        },
        {
            'id': 'breathing',
            'title': 'Severe Breathing Difficulty',
            'icon': '😮‍💨',
            'severity': 'HIGH',
            'steps': [
                {'step': 1, 'instruction': 'Sit upright immediately', 'detail': 'Help the mother sit up straight against a wall or propped with pillows. Lying flat makes it worse.'},
                {'step': 2, 'instruction': 'Provide fresh air', 'detail': 'Open windows or doors. Loosen any tight clothing around the chest or waist.'},
                {'step': 3, 'instruction': 'Calm breathing', 'detail': 'Ask her to breathe in through the nose slowly and blow out through the mouth like whistling.'},
                {'step': 4, 'instruction': 'Seek transport', 'detail': 'If her lips or nails turn blue, or breathing doesn\'t ease in 5 minutes, move to the nearest clinic.'},
            ]
        }
    ]

    # Translate the scenarios if language is not English
    if lang != 'en':
        lang_code = lang.split('-')[0]
        try:
            for scenario in scenarios:
                scenario['title'] = GoogleTranslator(source='en', target=lang_code).translate(scenario['title'])
                for step in scenario['steps']:
                    step['instruction'] = GoogleTranslator(source='en', target=lang_code).translate(step['instruction'])
                    step['detail'] = GoogleTranslator(source='en', target=lang_code).translate(step['detail'])
        except Exception as e:
            print("Translation Error for Emergency Steps:", e)

    return jsonify(scenarios)

@app.route('/api/emergency/search', methods=['GET'])
def search_emergency():
    query = request.args.get('query', '').lower()
    lang = request.args.get('lang', 'en')
    
    if not query:
        return jsonify({'matched_id': None})
        
    # Translate query to English if needed
    if lang and not lang.startswith('en'):
        try:
            english_query = GoogleTranslator(source='auto', target='en').translate(query).lower()
        except Exception:
            english_query = query
    else:
        english_query = query
        
    if any(word in english_query for word in ['bleed', 'blood']):
        return jsonify({'matched_id': 'bleeding'})
    elif any(word in english_query for word in ['labor', 'birth', 'baby', 'water']):
        return jsonify({'matched_id': 'labor'})
    elif any(word in english_query for word in ['breath', 'air', 'chok', 'asthma']):
        return jsonify({'matched_id': 'breathing'})
    elif any(word in english_query for word in ['fit', 'seizure', 'shake', 'shaking', 'convul']):
        return jsonify({'matched_id': 'convulsions'})
        
    return jsonify({'matched_id': None})



if __name__ == '__main__':
    init_db()
    print("Database initialized")
    print("Starting Maternal Healthcare API Server...")
    app.run(debug=True, port=5000)
