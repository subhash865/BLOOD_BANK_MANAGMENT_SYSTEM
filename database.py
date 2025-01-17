import psycopg2
from psycopg2 import OperationalError

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

def get_all_persons():
    conn = get_db_connection()
    if conn:
        cur = conn.cursor()
        cur.execute('''
            SELECT p.PERSON_ID, p.NAME, p.DATE_OF_BIRTH, p.AGE, p.GENDER, p.BLOOD_GROUP, 
                   CONCAT(p.D_NO, ' ', p.STREET_NAME, ' ', p.STREET_NO, ' ', p.APT_NUMBER) AS ADDRESS, 
                   p.CITY, p.STATE, COALESCE(c.CONTACT, 'N/A') AS CONTACT
            FROM PERSON p
            LEFT JOIN CONTACT_INFO c ON p.PERSON_ID = c.PERSON_ID
        ''')
        persons = cur.fetchall()
        cur.close()
        conn.close()
        return persons
    else:
        return None

def get_all_donors():
    conn = get_db_connection()
    if conn:
        cur = conn.cursor()
        cur.execute('''
            SELECT d.DONOR_ID, p.NAME, p.BLOOD_GROUP, c.CONTACT, d.DONATION_DATE, d.TAKING_QUANTITY, dn.BRANCH_ID
            FROM DONOR d
            JOIN PERSON p ON d.PERSON_ID = p.PERSON_ID
            LEFT JOIN CONTACT_INFO c ON p.PERSON_ID = c.PERSON_ID
            LEFT JOIN DONATES dn ON d.DONOR_ID = dn.DONOR_ID
        ''')
        donors = cur.fetchall()
        cur.close()
        conn.close()
        return donors
    else:
        return None

def get_all_recipients():
    conn = get_db_connection()
    if conn:
        cur = conn.cursor()
        cur.execute('''
            SELECT r.RECIPIENT_ID, p.NAME, p.BLOOD_GROUP, c.CONTACT, r.RECEIVED_DATE, r.RECEIVING_QUANTITY, rc.BRANCH_ID
            FROM RECIPIENT r
            JOIN PERSON p ON r.PERSON_ID = p.PERSON_ID
            LEFT JOIN CONTACT_INFO c ON p.PERSON_ID = c.PERSON_ID
            LEFT JOIN RECEIVES rc ON r.RECIPIENT_ID = rc.RECIPIENT_ID
        ''')
        recipients = cur.fetchall()
        cur.close()
        conn.close()
        return recipients
    else:
        return None
