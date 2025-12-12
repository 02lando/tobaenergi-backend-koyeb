# app.py
from flask import Flask, request, jsonify, render_template, send_file
from calculator import get_pvout_annual, calculate_solar_economics, PANEL_WATT_PEAK
import io
from fpdf import FPDF

app = Flask(__name__)


# Utility function
def format_rupiah(angka):
    try:
        return f"Rp {float(angka):,.0f}".replace(",", "_").replace(".", ",").replace("_", ".")
    except:
        return "Rp -"


# --- FUNGSI PEMBUAT PDF (SAFE) ---
def create_proposal_pdf(data):
    nama = data.get('nama', 'Pelanggan Yth.')
    coordinates = data.get('coordinates', '-')
    tagihan_listrik = data.get('tagihan_listrik', 0)
    penghematan_persen = data.get('penghematan_persen', 0)

    results = data.get('results', {})
    if not results or results.get('status') != 'success':
        raise Exception("Data perhitungan tidak valid.")

    # Ambil hasil
    TDL_USED = results.get('TDL_Used', 1699.53)
    PVOUT_ANNUAL = results.get('PVOut_Annual', 0)
    PVOUT_BULANAN_EFEKTIF = results.get('PVOUT_Bulanan_Efektif', 0)
    KEBUTUHAN_KWH = results.get('Kebutuhan_kWh_Bulanan', 0)
    KAPASITAS_KWP = results.get('Kapasitas_kWp', 0)
    JUMLAH_PANEL = results.get('Jumlah_Panel', 0)
    ESTIMASI_AREA = results.get('Estimasi_Area_m2', 0)
    TOTAL_INVESTASI = results.get('Total_Investasi', 0)
    PRODUKSI_KWH_BULANAN = results.get('Produksi_kWh_Bulanan', 0)
    PENGHEMATAN_BULANAN_RP = PRODUKSI_KWH_BULANAN * TDL_USED
    PENGHEMATAN_TAHUNAN_RP = results.get('Penghematan_Tahunan_Rp', 0)
    BEP_TAHUN = results.get('BEP_Tahun', 'Inf')
    LOSS_FACTOR_PERC = int(results.get('LOSS_FACTOR', 0.85) * 100)

    # Layout table widths (mm)
    W1 = 60.0
    W2 = 110.0

    def safe_text(text):
        return str(text).encode('latin-1', 'replace').decode('latin-1')

    pdf = FPDF(unit='mm', format='A4')
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font('Arial', 'B', 16)

    # Header
    pdf.set_fill_color(230, 230, 230)
    pdf.cell(0, 10, safe_text('PROPOSAL ESTIMASI KEBUTUHAN PLTS ATAP'), 0, 1, 'C', 1)
    pdf.ln(5)

    pdf.set_font('Arial', '', 11)
    pdf.cell(0, 5, safe_text(f'Yth. {nama}'), 0, 1)
    pdf.cell(0, 5, safe_text(f'di {coordinates}'), 0, 1)
    pdf.ln(5)

    # Body
    pdf.set_font('Arial', '', 10)
    pdf.multi_cell(0, 5, safe_text(f"Terima kasih atas ketertarikan Bapak/Ibu terhadap solusi Pembangkit Listrik Tenaga Surya (PLTS) Atap yang kami tawarkan. Kami menghargai kesempatan untuk membantu menganalisa kebutuhan energi dan potensi penghematan listrik di properti Bapak/Ibu."))
    pdf.ln(2)

    kebutuhan_str = f"Berdasarkan data input tagihan {format_rupiah(tagihan_listrik)} yang setara dengan konsumsi listrik sebesar {round(KEBUTUHAN_KWH, 2):,.2f} kWh per bulan, serta target penghematan sekitar {int(penghematan_persen)}%, kami telah melakukan perhitungan teknis menggunakan nilai irradiance dari PVGIS."
    pdf.multi_cell(0, 5, safe_text(kebutuhan_str))
    pdf.ln(2)

    pvout_str = f"Nilai PVOUT lokasi adalah {round(PVOUT_BULANAN_EFEKTIF, 4):,.4f} kWh/kWp per bulan (nilai ini sudah mempertimbangkan Performance Ratio/Loss Factor {LOSS_FACTOR_PERC}%), yang menjadi dasar penentuan estimasi kapasitas PLTS."
    pdf.multi_cell(0, 5, safe_text(pvout_str))
    pdf.ln(5)

    # Table
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 7, safe_text('HASIL ESTIMASI TEKNIS DAN FINANSIAL'), 0, 1, 'L')
    pdf.ln(2)

    def row(label, val, bold=False):
        pdf.set_font('Arial', 'B' if bold else '', 10)
        pdf.cell(W1, 6, safe_text(label), 1, 0, 'L')
        pdf.set_font('Arial', '', 10)
        pdf.cell(W2, 6, safe_text(val), 1, 1, 'R')

    row('Kapasitas PLTS yang Dibutuhkan:', f'{round(KAPASITAS_KWP, 2):,.2f} kWp', True)
    row(f'Jumlah Panel {PANEL_WATT_PEAK} Wp:', f'{JUMLAH_PANEL} keping')
    row('Estimasi Area Atap:', f'{round(ESTIMASI_AREA, 2):,.2f} m2')
    row('Total Investasi Estimasi:', format_rupiah(TOTAL_INVESTASI), True)

    pdf.ln(5)
    pdf.multi_cell(0, 5, safe_text(f"Dengan kapasitas tersebut, sistem PLTS diperkirakan mampu menghasilkan energi sekitar {round(PRODUKSI_KWH_BULANAN, 4):,.4f} kWh per bulan, sehingga dapat memberikan potensi penghematan sebagai berikut:"))
    pdf.ln(2)

    row('Penghematan Bulanan (Uang):', format_rupiah(PENGHEMATAN_BULANAN_RP))
    row('Penghematan Tahunan (Uang):', format_rupiah(PENGHEMATAN_TAHUNAN_RP))
    row('Perkiraan Waktu Balik Modal (BEP):', f'{BEP_TAHUN} tahun', True)

    pdf.ln(5)
    pdf.set_font('Arial', 'I', 9)
    pdf.multi_cell(0, 4, safe_text(f"Perhitungan ini merujuk pada tarif listrik saat ini yaitu {format_rupiah(TDL_USED)} per kWh dan PVOUT tahunan sebesar {round(PVOUT_ANNUAL, 1):,.1f} kWh/kWp/year."))
    pdf.ln(5)

    # Page 2 - notes
    pdf.add_page()
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 7, safe_text('CATATAN PENTING'), 0, 1, 'L')
    pdf.ln(2)
    pdf.set_font('Arial', '', 10)
    pdf.multi_cell(0, 5, safe_text("1. Nilai PVOUT pada simulasi ini bersumber dari PVGIS (JRC), sehingga hasil estimasi produksi energi memiliki tingkat keandalan yang baik."))
    pdf.ln(2)
    pdf.multi_cell(0, 5, safe_text("2. Estimasi total investasi pada simulasi ini menggunakan pendekatan linier. Namun, dalam praktiknya harga aktual sering kali lebih rendah pada kapasitas yang lebih besar karena efisiensi skala."))
    pdf.ln(2)
    pdf.multi_cell(0, 5, safe_text("Sehingga simulasi ini dapat digunakan sebagai referensi awal yang baik, dan nilai final akan disesuaikan pada saat penyusunan penawaran resmi."))
    pdf.ln(10)

    pdf.multi_cell(0, 5, safe_text("Kami siap membantu Bapak/Ibu dalam diskusi lanjutan mengenai opsi kapasitas, konfigurasi teknis, dan penawaran resmi."))
    pdf.ln(5)
    pdf.cell(0, 5, safe_text("Terima kasih atas perhatian dan kepercayaan Bapak/Ibu."), 0, 1)
    pdf.ln(5)
    pdf.cell(0, 5, safe_text("Hormat kami,"), 0, 1)
    pdf.ln(2)
    pdf.set_font('Arial', 'B', 10)
    pdf.cell(0, 5, safe_text("PT. TOBA ENERGI NUSAJAYA"), 0, 1)

    pdf.set_y(-20)
    pdf.set_font('Arial', 'I', 8)
    pdf.cell(0, 5, safe_text('Jl. Raya Kertamaya No.1, Bogor, Jawa Barat | Phone: +62 853-7071-6686 | info@tobaenergi.com'), 0, 0, 'C')

    return pdf


