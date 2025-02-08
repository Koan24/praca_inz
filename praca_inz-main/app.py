from flask import Flask, request, render_template, redirect, url_for, send_from_directory
from PIL import Image
from azure.storage.blob import BlobServiceClient
import psycopg2
import os
import uuid

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# Konfiguracja Azure Blob Storage
AZURE_STORAGE_CONNECTION_STRING = "DefaultEndpointsProtocol=https;AccountName=storagepunkty2025;AccountKey=9X9ILx4bq7cp79OrQTmYj1lC2afoGlTL9IX5oVLcNS+oEdYCBp4i7wOWdVk1dVRQbCS4900Nkb6a+AStjmu8dA==;EndpointSuffix=core.windows.net"
CONTAINER_NAME = "zdjecia"

blob_service_client = BlobServiceClient.from_connection_string(AZURE_STORAGE_CONNECTION_STRING)
container_client = blob_service_client.get_container_client(CONTAINER_NAME)

# konfiguracja postgres wraz z azure
DATABASE_URL = "dbname='punkty_wodowskazowe' user='postgres' password='1910$trzegoM' host='punkty-postgres.postgres.database.azure.com' sslmode='require'"

# # Konfiguracja folderu na zdjęcia
# UPLOAD_FOLDER = 'zdjecia'
# if not os.path.exists(UPLOAD_FOLDER):
#     os.makedirs(UPLOAD_FOLDER)
#
# @app.route('/')
# def wyswietl_zdjecie(filename):
#     return send_from_directory(UPLOAD_FOLDER, filename)
#
def sanitize_input(value):
    """
    Funkcja oczyszcza dane wejściowe z błędnych znaków.
    """
    if isinstance(value, str):
        return value.encode('utf-8', 'replace').decode('utf-8')
    return value

@app.route('/')
def index():
    # Pobranie istniejących punktów wodowskazowych z bazy danych
    try:
        # Połączenie z bazą danych
        conn = psycopg2.connect(DATABASE_URL, options='-c client_encoding=UTF8')
        cursor = conn.cursor()

        # Pobranie listy punktów wodowskazowych
        cursor.execute("SELECT id, nazwa FROM punkty_wodowskazowe;")
        rows = cursor.fetchall()

        # Oczyszczenie danych
        punkty = []
        for row in rows:
            try:
                punkty.append((row[0], sanitize_input(row[1])))
            except Exception as e:
                print(f"Błąd podczas oczyszczania danych: {row} - {e}")

        cursor.close()
        conn.close()

        return render_template('index.html', punkty=punkty)

    except Exception as e:
        print(f"Błąd ładowania punktów: {e}")
        return f"Wystąpił błąd podczas ładowania punktów: {str(e)}"

@app.route('/submit', methods=['POST'])
def submit():
    try:
        # Pobranie i sanityzacja danych z formularza
        punkt_id = sanitize_input(request.form['punkt_id'])
        data_pomiaru = sanitize_input(request.form['data_pomiaru'])
        autor = sanitize_input(request.form['autor'])
        dojscie = sanitize_input(request.form['dojscie'])
        mozliwosc_odczytu = sanitize_input(request.form['mozliwosc_odczytu'])
        poziom_wody = sanitize_input(request.form['poziom_wody'])
        print("Poziom wody z formularza:", poziom_wody)
        dokladny_pomiar = request.form.get('dokladny_pomiar')

        if dokladny_pomiar == "": #jesli jest puste
            dokladny_pomiar = None #czyli ze null
        uwagi = sanitize_input(request.form['uwagi'])

        lokalizacja = sanitize_input(request.form['lokalizacja'])
        zdjecie = request.files['zdjecie']

        if dokladny_pomiar:
            try:
                dokladny_pomiar = round(float(dokladny_pomiar), 2)
            except ValueError:
                dokladny_pomiar = None # ignoruj bledny format

        # Sprawdzenie poprawności formatu lokalizacji
        if not lokalizacja.startswith("POINT"):
            return "Nieprawidłowy format lokalizacji!", 400

        # Walidacja obowiazkowych pol
        if not punkt_id or not data_pomiaru or not autor or not zdjecie or not poziom_wody:
            return "Wszystkie wymagane pola muszą być wypełnione!", 400

        # Generowanie unikalnej nazwy pliku dla zdjęcia
        zdjecie_nazwa = f"{uuid.uuid4().hex}.jpg"
        # sciezka_zdjecia = os.path.join(UPLOAD_FOLDER, zdjecie_nazwa).replace("\\", "/")
        # sciezka_miniaturki = os.path.join(UPLOAD_FOLDER, f"thumb_{zdjecie_nazwa}")
        zdjecie_nazwa = f"{uuid.uuid4().hex}.jpg"

        # przesylanie zdjecia na Azure Blob Storage
        blob_client = container_client.get_blob_client(zdjecie_nazwa)
        blob_client.upload_blob(zdjecie, overwrite=True)

        # # Zapis oryginalnego zdjęcia
        # zdjecie.save(sciezka_zdjecia)
        #
        # # miniaturka
        # with Image.open(sciezka_zdjecia) as img:
        #     img.thumbnail((150, 150))  # Rozmiar miniaturki (150x150 px)
        #     img.save(sciezka_miniaturki)

        # zapis danych z formularza do bazdy danych
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO zgloszenia (punkt_id, data_pomiaru, autor, poziom_wody, dokladny_pomiar, dojscie, mozliwosc_odczytu, zdjecie, uwagi, lokalizacja)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, ST_GeomFromText(%s, 4326))
        """, (punkt_id, data_pomiaru, autor, poziom_wody, dokladny_pomiar, dojscie, mozliwosc_odczytu, zdjecie_nazwa, uwagi, lokalizacja))
        conn.commit()
        cursor.close()
        conn.close()

        # Przekierowanie na stronę sukcesu
        return redirect(url_for('success'))

    except Exception as e:
        print(f"Błąd: {str(e)}")
        return f"Wystąpił błąd podczas zapisywania danych. Spróbuj ponownie później."

@app.route('/zgloszenia')
def zgloszenia():
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, punkt_id, data_pomiaru, autor, poziom_wody, dokladny_pomiar, dojscie, mozliwosc_odczytu, uwagi, 
                   ST_AsText(lokalizacja) AS lokalizacja, zdjecie, dokladny_pomiar
            FROM zgloszenia;
        """)
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        return render_template('zgloszenia.html', zgloszenia=rows)
    except Exception as e:
        return f"Błąd: {e}"

@app.route('/success')
def success():
    return render_template('success.html')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))