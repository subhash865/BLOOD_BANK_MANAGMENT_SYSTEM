from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
import psycopg2
from psycopg2 import OperationalError
from database import get_all_persons, get_all_donors, get_all_recipients

app = Flask(__name__)
app.secret_key = 'your_secret_key'

def get_db_connection():
    try:
        conn = psycopg2.connect(
            dbname="bloodbank",
            user="postgres",
            password="12345678",
            host="localhost",
            port="5432"
        )
        return conn
    except OperationalError as e:
        print(f"Error: {e}")
        return None

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/new-user', methods=['GET', 'POST'])
def new_user():
    if request.method == 'POST':
        aadhaar_number = request.form['aadhaar_number']
        name = request.form['name']
        date_of_birth = request.form['date_of_birth']
        age = request.form['age']
        gender = request.form['gender']
        blood_group = request.form['blood_group']
        d_no = request.form['d_no']
        street_name = request.form['street_name']
        street_no = request.form['street_no']
        apt_number = request.form['apt_number']
        city = request.form['city']
        state = request.form['state']
        contact_number = request.form['contact_number']

        conn = get_db_connection()
        if conn:
            cur = conn.cursor()
            cur.execute('''
                INSERT INTO PERSON (AADHAAR_NUMBER, NAME, DATE_OF_BIRTH, AGE, GENDER, BLOOD_GROUP, D_NO, STREET_NAME, STREET_NO, APT_NUMBER, CITY, STATE)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING PERSON_ID
            ''', (aadhaar_number, name, date_of_birth, age, gender, blood_group, d_no, street_name, street_no, apt_number, city, state))
            person_id = cur.fetchone()[0]
            
            cur.execute('''
                INSERT INTO CONTACT_INFO (PERSON_ID, CONTACT)
                VALUES (%s, %s)
            ''', (person_id, contact_number))
            
            conn.commit()
            cur.close()
            conn.close()
            flash('Values inserted successfully!')
            return redirect(url_for('new_user'))
        else:
            return "Database connection failed", 500
    return render_template('newuser.html')

@app.route('/old-user')
def old_user():
    return render_template('olduser.html')

@app.route('/view-details')
def view_details():
    return render_template('viewdetails.html')

@app.route('/donor', methods=['GET', 'POST'])
def donor():
    if request.method == 'POST':
        person_id = request.form['person_id']
        donation_date = request.form['donation_date']
        taking_quantity = request.form['taking_quantity']
        branch_id = request.form['branch_id']
        blood_group = request.form.get('blood_group')  # Use request.form.get to avoid KeyError

        if not blood_group:
            flash('Blood group is required. Please fetch the blood type before submitting.')
            return redirect(url_for('donor'))

        conn = get_db_connection()
        if conn:
            cur = conn.cursor()
            try:
                cur.execute('''
                    INSERT INTO DONOR (PERSON_ID, DONATION_DATE, TAKING_QUANTITY)
                    VALUES (%s, %s, %s)
                    RETURNING DONOR_ID
                ''', (person_id, donation_date, taking_quantity))
                donor_id = cur.fetchone()[0]
                
                cur.execute('''
                    INSERT INTO DONATES (DONOR_ID, BRANCH_ID)
                    VALUES (%s, %s)
                ''', (donor_id, branch_id))
                
                cur.execute('''
                    INSERT INTO STORAGE (BRANCH_ID, BLOOD_GROUP, STORAGE_QUANTITY)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (BRANCH_ID, BLOOD_GROUP) DO UPDATE
                    SET STORAGE_QUANTITY = STORAGE.STORAGE_QUANTITY + EXCLUDED.STORAGE_QUANTITY
                ''', (branch_id, blood_group, taking_quantity))
                
                conn.commit()
                flash('Donor information, branch association, and storage update inserted successfully!')
            except psycopg2.errors.CheckViolation as e:
                conn.rollback()
                flash(f'Error: {e.pgerror}')
            finally:
                cur.close()
                conn.close()
            return redirect(url_for('donor'))
        else:
            return "Database connection failed", 500
    return render_template('donor.html')

