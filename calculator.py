# calculator.py
import math
import requests

# --- KONSTANTA GLOBAL ---
DEFAULT_TARIFF = 1699.53
COST_PER_KWP = 12390000
LOSS_FACTOR = 0.85  # used in economics (kept for reference)
PANEL_WATT_PEAK = 650
PANEL_AREA_SQM = 2.71

# --- FUNGSI: Ambil PVOUT annual dari PVGIS (PVcalc) ---
def get_pvout_annual(latitude, longitude, loss=14, slope=0, azimuth=0):
    """
    Mengambil PVOUT annual (kWh/kWp/year) dari PVGIS (JRC PVcalc).
    Mengembalikan dict: {"pvout_numeric": float, "pvout_formatted": str} 
    atau {"error": "..."} saat gagal.
    """
    try:
        url = (
            "https://re.jrc.ec.europa.eu/api/PVcalc?"
            f"lat={latitude}&lon={longitude}&peakpower=1&loss={loss}"
            f"&slope={slope}&azimuth={azimuth}&outputformat=json"
        )
        r = requests.get(url, timeout=12)
        r.raise_for_status()
        data = r.json()

        # Ambil E_y dari struktur JSON
        pvout_value = None
        try:
            pvout_value = data["outputs"]["totals"]["fixed"]["E_y"]
        except Exception:
            # struktur mungkin berbeda; coba jalur lain aman
            # jika tidak ditemukan, kembalikan error
            return {"error": "PVGIS response missing E_y value."}

        return {
            "pvout_numeric": float(pvout_value),
            "pvout_formatted": str(round(float(pvout_value), 1)).replace(".", ",")
        }

    except requests.exceptions.RequestException as e:
        return {"error": f"PVGIS request error: {e}"}
    except Exception as e:
        return {"error": f"Unexpected error while fetching PVOUT: {e}"}


# --- FUNGSI: Perhitungan finansial & sizing (dipakai app.py) ---
def calculate_solar_economics(pvout_annual, tagihan_listrik, tarif_listrik, penghematan_persen):
    """
    pvout_annual: kWh/kWp/year (float)
    tagihan_listrik: Rp (float)
    tarif_listrik: Rp/kWh (float)
    penghematan_persen: persen (float 0-100)

    Mengembalikan dict yg berisi kunci yang dipakai app.py/pdf:
    - status
    - TDL_Used, PVOut_Annual, PVOUT_Bulanan_Efektif, Kebutuhan_kWh_Bulanan,
      Kapasitas_kWp, Produksi_kWh_Bulanan, Total_Investasi,
      Penghematan_Tahunan_Rp, BEP_Tahun, Jumlah_Panel, Estimasi_Area_m2, LOSS_FACTOR
    """
    try:
        tdl = float(tarif_listrik) if tarif_listrik and float(tarif_listrik) > 0 else DEFAULT_TARIFF
        kebutuhan_energi_bulanan = float(tagihan_listrik) / tdl if float(tdl) != 0 else 0.0
        penghematan_desimal = float(penghematan_persen) / 100.0
        target_produksi_bulanan = kebutuhan_energi_bulanan * penghematan_desimal

        # PVOUT bulanan efektif = (pvout_annual / 12) * performance ratio (LOSS_FACTOR)
        pvout_monthly_effective = (float(pvout_annual) / 12.0) * LOSS_FACTOR
        if pvout_monthly_effective == 0:
            return {"error": "PVOut tahunan tidak valid (0) atau LOSS_FACTOR=0."}

        kapasitas_kwp = target_produksi_bulanan / pvout_monthly_effective
        total_investasi = kapasitas_kwp * COST_PER_KWP
        penghematan_tahunan_uang = target_produksi_bulanan * 12.0 * float(tdl)
        bep_tahun = (total_investasi / penghematan_tahunan_uang) if penghematan_tahunan_uang > 0 else float('inf')

        jumlah_panel = int(math.ceil(kapasitas_kwp * 1000.0 / PANEL_WATT_PEAK)) if kapasitas_kwp > 0 else 0
        estimasi_area = jumlah_panel * PANEL_AREA_SQM
        produksi_kwh_bulanan = target_produksi_bulanan

        return {
            "status": "success",
            "TDL_Used": float(round(tdl, 2)),
            "PVOut_Annual": float(round(float(pvout_annual), 1)),
            "PVOUT_Bulanan_Efektif": float(round(pvout_monthly_effective, 4)),
            "Kebutuhan_kWh_Bulanan": float(round(kebutuhan_energi_bulanan, 2)),
            "Kapasitas_kWp": float(round(kapasitas_kwp, 2)),
            "Produksi_kWh_Bulanan": float(round(produksi_kwh_bulanan, 4)),
            "Total_Investasi": float(round(total_investasi, 0)),
            "Penghematan_Tahunan_Rp": float(round(penghematan_tahunan_uang, 0)),
            "BEP_Tahun": float(round(bep_tahun, 1)) if bep_tahun != float('inf') else 'Inf',
            "Jumlah_Panel": jumlah_panel,
            "Estimasi_Area_m2": float(round(estimasi_area, 2)),
            "LOSS_FACTOR": LOSS_FACTOR
        }

    except Exception as e:
        return {"error": f"Kesalahan perhitungan finansial: {e}"}