# --- API ENDPOINTS ---
@app.route('/api/pvout', methods=['POST'])
def api_pvout():
    try:
        data = request.json
        input_str = data.get('coordinates', '').strip()
        parts = input_str.split(',')
        if len(parts) != 2:
            raise ValueError("Format Salah")
        lat = float(parts[0].strip())
        lon = float(parts[1].strip())
    except Exception:
        return jsonify({"status": "failed", "message": "Input Salah"}), 400

    result = get_pvout_annual(lat, lon)
    if "error" in result:
        return jsonify({"status": "failed", "message": result['error']}), 500

    return jsonify({"status": "success", "pvout_value": result['pvout_formatted'], "raw_value": result['pvout_numeric']})


@app.route('/api/calculate_bep', methods=['POST'])
def api_calculate_bep():
    try:
        data = request.json
        result = calculate_solar_economics(
            data.get('pvout_annual'),
            data.get('tagihan_listrik'),
            data.get('tarif_listrik'),
            data.get('penghematan_persen')
        )
        if "error" in result:
            return jsonify({"status": "failed", "message": result['error']}), 500
        return jsonify(result), 200
    except Exception as e:
        return jsonify({"status": "failed", "message": str(e)}), 500


@app.route('/api/generate_pdf', methods=['POST'])
def api_generate_pdf():
    try:
        data = request.json
        pdf = create_proposal_pdf(data)
        buffer = io.BytesIO(pdf.output(dest='S').encode('latin-1'))
        buffer.seek(0)
        return send_file(buffer, download_name=f'Proposal_PLTS.pdf', mimetype='application/pdf', as_attachment=True)
    except Exception as e:
        return jsonify({"status": "failed", "message": str(e)}), 500


@app.route('/')
def index():
    return render_template('index.html')


if __name__ == '__main__':
    app.run(debug=True)