@app.route('/recipient', methods=['GET', 'POST'])
def recipient():
    if request.method == 'POST':
        person_id = request.form['person_id']
        date_of_taking = request.form['date_of_taking']
        quantity = request.form['quantity']
        branch_id = request.form['branch_id']

        conn = get_db_connection()
        if conn:
            cur = conn.cursor()
            try:
                # Check if the required quantity is available in the storage
                cur.execute('''
                    SELECT STORAGE_QUANTITY FROM STORAGE
                    WHERE BRANCH_ID = %s AND BLOOD_GROUP = (
                        SELECT BLOOD_GROUP FROM PERSON WHERE PERSON_ID = %s
                    )
                ''', (branch_id, person_id))
                storage = cur.fetchone()
                
                if storage is None or storage[0] < float(quantity):
                    flash('Error: The required quantity is not available in the storage.')
                    return redirect(url_for('recipient'))

                cur.execute('''
                    INSERT INTO RECIPIENT (PERSON_ID, RECEIVING_QUANTITY, RECEIVED_DATE)
                    VALUES (%s, %s, %s)
                    RETURNING RECIPIENT_ID
                ''', (person_id, quantity, date_of_taking))
                recipient_id = cur.fetchone()[0]
                
                cur.execute('''
                    INSERT INTO RECEIVES (RECIPIENT_ID, BRANCH_ID)
                    VALUES (%s, %s)
                ''', (recipient_id, branch_id))
                
                cur.execute('''
                    UPDATE STORAGE
                    SET STORAGE_QUANTITY = STORAGE_QUANTITY - %s
                    WHERE BRANCH_ID = %s AND BLOOD_GROUP = (
                        SELECT BLOOD_GROUP FROM PERSON WHERE PERSON_ID = %s
                    )
                ''', (quantity, branch_id, person_id))
                
                conn.commit()
                flash('Recipient information, branch association, and storage update inserted successfully!')
            except psycopg2.errors.CheckViolation as e:
                conn.rollback()
                flash(f'Error: {e.pgerror}')
            finally:
                cur.close()
                conn.close()
            return redirect(url_for('recipient'))
        else:
            return "Database connection failed", 500
    return render_template('recipient.html')

@app.route('/total-persons')
def total_persons():
    persons = get_all_persons()
    if persons is not None:
        return render_template('total_persons.html', persons=persons)
    else:
        return "Database connection failed", 500

@app.route('/donors')
def donors():
    conn = get_db_connection()
    if conn:
        cur = conn.cursor()
        cur.execute('''
            SELECT d.DONOR_ID, p.NAME, p.BLOOD_GROUP, c.CONTACT, d.DONATION_DATE, d.TAKING_QUANTITY, b.BRANCH_ID
            FROM DONOR d
            JOIN PERSON p ON d.PERSON_ID = p.PERSON_ID
            JOIN CONTACT_INFO c ON p.PERSON_ID = c.PERSON_ID
            JOIN DONATES dn ON d.DONOR_ID = dn.DONOR_ID
            JOIN BLOOD_BANK_BRANCH b ON dn.BRANCH_ID = b.BRANCH_ID
        ''')
        donors = cur.fetchall()
        cur.close()
        conn.close()
        return render_template('donors.html', donors=donors)
    else:
        return "Database connection failed", 500

@app.route('/recipients')
def recipients():
    recipients = get_all_recipients()
    if recipients is not None:
        return render_template('recipients.html', recipients=recipients)
    else:
        return "Database connection failed", 500

@app.route('/blood-type/<int:person_id>')
def blood_type(person_id):
    conn = get_db_connection()
    if conn:
        cur = conn.cursor()
        cur.execute('SELECT BLOOD_GROUP FROM PERSON WHERE PERSON_ID = %s', (person_id,))
        blood_type = cur.fetchone()
        cur.close()
        conn.close()
        if blood_type:
            return blood_type[0]
        else:
            return "Person ID not found", 404
    else:
        return "Database connection failed", 500

@app.route('/get-blood-type/<int:person_id>', methods=['GET'])
def get_blood_type(person_id):
    conn = get_db_connection()
    if conn:
        cur = conn.cursor()
        cur.execute('SELECT BLOOD_GROUP FROM PERSON WHERE PERSON_ID = %s', (person_id,))
        blood_type = cur.fetchone()
        cur.close()
        conn.close()
        if blood_type:
            return jsonify({'blood_type': blood_type[0]})
        else:
            return jsonify({'error': 'Person ID not found'}), 404
    else:
        return jsonify({'error': 'Database connection failed'}), 500

@app.route('/storage/<int:branch_id>')
def storage(branch_id):
    conn = get_db_connection()
    if conn:
        cur = conn.cursor()
        cur.execute('''
            SELECT BLOOD_GROUP, STORAGE_QUANTITY
            FROM STORAGE
            WHERE BRANCH_ID = %s
        ''', (branch_id,))
        storage_details = cur.fetchall()
        cur.close()
        conn.close()
        return render_template('storage.html', storage_details=storage_details, branch_id=branch_id)
    else:
        return "Database connection failed", 500

if __name__ == '__main__':
    app.run(debug=True)
